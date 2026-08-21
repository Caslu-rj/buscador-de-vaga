"""Interface profunda para descobrir e organizar oportunidades."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol
from unicodedata import normalize as normalize_unicode
from urllib.parse import urlsplit, urlunsplit

from buscador_de_vaga.domain import (
    CandidateProfile,
    Evidence,
    EvidenceAssertion,
    FitBreakdown,
    FitDimension,
    FitScore,
    JobCategory,
    JobPosting,
    JobSourceQuery,
    MatchAssessment,
    Opportunity,
    Provenance,
    Requirement,
    RequirementAssessment,
    RequirementImportance,
    RequirementKind,
    RequirementStatus,
    RequirementSubject,
    SearchCriteria,
    Shortlist,
)


class InvalidDiscoveryRequest(ValueError):
    """Indica que perfil e critérios não formam uma busca válida."""


class JobSourceFailureKind(StrEnum):
    """Categorias estáveis de falha que não expõem detalhes do fornecedor."""

    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    CONTRACT = "contract"


class JobSourceError(RuntimeError):
    """Falha segura e acionável produzida por um JobSource."""

    def __init__(
        self,
        message: str,
        *,
        source_name: str,
        kind: JobSourceFailureKind,
        action: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.source_name = source_name
        self.kind = kind
        self.action = action
        self.retryable = retryable


class JobSource(Protocol):
    """Seam para uma fonte externa de publicações de vagas."""

    @property
    def name(self) -> str:
        """Identificador legível e estável da fonte."""
        ...

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        """Retorna publicações preservando identidade e procedência."""
        ...


@dataclass(frozen=True, slots=True)
class SourceReport:
    """Resumo observável da consulta ao JobSource."""

    source_name: str
    postings_received: int


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Resultado auditável de uma execução de descoberta."""

    candidate_profile_id: str
    criteria: SearchCriteria
    source_report: SourceReport
    postings: tuple[JobPosting, ...]
    opportunities: tuple[Opportunity, ...]
    match_assessments: tuple[MatchAssessment, ...]
    shortlist: Shortlist


_CATEGORY_SEARCH_TERMS: dict[JobCategory, str] = {
    JobCategory.SOFTWARE_DEVELOPMENT: "desenvolvedor de software",
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: "suporte de TI infraestrutura",
    JobCategory.SYSTEMS: "analista de sistemas",
    JobCategory.QUALITY_ASSURANCE: "qualidade de software QA",
    JobCategory.DATA: "analista de dados",
}

_CATEGORY_TITLE_ALIASES: dict[JobCategory, tuple[str, ...]] = {
    JobCategory.SOFTWARE_DEVELOPMENT: (
        "backend engineer",
        "desenvolvedor",
        "desenvolvedora",
        "developer",
        "programador",
        "programadora",
        "software engineer",
    ),
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: (
        "help desk",
        "infraestrutura",
        "service desk",
        "suporte",
    ),
    JobCategory.SYSTEMS: ("analista de sistemas", "systems analyst"),
    JobCategory.QUALITY_ASSURANCE: (
        "quality assurance",
        "qa",
        "software tester",
        "tester",
    ),
    JobCategory.DATA: (
        "analista de dados",
        "analytics",
        "business intelligence",
        "data analyst",
    ),
}

_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "aws": ("amazon web services", "aws"),
    "docker": ("docker",),
    "git": ("git",),
    "linux": ("linux",),
    "python": ("python",),
    "sql": ("sql",),
}

_SKILL_CONTEXT_TERMS = (
    "conhecimento",
    "conhecimentos",
    "desejável",
    "desejavel",
    "experiência",
    "experiencia",
    "habilidade",
    "habilidades",
    "requisito",
    "requisitos",
    "skills",
    "tecnologia",
    "tecnologias",
)

_ENTRY_PROGRAM_ALIASES: dict[str, tuple[str, ...]] = {
    "apprenticeship": ("aprendiz",),
    "internship": ("estagiário", "estagiaria", "estagiária", "estagio", "estágio", "intern"),
    "trainee": ("trainee",),
}

_SENIORITY_ALIASES: dict[str, tuple[str, ...]] = {
    "junior": ("jr", "junior", "júnior"),
    "mid-level": ("mid-level", "pleno"),
    "senior": ("senior", "sênior"),
}

_WORKPLACE_MODE_ALIASES: dict[str, tuple[str, ...]] = {
    "hybrid": ("hibrida", "hibrido", "híbrida", "híbrido", "hybrid"),
    "onsite": ("on-site", "onsite", "presencial"),
    "remote": ("home office", "remote", "remota", "remoto"),
}

_WORKPLACE_CONTEXT_TERMS = (
    "modelo",
    "modalidade",
    "regime",
    "trabalho",
    "workplace",
)

_MATCH_POLICY_VERSION = "match-v1"
_DIMENSION_WEIGHTS: tuple[tuple[FitDimension, int], ...] = (
    (FitDimension.JOB_CATEGORY, 40),
    (FitDimension.SKILLS, 25),
    (FitDimension.ENTRY_PROGRAM_SENIORITY, 20),
    (FitDimension.LOCATION_WORKPLACE_MODE, 15),
)

type _ExternalIdentity = tuple[Literal["external-id"], str, str]
type _CanonicalUrlIdentity = tuple[Literal["canonical-url"], str]
type _StrongIdentity = _ExternalIdentity | _CanonicalUrlIdentity
type _CompleteFieldsIdentity = tuple[str, str, str]


class OpportunityDiscovery:
    """Orquestra a descoberta sem expor suas etapas internas."""

    def __init__(self, *, source: JobSource) -> None:
        self._source = source

    def discover(
        self,
        profile: CandidateProfile,
        criteria: SearchCriteria,
    ) -> DiscoveryResult:
        """Busca publicações e devolve oportunidades normalizadas."""
        if criteria.category not in profile.target_categories:
            raise InvalidDiscoveryRequest(
                f"JobCategory {criteria.category} não pertence ao CandidateProfile"
            )

        query = JobSourceQuery(
            keywords=_CATEGORY_SEARCH_TERMS[criteria.category],
            location=criteria.location,
            limit=criteria.limit,
        )
        postings = self._source.search(query)
        opportunities = _consolidate_postings(postings)
        match_assessments = tuple(
            _assess_opportunity(opportunity, profile) for opportunity in opportunities
        )

        return DiscoveryResult(
            candidate_profile_id=profile.id,
            criteria=criteria,
            source_report=SourceReport(
                source_name=self._source.name,
                postings_received=len(postings),
            ),
            postings=postings,
            opportunities=opportunities,
            match_assessments=match_assessments,
            shortlist=Shortlist(items=opportunities),
        )


def _assess_opportunity(
    opportunity: Opportunity,
    profile: CandidateProfile,
) -> MatchAssessment:
    requirements = tuple(
        sorted(
            (
                *_category_requirements(opportunity),
                *_skill_requirements(opportunity),
                *_entry_requirements(opportunity),
                *_location_requirements(opportunity),
            ),
            key=_requirement_sort_key,
        )
    )
    point_allocations = _point_allocations(requirements)
    assessments = tuple(
        _assess_requirement(
            requirement,
            profile,
            maximum_points=point_allocations[requirement.id],
        )
        for requirement in requirements
    )
    breakdown = tuple(
        FitBreakdown(
            dimension=dimension,
            weight=weight,
            awarded_points=sum(
                assessment.awarded_points
                for assessment in assessments
                if assessment.requirement.dimension is dimension
            ),
            covered_weight=sum(
                assessment.covered_points
                for assessment in assessments
                if assessment.requirement.dimension is dimension
            ),
        )
        for dimension, weight in _DIMENSION_WEIGHTS
    )
    return MatchAssessment(
        opportunity_id=opportunity.id,
        requirement_assessments=assessments,
        fit_score=FitScore(
            value=sum(item.awarded_points for item in breakdown),
            evidence_coverage=sum(item.covered_weight for item in breakdown),
            policy_version=_MATCH_POLICY_VERSION,
            breakdown=breakdown,
        ),
    )


def _category_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    matches: set[JobCategory] = set()
    provenance: set[Provenance] = set()
    for posting in opportunity.postings:
        posting_categories = _categories_in_title(posting.title)
        matches.update(posting_categories)
        if posting_categories:
            provenance.add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                )
            )

    if len(matches) != 1:
        return ()

    category = matches.pop()
    return (
        Requirement(
            id=f"job-category:{category.value}",
            subject=RequirementSubject(
                kind=RequirementKind.JOB_CATEGORY,
                value=category.value,
            ),
            statement=f"A Opportunity pertence à JobCategory {category.value}.",
            dimension=FitDimension.JOB_CATEGORY,
            importance=RequirementImportance.UNKNOWN,
            provenance=tuple(sorted(provenance, key=_provenance_sort_key)),
        ),
    )


def _skill_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    provenance_by_skill: dict[str, set[Provenance]] = {}
    for posting in opportunity.postings:
        for skill in _skills_in_text(posting.title):
            provenance_by_skill.setdefault(skill, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                )
            )

        if posting.summary is None or not _has_skill_context(posting.summary):
            continue
        for skill in _skills_in_text(posting.summary):
            provenance_by_skill.setdefault(skill, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#summary",
                )
            )

    return tuple(
        Requirement(
            id=f"skill:{skill}",
            subject=RequirementSubject(
                kind=RequirementKind.SKILL,
                value=skill,
            ),
            statement=f"A Opportunity menciona explicitamente a skill {skill}.",
            dimension=FitDimension.SKILLS,
            importance=RequirementImportance.UNKNOWN,
            provenance=tuple(
                sorted(provenance_by_skill[skill], key=_provenance_sort_key)
            ),
        )
        for skill in sorted(provenance_by_skill)
    )


def _skills_in_text(value: str) -> set[str]:
    normalized = _comparison_text(value) or ""
    return {
        skill
        for skill, aliases in _SKILL_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }


def _has_skill_context(summary: str) -> bool:
    normalized = _comparison_text(summary) or ""
    return any(_contains_term(normalized, term) for term in _SKILL_CONTEXT_TERMS)


def _entry_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    provenance_by_subject: dict[RequirementSubject, set[Provenance]] = {}
    values_by_kind: dict[RequirementKind, set[str]] = {}
    for posting in opportunity.postings:
        for subject in _entry_subjects_in_title(posting.title):
            values_by_kind.setdefault(subject.kind, set()).add(subject.value)
            provenance_by_subject.setdefault(subject, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                )
            )

    unambiguous_subjects = tuple(
        subject
        for subject in provenance_by_subject
        if len(values_by_kind[subject.kind]) == 1
    )
    return tuple(
        Requirement(
            id=f"{subject.kind.value}:{subject.value}",
            subject=subject,
            statement=f"A Opportunity declara {subject.kind.value} {subject.value}.",
            dimension=FitDimension.ENTRY_PROGRAM_SENIORITY,
            importance=RequirementImportance.UNKNOWN,
            provenance=tuple(
                sorted(provenance_by_subject[subject], key=_provenance_sort_key)
            ),
        )
        for subject in sorted(
            unambiguous_subjects,
            key=lambda subject: (subject.kind.value, subject.value),
        )
    )


def _entry_subjects_in_title(title: str) -> set[RequirementSubject]:
    normalized = _comparison_text(title) or ""
    subjects = {
        RequirementSubject(kind=RequirementKind.ENTRY_PROGRAM, value=value)
        for value, aliases in _ENTRY_PROGRAM_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }
    subjects.update(
        RequirementSubject(kind=RequirementKind.SENIORITY, value=value)
        for value, aliases in _SENIORITY_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    )
    return subjects


def _location_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    provenance_by_subject: dict[RequirementSubject, set[Provenance]] = {}
    values_by_kind: dict[RequirementKind, set[str]] = {}
    for posting in opportunity.postings:
        if posting.location is not None:
            normalized_location = _comparison_text(posting.location)
            if normalized_location is not None:
                location_subject = RequirementSubject(
                    kind=RequirementKind.LOCATION,
                    value=normalized_location,
                )
                values_by_kind.setdefault(RequirementKind.LOCATION, set()).add(
                    normalized_location
                )
                provenance_by_subject.setdefault(location_subject, set()).add(
                    Provenance(
                        origin=posting.source_name,
                        locator=f"{posting.external_id}#location",
                    )
                )
            for mode in _workplace_modes_in_text(posting.location):
                _record_workplace_mode(
                    mode,
                    posting,
                    field="location",
                    values_by_kind=values_by_kind,
                    provenance_by_subject=provenance_by_subject,
                )

        if posting.summary is not None and _has_workplace_context(posting.summary):
            for mode in _workplace_modes_in_text(posting.summary):
                _record_workplace_mode(
                    mode,
                    posting,
                    field="summary",
                    values_by_kind=values_by_kind,
                    provenance_by_subject=provenance_by_subject,
                )

    unambiguous_subjects = tuple(
        subject
        for subject in provenance_by_subject
        if len(values_by_kind[subject.kind]) == 1
    )
    return tuple(
        Requirement(
            id=f"{subject.kind.value}:{subject.value}",
            subject=subject,
            statement=f"A Opportunity declara {subject.kind.value} {subject.value}.",
            dimension=FitDimension.LOCATION_WORKPLACE_MODE,
            importance=RequirementImportance.UNKNOWN,
            provenance=tuple(
                sorted(provenance_by_subject[subject], key=_provenance_sort_key)
            ),
        )
        for subject in sorted(
            unambiguous_subjects,
            key=lambda subject: (subject.kind.value, subject.value),
        )
    )


def _record_workplace_mode(
    mode: str,
    posting: JobPosting,
    *,
    field: str,
    values_by_kind: dict[RequirementKind, set[str]],
    provenance_by_subject: dict[RequirementSubject, set[Provenance]],
) -> None:
    subject = RequirementSubject(
        kind=RequirementKind.WORKPLACE_MODE,
        value=mode,
    )
    values_by_kind.setdefault(RequirementKind.WORKPLACE_MODE, set()).add(mode)
    provenance_by_subject.setdefault(subject, set()).add(
        Provenance(
            origin=posting.source_name,
            locator=f"{posting.external_id}#{field}",
        )
    )


def _workplace_modes_in_text(value: str) -> set[str]:
    normalized = _comparison_text(value) or ""
    return {
        mode
        for mode, aliases in _WORKPLACE_MODE_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }


def _has_workplace_context(summary: str) -> bool:
    normalized = _comparison_text(summary) or ""
    return any(_contains_term(normalized, term) for term in _WORKPLACE_CONTEXT_TERMS)


def _categories_in_title(title: str) -> set[JobCategory]:
    normalized = _comparison_text(title) or ""
    return {
        category
        for category, aliases in _CATEGORY_TITLE_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!\w){escaped}(?!\w)", text) is not None


def _assess_requirement(
    requirement: Requirement,
    profile: CandidateProfile,
    *,
    maximum_points: int,
) -> RequirementAssessment:
    evidence = tuple(
        sorted(
            (
                *_matching_profile_evidence(requirement, profile),
                *_derived_category_evidence(requirement, profile),
            ),
            key=_evidence_sort_key,
        )
    )
    assertions = {item.assertion for item in evidence}
    if assertions == {EvidenceAssertion.SUPPORTS}:
        status = RequirementStatus.MET
    elif assertions == {EvidenceAssertion.CONTRADICTS}:
        status = RequirementStatus.UNMET
    else:
        status = RequirementStatus.UNKNOWN

    awarded_points = maximum_points if status is RequirementStatus.MET else 0
    covered_points = maximum_points if status is not RequirementStatus.UNKNOWN else 0
    return RequirementAssessment(
        requirement=requirement,
        status=status,
        evidence=evidence,
        maximum_points=maximum_points,
        awarded_points=awarded_points,
        covered_points=covered_points,
    )


def _matching_profile_evidence(
    requirement: Requirement,
    profile: CandidateProfile,
) -> tuple[Evidence, ...]:
    return tuple(
        evidence
        for evidence in profile.evidence
        if evidence.subject.kind is requirement.subject.kind
        and _comparison_text(evidence.subject.value)
        == _comparison_text(requirement.subject.value)
    )


def _derived_category_evidence(
    requirement: Requirement,
    profile: CandidateProfile,
) -> tuple[Evidence, ...]:
    if requirement.subject.kind is not RequirementKind.JOB_CATEGORY:
        return ()

    category = JobCategory(requirement.subject.value)
    supports = category in profile.target_categories
    return (
        Evidence(
            id=f"candidate-profile:target-category:{category.value}",
            subject=requirement.subject,
            statement=(
                f"CandidateProfile declara {category.value} em target_categories."
                if supports
                else f"CandidateProfile não declara {category.value} em target_categories."
            ),
            assertion=(
                EvidenceAssertion.SUPPORTS
                if supports
                else EvidenceAssertion.CONTRADICTS
            ),
            provenance=Provenance(
                origin="candidate-profile",
                locator="target_categories",
            ),
        ),
    )


def _point_allocations(requirements: tuple[Requirement, ...]) -> dict[str, int]:
    allocations: dict[str, int] = {}
    for dimension, weight in _DIMENSION_WEIGHTS:
        dimension_requirements = tuple(
            requirement
            for requirement in requirements
            if requirement.dimension is dimension
        )
        if not dimension_requirements:
            continue
        base_points, remainder = divmod(weight, len(dimension_requirements))
        for index, requirement in enumerate(dimension_requirements):
            allocations[requirement.id] = base_points + (index < remainder)
    return allocations


def _requirement_sort_key(requirement: Requirement) -> tuple[int, str, str]:
    dimension_order = {
        dimension: index for index, (dimension, _) in enumerate(_DIMENSION_WEIGHTS)
    }
    return (
        dimension_order[requirement.dimension],
        requirement.subject.kind.value,
        requirement.subject.value,
    )


def _evidence_sort_key(evidence: Evidence) -> tuple[str, str, str]:
    return (
        evidence.id,
        evidence.provenance.origin,
        evidence.provenance.locator,
    )


def _provenance_sort_key(provenance: Provenance) -> tuple[str, str]:
    return (provenance.origin, provenance.locator)


def _consolidate_postings(postings: tuple[JobPosting, ...]) -> tuple[Opportunity, ...]:
    """Forma componentes fortes e só depois aplica equivalência textual inequívoca."""
    parents = list(range(len(postings)))
    identity_owner: dict[_StrongIdentity, int] = {}

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for index, posting in enumerate(postings):
        for identity in _strong_identity_keys(posting):
            owner = identity_owner.setdefault(identity, index)
            union(index, owner)

    strong_components: dict[int, list[int]] = {}
    for index in range(len(postings)):
        strong_components.setdefault(find(index), []).append(index)

    fields_owner: dict[_CompleteFieldsIdentity, int] = {}
    for component in strong_components.values():
        # Triplas conflitantes tornam qualquer expansão textual desse componente incerta.
        fields_identities: set[_CompleteFieldsIdentity] = set()
        for index in component:
            fields_identity = _complete_fields_identity(postings[index])
            if fields_identity is not None:
                fields_identities.add(fields_identity)
        if len(fields_identities) == 1:
            fields_identity = fields_identities.pop()
            owner = fields_owner.setdefault(fields_identity, component[0])
            union(component[0], owner)

    groups: dict[int, list[JobPosting]] = {}
    for index, posting in enumerate(postings):
        groups.setdefault(find(index), []).append(posting)

    normalized_groups = tuple(
        tuple(sorted(group, key=_posting_sort_key)) for group in groups.values()
    )
    return tuple(
        _to_opportunity(group)
        for group in sorted(
            normalized_groups,
            key=lambda group: min(
                (posting.source_name, posting.external_id) for posting in group
            ),
        )
    )


def _strong_identity_keys(posting: JobPosting) -> tuple[_StrongIdentity, ...]:
    identities: list[_StrongIdentity] = []
    if posting.source_name.strip() and posting.external_id.strip():
        identities.append(("external-id", posting.source_name, posting.external_id))

    canonical_url = _canonical_url(posting.source_url)
    if canonical_url is not None:
        identities.append(("canonical-url", canonical_url))

    return tuple(identities)


def _complete_fields_identity(posting: JobPosting) -> _CompleteFieldsIdentity | None:
    title = _comparison_text(posting.title)
    company = _comparison_text(posting.company)
    location = _comparison_text(posting.location)
    if title is None or company is None or location is None:
        return None
    return (company, title, location)


def _to_opportunity(postings: tuple[JobPosting, ...]) -> Opportunity:
    posting = postings[0]
    source_name, external_id = min(
        (candidate.source_name, candidate.external_id) for candidate in postings
    )
    return Opportunity(
        id=f"{source_name}:{external_id}",
        title=_normalize_required_text(posting.title),
        company=_normalize_optional_text(posting.company),
        location=_normalize_optional_text(posting.location),
        source_url=_canonical_url(posting.source_url)
        or _normalize_required_text(posting.source_url),
        postings=postings,
    )


def _posting_sort_key(posting: JobPosting) -> tuple[str, ...]:
    return (
        posting.source_name,
        posting.external_id,
        _canonical_url(posting.source_url) or _normalize_required_text(posting.source_url),
        _normalize_required_text(posting.title),
        _normalize_optional_text(posting.company) or "",
        _normalize_optional_text(posting.location) or "",
        posting.collected_at.isoformat(),
        posting.source_updated_at.isoformat() if posting.source_updated_at else "",
        posting.summary or "",
        posting.title,
        posting.company or "",
        posting.location or "",
        posting.source_url,
    )


def _canonical_url(value: str) -> str | None:
    """Canonicaliza apenas transformações seguras para identidade HTTP(S)."""
    normalized = _normalize_required_text(value)
    if not normalized or any(character.isspace() for character in normalized):
        return None

    try:
        parts = urlsplit(normalized)
        scheme = parts.scheme.casefold()
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        return None

    if scheme not in {"http", "https"} or hostname is None:
        return None
    if parts.username is not None or parts.password is not None:
        return None

    host = hostname.casefold()
    if ":" in host:
        host = f"[{host}]"
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    return urlunsplit((scheme, host, parts.path or "/", parts.query, parts.fragment))


def _normalize_required_text(value: str) -> str:
    return " ".join(normalize_unicode("NFC", value).split())


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_required_text(value)
    return normalized or None


def _comparison_text(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.casefold() if normalized is not None else None
