"""Interface profunda para descobrir e organizar oportunidades."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from html import unescape
from html.parser import HTMLParser
from typing import Literal, Protocol
from unicodedata import combining
from unicodedata import normalize as normalize_unicode
from urllib.parse import urlsplit, urlunsplit

from buscador_de_vaga.application_candidate import (
    ApplicationCandidate,
    select_application_candidates,
)
from buscador_de_vaga.candidate_positioning import (
    MAX_AUTOMATIC_QUERIES,
    AutomaticSearchPlan,
    AutomaticSearchTarget,
    CandidateCareerAlignment,
    CandidateCareerLevel,
    CandidateProfileAssessment,
    assess_candidate_profile,
)
from buscador_de_vaga.domain import (
    CandidateProfile,
    CareerPreference,
    CareerPreferenceAssessment,
    CareerPriority,
    CareerRecommendation,
    EligibilityStatus,
    EntryProgram,
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
    Seniority,
    Shortlist,
    WorkplaceMode,
)
from buscador_de_vaga.location import (
    NormalizedLocation,
    locations_equivalent,
    normalize_location,
)
from buscador_de_vaga.search_strategy import (
    AutomaticCareerSearchStrategy,
    CareerSearchStrategy,
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
    policy_version: str
    source_report: SourceReport
    postings: tuple[JobPosting, ...]
    opportunities: tuple[Opportunity, ...]
    match_assessments: tuple[MatchAssessment, ...]
    shortlist: Shortlist

    @property
    def application_candidates(self) -> tuple[ApplicationCandidate, ...]:
        """Deriva recomendações manuais apenas da Shortlist existente."""
        return select_application_candidates(
            _shortlisted_match_assessments(self.match_assessments, self.shortlist)
        )


@dataclass(frozen=True, slots=True)
class AutomaticDiscoveryResult:
    """Resultado auditável de uma execução de descoberta automática."""

    candidate_profile_id: str
    assessment: CandidateProfileAssessment
    plan: AutomaticSearchPlan
    policy_version: str
    source_report: SourceReport
    postings: tuple[JobPosting, ...]
    opportunities: tuple[Opportunity, ...]
    match_assessments: tuple[MatchAssessment, ...]
    alignments_by_opportunity_id: dict[str, CandidateCareerAlignment]
    shortlist: Shortlist

    @property
    def application_candidates(self) -> tuple[ApplicationCandidate, ...]:
        """Deriva recomendações automáticas usando os alinhamentos existentes."""
        return select_application_candidates(
            _shortlisted_match_assessments(self.match_assessments, self.shortlist),
            alignments_by_opportunity_id=self.alignments_by_opportunity_id,
        )


def _shortlisted_match_assessments(
    match_assessments: tuple[MatchAssessment, ...],
    shortlist: Shortlist,
) -> tuple[MatchAssessment, ...]:
    assessments_by_id = {
        assessment.opportunity_id: assessment for assessment in match_assessments
    }
    return tuple(
        assessments_by_id[opportunity.id] for opportunity in shortlist.items
    )


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
    "diferencial",
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

_BLOCKING_IMPORTANCE_TERMS = (
    "mandatory",
    "must have",
    "obrigatoria",
    "obrigatórias",
    "obrigatorio",
    "obrigatórios",
    "obrigatória",
    "obrigatório",
    "required",
)

_PREFERRED_IMPORTANCE_TERMS = (
    "desejavel",
    "desejável",
    "diferencial",
    "nice to have",
    "preferencial",
    "preferred",
)

_NEGATED_BLOCKING_PATTERN = re.compile(
    r"(?<!\w)(?:nao|não|not)"
    r"(?:\s+\w+){0,3}\s+"
    r"(?:mandatory|required|must(?:\s+|-)have|obrigat[oó]ri[oa]s?)"
    r"(?!\w)"
)

_ENTRY_PROGRAM_ALIASES: dict[EntryProgram, tuple[str, ...]] = {
    EntryProgram.APPRENTICESHIP: ("aprendiz",),
    EntryProgram.INTERNSHIP: (
        "estagiário",
        "estagiaria",
        "estagiária",
        "estagio",
        "estágio",
        "intern",
    ),
    EntryProgram.TRAINEE: ("trainee",),
}

_SENIORITY_ALIASES: dict[Seniority, tuple[str, ...]] = {
    Seniority.JUNIOR: ("jr", "junior", "júnior"),
    Seniority.MID_LEVEL: ("mid-level", "pleno"),
    Seniority.SENIOR: ("sr", "senior", "sênior"),
}

_SUMMARY_ENTRY_PROGRAM_CONTEXTS: dict[EntryProgram, tuple[str, ...]] = {
    EntryProgram.INTERNSHIP: (
        "vaga de estagio",
        "vaga para estagio",
        "oportunidade de estagio",
        "programa de estagio",
        "posicao de estagio",
    ),
    EntryProgram.TRAINEE: (
        "programa trainee",
        "programa de trainee",
        "vaga trainee",
        "vaga de trainee",
        "posicao trainee",
        "posicao de trainee",
    ),
}
_SUMMARY_SENIORITY_CONTEXTS: dict[Seniority, tuple[str, ...]] = {
    Seniority.JUNIOR: (
        "vaga junior",
        "posicao junior",
        "nivel junior",
    ),
    Seniority.MID_LEVEL: (
        "vaga pleno",
        "posicao pleno",
        "nivel pleno",
    ),
    Seniority.SENIOR: (
        "vaga senior",
        "posicao senior",
        "nivel senior",
    ),
}
_SUMMARY_ENTRY_PROGRAM_ROLE_CONTEXTS: dict[EntryProgram, tuple[str, ...]] = {
    EntryProgram.INTERNSHIP: ("estagiario", "estagiaria"),
}
_SUMMARY_SENIORITY_ROLES = (
    "pessoa desenvolvedora",
    "desenvolvedor",
    "desenvolvedora",
    "profissional",
)
_SUMMARY_ROLE_INTENT_TERMS = (
    "buscamos",
    "contratamos",
    "contratando",
    "contratar",
    "nivel",
    "oportunidade",
    "posicao",
    "programa",
    "procuramos",
    "vaga",
)
_SUMMARY_ROLE_INTENT_LINK_TERMS = frozenset(
    {
        "a",
        "ao",
        "da",
        "de",
        "do",
        "o",
        "para",
        "por",
        "um",
        "uma",
    }
)
_SUMMARY_ROLE_QUALIFIER_BLOCKERS = frozenset(
    {
        "a",
        "ao",
        "com",
        "da",
        "do",
        "e",
        "em",
        "na",
        "no",
        "para",
        "por",
        "que",
        "um",
        "uma",
    }
)
_SUMMARY_ROLE_QUALIFIER_CONNECTORS = frozenset({"de"})
_SUMMARY_ROLE_MAX_QUALIFIER_TOKENS = 4

_WORKPLACE_MODE_ALIASES: dict[WorkplaceMode, tuple[str, ...]] = {
    WorkplaceMode.HYBRID: (
        "hibrida",
        "hibrido",
        "híbrida",
        "híbrido",
        "hybrid",
    ),
    WorkplaceMode.ONSITE: ("on-site", "onsite", "presencial"),
    WorkplaceMode.REMOTE: ("home office", "remote", "remota", "remoto"),
}

_WORKPLACE_CONTEXT_TERMS = (
    "modelo",
    "modalidade",
    "regime",
    "trabalho",
    "workplace",
)

_MATCH_POLICY_VERSION = "match-v2"
_CAREER_ENTRY_POLICY_VERSION = "career-entry-v1"
_DIMENSION_WEIGHTS: tuple[tuple[FitDimension, int], ...] = (
    (FitDimension.JOB_CATEGORY, 40),
    (FitDimension.SKILLS, 25),
    (FitDimension.ENTRY_PROGRAM_SENIORITY, 20),
    (FitDimension.LOCATION_WORKPLACE_MODE, 15),
)
_ELIGIBILITY_ORDER = {
    EligibilityStatus.ELIGIBLE: 0,
    EligibilityStatus.UNCERTAIN: 1,
}
_ALIGNMENT_ORDER = {
    CandidateCareerAlignment.MATCH: 0,
    CandidateCareerAlignment.REVIEW: 1,
    CandidateCareerAlignment.BELOW_PROFILE: 2,
    CandidateCareerAlignment.ABOVE_PROFILE: 3,
}
_CAREER_RECOMMENDATION_ORDER = {
    CareerRecommendation.RECOMMENDED: 0,
    CareerRecommendation.REVIEW: 1,
    CareerRecommendation.LOW_PRIORITY: 2,
    CareerRecommendation.NOT_RECOMMENDED: 3,
}
_CAREER_PRIORITY_ORDER = {
    CareerPriority.INTERNSHIP: 0,
    CareerPriority.JUNIOR: 1,
    CareerPriority.TRAINEE: 2,
    CareerPriority.UNKNOWN: 3,
    CareerPriority.MID_LEVEL: 4,
    CareerPriority.SENIOR: 5,
}

type _ExternalIdentity = tuple[Literal["external-id"], str, str]
type _CanonicalUrlIdentity = tuple[Literal["canonical-url"], str]
type _StrongIdentity = _ExternalIdentity | _CanonicalUrlIdentity
type _CompleteFieldsIdentity = tuple[str, str, str]


class _SummaryTextExtractor(HTMLParser):
    """Extrai apenas o texto inerte de um summary possivelmente em HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_element_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.casefold() in {"script", "style"}:
            self._ignored_element_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"} and self._ignored_element_depth:
            self._ignored_element_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_element_depth:
            self.parts.append(data)


class _RequirementSignals:
    """Acumula subjects detectados sem apagar conflitos entre fontes."""

    def __init__(self) -> None:
        self._provenance_by_subject: dict[RequirementSubject, set[Provenance]] = {}
        self._values_by_kind: dict[RequirementKind, set[str]] = {}
        self._importances_by_subject: dict[RequirementSubject, set[RequirementImportance]] = {}

    def record(
        self,
        subject: RequirementSubject,
        provenance: Provenance,
        *,
        importance: RequirementImportance = RequirementImportance.UNKNOWN,
    ) -> None:
        self._values_by_kind.setdefault(subject.kind, set()).add(subject.resolved_value)
        self._provenance_by_subject.setdefault(subject, set()).add(provenance)
        self._importances_by_subject.setdefault(subject, set()).add(importance)

    def to_requirements(self, dimension: FitDimension) -> tuple[Requirement, ...]:
        return tuple(
            Requirement(
                id=f"{subject.kind.value}:{subject.resolved_value}",
                subject=subject,
                statement=(f"A Opportunity declara {subject.kind.value} {subject.resolved_value}."),
                dimension=dimension,
                importance=_combined_importance(self._importances_by_subject[subject]),
                provenance=tuple(
                    sorted(
                        self._provenance_by_subject[subject],
                        key=_provenance_sort_key,
                    )
                ),
                is_resolved=len(self._values_by_kind[subject.kind]) == 1,
            )
            for subject in sorted(
                self._provenance_by_subject,
                key=lambda item: (item.kind.value, item.resolved_value),
            )
        )


class OpportunityDiscovery:
    """Orquestra a descoberta sem expor suas etapas internas."""

    def __init__(self, *, source: JobSource) -> None:
        self._source = source
        self._search_strategy = CareerSearchStrategy()

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

        queries = self._search_strategy.queries_for(
            category=criteria.category,
            location=criteria.location,
            limit=criteria.limit,
        )
        collected_postings: list[JobPosting] = []
        for query in queries:
            collected_postings.extend(self._source.search(query))
        postings = tuple(collected_postings)
        opportunities = _consolidate_postings(postings)
        match_assessments = tuple(
            _assess_opportunity(opportunity, profile, criteria) for opportunity in opportunities
        )
        assessments_by_opportunity_id = {
            assessment.opportunity_id: assessment for assessment in match_assessments
        }
        shortlist_items = _ranked_shortlist_items(
            opportunities,
            assessments_by_opportunity_id,
            career_preference=criteria.career_preference,
        )[: criteria.limit]

        return DiscoveryResult(
            candidate_profile_id=profile.id,
            criteria=criteria,
            policy_version=_MATCH_POLICY_VERSION,
            source_report=SourceReport(
                source_name=self._source.name,
                postings_received=len(postings),
            ),
            postings=postings,
            opportunities=opportunities,
            match_assessments=match_assessments,
            shortlist=Shortlist(items=shortlist_items),
        )


class _AutomaticOpportunityDiscovery:
    """Orquestra a descoberta automática orientada pelo CandidateProfile."""

    def __init__(self, *, source: JobSource) -> None:
        self._source = source
        self._search_strategy = AutomaticCareerSearchStrategy()

    def discover(
        self,
        profile: CandidateProfile,
        *,
        location: str,
        limit: int = 10,
        career_preference: CareerPreference | None = None,
    ) -> AutomaticDiscoveryResult:
        """Busca publicações autonomamente e devolve oportunidades priorizadas."""
        assessment = assess_candidate_profile(profile)
        queries = self._search_strategy.build_queries(
            assessment=assessment,
            location=location,
            limit=limit,
            max_queries=MAX_AUTOMATIC_QUERIES,
        )
        plan = AutomaticSearchPlan(
            targets=tuple(
                AutomaticSearchTarget(
                    category=category,
                    recommended_levels=(
                        category_assessment.recommended_levels
                        if (
                            category_assessment := assessment.get_assessment(category)
                        )
                        is not None
                        else ()
                    ),
                )
                for category in assessment.selected_categories
            ),
            queries=queries,
        )

        collected_postings: list[JobPosting] = []
        for query in plan.queries:
            collected_postings.extend(self._source.search(query))
        postings = tuple(collected_postings)
        opportunities = _consolidate_postings(postings)

        match_assessments: list[MatchAssessment] = []
        alignments: dict[str, CandidateCareerAlignment] = {}

        for opportunity in opportunities:
            opp_category = _opportunity_resolved_category(opportunity)
            criteria_category = (
                opp_category
                if opp_category is not None
                else (
                    assessment.selected_categories[0]
                    if assessment.selected_categories
                    else (
                        profile.target_categories[0]
                        if profile.target_categories
                        else JobCategory.SOFTWARE_DEVELOPMENT
                    )
                )
            )
            criteria = SearchCriteria(
                category=criteria_category,
                location=location,
                limit=limit,
                career_preference=career_preference,
            )
            match_assessment = _assess_opportunity(opportunity, profile, criteria)
            match_assessments.append(match_assessment)

            alignment = _assess_opportunity_career_alignment(opportunity, assessment)
            alignments[opportunity.id] = alignment

        match_assessments_tuple = tuple(match_assessments)
        assessments_by_id = {m.opportunity_id: m for m in match_assessments_tuple}

        shortlist_items = _ranked_automatic_shortlist_items(
            opportunities,
            assessments_by_id,
            alignments,
            assessment,
            career_preference=career_preference,
        )[:limit]

        return AutomaticDiscoveryResult(
            candidate_profile_id=profile.id,
            assessment=assessment,
            plan=plan,
            policy_version=_MATCH_POLICY_VERSION,
            source_report=SourceReport(
                source_name=self._source.name,
                postings_received=len(postings),
            ),
            postings=postings,
            opportunities=opportunities,
            match_assessments=match_assessments_tuple,
            alignments_by_opportunity_id=alignments,
            shortlist=Shortlist(items=shortlist_items),
        )


def _opportunity_resolved_category(opportunity: Opportunity) -> JobCategory | None:
    category_reqs = _category_requirements(opportunity)
    if (
        len(category_reqs) == 1
        and category_reqs[0].is_resolved
        and isinstance(category_reqs[0].subject.value, JobCategory)
    ):
        return category_reqs[0].subject.value
    return None


def _assess_opportunity_career_alignment(
    opportunity: Opportunity,
    assessment: CandidateProfileAssessment,
) -> CandidateCareerAlignment:
    opp_category = _opportunity_resolved_category(opportunity)
    if opp_category is None:
        return CandidateCareerAlignment.REVIEW

    cat_assessment = assessment.get_assessment(opp_category)
    if cat_assessment is None:
        return CandidateCareerAlignment.REVIEW

    opportunity_levels: set[CandidateCareerLevel] = set()
    for requirement in _entry_requirements(opportunity):
        level = _career_level_for_requirement(requirement)
        if level is None:
            continue
        if not requirement.is_resolved:
            return CandidateCareerAlignment.REVIEW
        opportunity_levels.add(level)

    if not opportunity_levels or _career_levels_conflict(opportunity_levels):
        return CandidateCareerAlignment.REVIEW

    candidate_levels = set(cat_assessment.recommended_levels)
    if not candidate_levels or CandidateCareerLevel.UNKNOWN in candidate_levels:
        return CandidateCareerAlignment.REVIEW

    if opportunity_levels & candidate_levels:
        return CandidateCareerAlignment.MATCH

    is_early_career_candidate = candidate_levels <= {
            CandidateCareerLevel.JUNIOR,
            CandidateCareerLevel.INTERNSHIP,
    }
    if is_early_career_candidate and opportunity_levels & {
        CandidateCareerLevel.MID_LEVEL,
        CandidateCareerLevel.SENIOR,
    }:
        return CandidateCareerAlignment.ABOVE_PROFILE

    if (
        CandidateCareerLevel.SENIOR in candidate_levels
        and opportunity_levels
        <= {CandidateCareerLevel.INTERNSHIP, CandidateCareerLevel.JUNIOR}
    ):
        return CandidateCareerAlignment.BELOW_PROFILE

    return CandidateCareerAlignment.REVIEW


def _career_level_for_requirement(
    requirement: Requirement,
) -> CandidateCareerLevel | None:
    levels_by_subject = {
        RequirementSubject.seniority(Seniority.SENIOR): CandidateCareerLevel.SENIOR,
        RequirementSubject.seniority(Seniority.MID_LEVEL): CandidateCareerLevel.MID_LEVEL,
        RequirementSubject.seniority(Seniority.JUNIOR): CandidateCareerLevel.JUNIOR,
        RequirementSubject.entry_program(
            EntryProgram.INTERNSHIP
        ): CandidateCareerLevel.INTERNSHIP,
    }
    return levels_by_subject.get(requirement.subject)


def _career_levels_conflict(levels: set[CandidateCareerLevel]) -> bool:
    seniority_levels = levels - {CandidateCareerLevel.INTERNSHIP}
    return len(seniority_levels) > 1 or (
        CandidateCareerLevel.INTERNSHIP in levels
        and bool(
            seniority_levels
            & {CandidateCareerLevel.MID_LEVEL, CandidateCareerLevel.SENIOR}
        )
    )


def _ranked_automatic_shortlist_items(
    opportunities: tuple[Opportunity, ...],
    assessments_by_opportunity_id: dict[str, MatchAssessment],
    alignments_by_opportunity_id: dict[str, CandidateCareerAlignment],
    candidate_assessment: CandidateProfileAssessment,
    *,
    career_preference: CareerPreference | None,
) -> tuple[Opportunity, ...]:
    visible_opportunities = tuple(
        opp
        for opp in opportunities
        if assessments_by_opportunity_id[opp.id].eligibility_status
        is not EligibilityStatus.INELIGIBLE
    )

    def sort_key(opportunity: Opportunity) -> tuple[object, ...]:
        match_assessment = assessments_by_opportunity_id[opportunity.id]
        alignment = alignments_by_opportunity_id[opportunity.id]
        opp_category = _opportunity_resolved_category(opportunity)
        cat_assessment = (
            candidate_assessment.get_assessment(opp_category) if opp_category else None
        )
        cat_score = cat_assessment.profile_score if cat_assessment else 0
        latest_update = _latest_source_update_timestamp(opportunity)

        if career_preference is not None and match_assessment.career_preference_assessment:
            career_assessment = match_assessment.career_preference_assessment
            return (
                _ELIGIBILITY_ORDER[match_assessment.eligibility_status],
                _ALIGNMENT_ORDER[alignment],
                _CAREER_RECOMMENDATION_ORDER[career_assessment.recommendation],
                -match_assessment.fit_score.value,
                _CAREER_PRIORITY_ORDER[career_assessment.priority],
                -cat_score,
                0 if latest_update is not None else 1,
                -latest_update if latest_update is not None else 0.0,
                opportunity.id,
            )

        return (
            _ELIGIBILITY_ORDER[match_assessment.eligibility_status],
            _ALIGNMENT_ORDER[alignment],
            -match_assessment.fit_score.value,
            -cat_score,
            0 if latest_update is not None else 1,
            -latest_update if latest_update is not None else 0.0,
            opportunity.id,
        )

    return tuple(sorted(visible_opportunities, key=sort_key))


def _ranked_shortlist_items(
    opportunities: tuple[Opportunity, ...],
    assessments_by_opportunity_id: dict[str, MatchAssessment],
    *,
    career_preference: CareerPreference | None,
) -> tuple[Opportunity, ...]:
    visible_opportunities = (
        opportunity
        for opportunity in opportunities
        if assessments_by_opportunity_id[opportunity.id].eligibility_status
        is not EligibilityStatus.INELIGIBLE
    )
    if career_preference is None:
        return tuple(
            sorted(
                visible_opportunities,
                key=lambda opportunity: _shortlist_sort_key(
                    opportunity,
                    assessments_by_opportunity_id[opportunity.id],
                ),
            )
        )
    return tuple(
        sorted(
            visible_opportunities,
            key=lambda opportunity: _career_shortlist_sort_key(
                opportunity,
                assessments_by_opportunity_id[opportunity.id],
            ),
        )
    )


def _shortlist_sort_key(
    opportunity: Opportunity,
    assessment: MatchAssessment,
) -> tuple[int, int, int, float, str]:
    latest_update = _latest_source_update_timestamp(opportunity)
    return (
        _ELIGIBILITY_ORDER[assessment.eligibility_status],
        -assessment.fit_score.value,
        0 if latest_update is not None else 1,
        -latest_update if latest_update is not None else 0.0,
        opportunity.id,
    )


def _latest_source_update_timestamp(opportunity: Opportunity) -> float | None:
    known_updates = tuple(
        timestamp
        for posting in opportunity.postings
        if posting.source_updated_at is not None
        if (timestamp := _utc_timestamp(posting.source_updated_at)) is not None
    )
    return max(known_updates, default=None)


def _utc_timestamp(value: datetime) -> float | None:
    if value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(UTC).timestamp()


def _assess_opportunity(
    opportunity: Opportunity,
    profile: CandidateProfile,
    criteria: SearchCriteria,
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
            criteria=criteria,
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
        career_preference_assessment=(
            _assess_career_preference(criteria.career_preference, requirements)
            if criteria.career_preference is not None
            else None
        ),
    )


def _career_shortlist_sort_key(
    opportunity: Opportunity,
    assessment: MatchAssessment,
) -> tuple[int, int, int, int, int, float, str]:
    career_assessment = assessment.career_preference_assessment
    assert career_assessment is not None
    latest_update = _latest_source_update_timestamp(opportunity)
    return (
        _ELIGIBILITY_ORDER[assessment.eligibility_status],
        _CAREER_RECOMMENDATION_ORDER[career_assessment.recommendation],
        -assessment.fit_score.value,
        _CAREER_PRIORITY_ORDER[career_assessment.priority],
        0 if latest_update is not None else 1,
        -latest_update if latest_update is not None else 0.0,
        opportunity.id,
    )


def _assess_career_preference(
    preference: CareerPreference,
    requirements: tuple[Requirement, ...],
) -> CareerPreferenceAssessment:
    has_senior = any(
        requirement.subject == RequirementSubject.seniority(Seniority.SENIOR)
        for requirement in requirements
    )
    if has_senior:
        return CareerPreferenceAssessment(
            preference=preference,
            priority=CareerPriority.SENIOR,
            recommendation=CareerRecommendation.NOT_RECOMMENDED,
            policy_version=_CAREER_ENTRY_POLICY_VERSION,
            reason=(
                "A Opportunity possui sinal explícito de nível sênior, "
                "incompatível com início de carreira."
            ),
        )
    has_mid_level = any(
        requirement.subject == RequirementSubject.seniority(Seniority.MID_LEVEL)
        for requirement in requirements
    )
    if has_mid_level:
        return CareerPreferenceAssessment(
            preference=preference,
            priority=CareerPriority.MID_LEVEL,
            recommendation=CareerRecommendation.LOW_PRIORITY,
            policy_version=_CAREER_ENTRY_POLICY_VERSION,
            reason=(
                "A Opportunity possui sinal explícito de nível pleno, "
                "fora da prioridade de início de carreira."
            ),
        )
    has_internship = any(
        requirement.subject == RequirementSubject.entry_program(EntryProgram.INTERNSHIP)
        for requirement in requirements
    )
    if has_internship:
        return CareerPreferenceAssessment(
            preference=preference,
            priority=CareerPriority.INTERNSHIP,
            recommendation=CareerRecommendation.RECOMMENDED,
            policy_version=_CAREER_ENTRY_POLICY_VERSION,
            reason="A Opportunity possui sinal explícito de programa de estágio.",
        )
    has_junior = any(
        requirement.subject == RequirementSubject.seniority(Seniority.JUNIOR)
        for requirement in requirements
    )
    if has_junior:
        return CareerPreferenceAssessment(
            preference=preference,
            priority=CareerPriority.JUNIOR,
            recommendation=CareerRecommendation.RECOMMENDED,
            policy_version=_CAREER_ENTRY_POLICY_VERSION,
            reason="A Opportunity possui sinal explícito de nível júnior.",
        )
    has_trainee = any(
        requirement.subject == RequirementSubject.entry_program(EntryProgram.TRAINEE)
        for requirement in requirements
    )
    if has_trainee:
        return CareerPreferenceAssessment(
            preference=preference,
            priority=CareerPriority.TRAINEE,
            recommendation=CareerRecommendation.RECOMMENDED,
            policy_version=_CAREER_ENTRY_POLICY_VERSION,
            reason="A Opportunity possui sinal explícito de programa trainee.",
        )
    return CareerPreferenceAssessment(
        preference=preference,
        priority=CareerPriority.UNKNOWN,
        recommendation=CareerRecommendation.REVIEW,
        policy_version=_CAREER_ENTRY_POLICY_VERSION,
        reason="A Opportunity não possui nível de carreira explícito.",
    )


def _category_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    provenance_by_category: dict[JobCategory, set[Provenance]] = {}
    for posting in opportunity.postings:
        for category in _categories_in_title(posting.title):
            provenance_by_category.setdefault(category, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                )
            )

    if not provenance_by_category:
        return (
            Requirement(
                id="job-category:unknown",
                subject=RequirementSubject.job_category(None),
                statement="A JobCategory da Opportunity não pôde ser identificada.",
                dimension=FitDimension.JOB_CATEGORY,
                importance=RequirementImportance.UNKNOWN,
                provenance=tuple(
                    sorted(
                        (
                            Provenance(
                                origin=posting.source_name,
                                locator=f"{posting.external_id}#title",
                            )
                            for posting in opportunity.postings
                        ),
                        key=_provenance_sort_key,
                    )
                ),
                is_resolved=False,
            ),
        )

    is_resolved = len(provenance_by_category) == 1
    return tuple(
        Requirement(
            id=f"job-category:{category.value}",
            subject=RequirementSubject.job_category(category),
            statement=f"A Opportunity pertence à JobCategory {category.value}.",
            dimension=FitDimension.JOB_CATEGORY,
            importance=RequirementImportance.UNKNOWN,
            provenance=tuple(sorted(provenance_by_category[category], key=_provenance_sort_key)),
            is_resolved=is_resolved,
        )
        for category in sorted(provenance_by_category, key=lambda item: item.value)
    )


def _skill_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    provenance_by_skill: dict[str, set[Provenance]] = {}
    importances_by_skill: dict[str, set[RequirementImportance]] = {}
    for posting in opportunity.postings:
        for skill in _skills_in_text(posting.title):
            importances_by_skill.setdefault(skill, set()).add(RequirementImportance.UNKNOWN)
            provenance_by_skill.setdefault(skill, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                )
            )

        if posting.summary is None:
            continue
        for skill, importance in _skill_signals_in_explicit_context(posting.summary):
            importances_by_skill.setdefault(skill, set()).add(importance)
            provenance_by_skill.setdefault(skill, set()).add(
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#summary",
                )
            )

    return tuple(
        Requirement(
            id=f"skill:{skill}",
            subject=RequirementSubject.skill(skill),
            statement=f"A Opportunity menciona explicitamente a skill {skill}.",
            dimension=FitDimension.SKILLS,
            importance=_combined_importance(importances_by_skill[skill]),
            provenance=tuple(sorted(provenance_by_skill[skill], key=_provenance_sort_key)),
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


def _skill_signals_in_explicit_context(
    summary: str,
) -> set[tuple[str, RequirementImportance]]:
    signals: set[tuple[str, RequirementImportance]] = set()
    for clause, importance in _explicit_requirement_clauses(
        summary,
        context_terms=_SKILL_CONTEXT_TERMS,
    ):
        skills = _skills_in_text(clause)
        if len(skills) > 1:
            importance = _collective_skill_importance(clause, skills)
        signals.update((skill, importance) for skill in skills)
    return signals


def _collective_skill_importance(
    clause: str,
    skills: set[str],
) -> RequirementImportance:
    normalized_clause = _comparison_text(clause) or ""
    header, separator, listed_requirements = normalized_clause.partition(":")
    if not separator or _skills_in_text(header) or _skills_in_text(listed_requirements) != skills:
        return RequirementImportance.UNKNOWN
    return _importance_in_clause(header)


def _explicit_requirement_clauses(
    summary: str,
    *,
    context_terms: tuple[str, ...],
) -> tuple[tuple[str, RequirementImportance], ...]:
    clauses: list[tuple[str, RequirementImportance]] = []
    for clause in re.split(r"[.!?;\r\n]+", summary):
        normalized_clause = _comparison_text(clause) or ""
        if any(
            _contains_term(normalized_clause, term)
            for term in (
                *context_terms,
                *_BLOCKING_IMPORTANCE_TERMS,
                *_PREFERRED_IMPORTANCE_TERMS,
            )
        ):
            clauses.append((clause, _importance_in_clause(normalized_clause)))
    return tuple(clauses)


def _importance_in_clause(normalized_clause: str) -> RequirementImportance:
    without_negated_blocking = _NEGATED_BLOCKING_PATTERN.sub(" ", normalized_clause)

    has_blocking = any(
        _contains_term(without_negated_blocking, term) for term in _BLOCKING_IMPORTANCE_TERMS
    )
    has_preferred = any(
        _contains_term(normalized_clause, term) for term in _PREFERRED_IMPORTANCE_TERMS
    )
    if has_blocking == has_preferred:
        return RequirementImportance.UNKNOWN
    if has_blocking:
        return RequirementImportance.BLOCKING
    return RequirementImportance.PREFERRED


def _combined_importance(
    importances: set[RequirementImportance],
) -> RequirementImportance:
    explicit_importances = importances - {RequirementImportance.UNKNOWN}
    if len(explicit_importances) == 1:
        return next(iter(explicit_importances))
    return RequirementImportance.UNKNOWN


def _entry_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    signals = _RequirementSignals()
    for posting in opportunity.postings:
        for subject in _entry_subjects_in_title(posting.title):
            signals.record(
                subject,
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#title",
                ),
            )
        if posting.summary is None:
            continue
        for subject in _entry_subjects_in_summary(posting.summary):
            signals.record(
                subject,
                Provenance(
                    origin=posting.source_name,
                    locator=f"{posting.external_id}#summary",
                ),
            )

    return signals.to_requirements(FitDimension.ENTRY_PROGRAM_SENIORITY)


def _entry_subjects_in_title(title: str) -> set[RequirementSubject]:
    normalized = _comparison_text(title) or ""
    subjects = {
        RequirementSubject.entry_program(value)
        for value, aliases in _ENTRY_PROGRAM_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }
    subjects.update(
        RequirementSubject.seniority(value)
        for value, aliases in _SENIORITY_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    )
    return subjects


def _entry_subjects_in_summary(summary: str) -> set[RequirementSubject]:
    subjects: set[RequirementSubject] = set()
    normalized_summary = _summary_comparison_text(summary)
    for clause in re.split(r"[.!?;\r\n]+", normalized_summary):
        subjects.update(_entry_subjects_in_summary_clause(clause))
    return subjects


def _entry_subjects_in_summary_clause(clause: str) -> set[RequirementSubject]:
    normalized = _comparison_text_without_diacritics(clause)
    subjects = {
        RequirementSubject.entry_program(value)
        for value, contexts in _SUMMARY_ENTRY_PROGRAM_CONTEXTS.items()
        if any(_contains_term(normalized, context) for context in contexts)
    }
    subjects.update(
        RequirementSubject.entry_program(value)
        for value, contexts in _SUMMARY_ENTRY_PROGRAM_ROLE_CONTEXTS.items()
        if any(_role_context_is_explicit(normalized, context) for context in contexts)
    )
    subjects.update(
        RequirementSubject.seniority(value)
        for value, contexts in _SUMMARY_SENIORITY_CONTEXTS.items()
        if any(_contains_term(normalized, context) for context in contexts)
    )
    subjects.update(
        RequirementSubject.seniority(value)
        for value, aliases in _SENIORITY_ALIASES.items()
        if any(
            _seniority_role_context_is_explicit(normalized, role, alias)
            for role in _SUMMARY_SENIORITY_ROLES
            for alias in aliases
        )
    )
    return subjects


def _role_context_is_explicit(clause: str, role_context: str) -> bool:
    escaped = re.escape(role_context).replace(r"\ ", r"\s+")
    for match in re.finditer(rf"(?<!\w){escaped}(?!\w)", clause):
        if _role_occurrence_is_explicit(clause, match.start()):
            return True
    return False


def _seniority_role_context_is_explicit(
    clause: str,
    role: str,
    seniority: str,
) -> bool:
    escaped_role = re.escape(role).replace(r"\ ", r"\s+")
    escaped_seniority = re.escape(seniority).replace(r"\ ", r"\s+")
    qualifier = rf"(?P<qualifiers>(?:\s+[\w+#.-]+){{0,{_SUMMARY_ROLE_MAX_QUALIFIER_TOKENS}}})"
    pattern = rf"(?<!\w){escaped_role}{qualifier}\s+{escaped_seniority}(?!\w)"
    for match in re.finditer(pattern, clause):
        qualifier_tokens = tuple(re.findall(r"[\w+#.-]+", match["qualifiers"]))
        if not _summary_role_qualifiers_are_conservative(qualifier_tokens):
            continue
        if _role_occurrence_is_explicit(clause, match.start()):
            return True
    return False


def _summary_role_qualifiers_are_conservative(qualifier_tokens: tuple[str, ...]) -> bool:
    for index, token in enumerate(qualifier_tokens):
        if token in _SUMMARY_ROLE_QUALIFIER_BLOCKERS:
            return False
        if token in _SUMMARY_ROLE_QUALIFIER_CONNECTORS and (
            index == len(qualifier_tokens) - 1
            or qualifier_tokens[index + 1] in _SUMMARY_ROLE_QUALIFIER_BLOCKERS
            or qualifier_tokens[index + 1] in _SUMMARY_ROLE_QUALIFIER_CONNECTORS
        ):
            return False
    return True


def _role_occurrence_is_explicit(clause: str, start: int) -> bool:
    preceding_words = re.findall(r"\w+", clause[:start])
    if not preceding_words:
        return True
    for index in range(len(preceding_words) - 1, max(-1, len(preceding_words) - 5), -1):
        if preceding_words[index] not in _SUMMARY_ROLE_INTENT_TERMS:
            continue
        return all(
            word in _SUMMARY_ROLE_INTENT_LINK_TERMS
            for word in preceding_words[index + 1 :]
        )
    return False


def _summary_comparison_text(value: str) -> str:
    parser = _SummaryTextExtractor()
    parser.feed(unescape(value))
    parser.close()
    return _comparison_text_without_diacritics("".join(parser.parts))


def _comparison_text_without_diacritics(value: str) -> str:
    normalized = _comparison_text(value) or ""
    return "".join(
        character
        for character in normalize_unicode("NFD", normalized)
        if not combining(character)
    )


def _location_requirements(opportunity: Opportunity) -> tuple[Requirement, ...]:
    signals = _RequirementSignals()
    normalized_locations_by_city: dict[
        str,
        list[tuple[NormalizedLocation, Provenance]],
    ] = {}
    for posting in opportunity.postings:
        if posting.location is not None:
            workplace_modes = _workplace_modes_in_text(posting.location)
            normalized_location = normalize_location(posting.location)
            if normalized_location.city and not workplace_modes:
                normalized_locations_by_city.setdefault(
                    normalized_location.city,
                    [],
                ).append(
                    (
                        normalized_location,
                        Provenance(
                            origin=posting.source_name,
                            locator=f"{posting.external_id}#location",
                        ),
                    )
                )
            for mode in workplace_modes:
                signals.record(
                    RequirementSubject.workplace_mode(mode),
                    Provenance(
                        origin=posting.source_name,
                        locator=f"{posting.external_id}#location",
                    ),
                )

        if posting.summary is not None:
            for mode, importance in _workplace_mode_signals_in_explicit_context(posting.summary):
                signals.record(
                    RequirementSubject.workplace_mode(mode),
                    Provenance(
                        origin=posting.source_name,
                        locator=f"{posting.external_id}#summary",
                    ),
                    importance=importance,
                )

    for city, locations_with_provenance in normalized_locations_by_city.items():
        explicit_states = {
            location.state
            for location, _ in locations_with_provenance
            if location.state is not None
        }
        if len(explicit_states) <= 1:
            merged_location = NormalizedLocation(
                city=city,
                state=min(explicit_states, default=None),
            )
            merged_subject = RequirementSubject.location(merged_location.canonical_value)
            for _, provenance in locations_with_provenance:
                signals.record(merged_subject, provenance)
            continue

        for location, provenance in locations_with_provenance:
            signals.record(
                RequirementSubject.location(location.canonical_value),
                provenance,
            )

    return signals.to_requirements(FitDimension.LOCATION_WORKPLACE_MODE)


def _workplace_modes_in_text(value: str) -> set[WorkplaceMode]:
    normalized = _comparison_text(value) or ""
    return {
        mode
        for mode, aliases in _WORKPLACE_MODE_ALIASES.items()
        if any(_contains_term(normalized, alias) for alias in aliases)
    }


def _workplace_mode_signals_in_explicit_context(
    summary: str,
) -> set[tuple[WorkplaceMode, RequirementImportance]]:
    signals: set[tuple[WorkplaceMode, RequirementImportance]] = set()
    for clause, importance in _explicit_requirement_clauses(
        summary,
        context_terms=_WORKPLACE_CONTEXT_TERMS,
    ):
        modes = _workplace_modes_in_text(clause)
        if len(modes) > 1 or _skills_in_text(clause):
            importance = RequirementImportance.UNKNOWN
        signals.update((mode, importance) for mode in modes)
    return signals


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
    criteria: SearchCriteria,
    maximum_points: int,
) -> RequirementAssessment:
    evidence = tuple(
        sorted(
            (
                *_matching_profile_evidence(requirement, profile),
                *_derived_category_evidence(requirement, profile),
                *_derived_search_criteria_evidence(requirement, criteria),
            ),
            key=_evidence_sort_key,
        )
    )
    assertions = {item.assertion for item in evidence}
    if not requirement.is_resolved:
        status = RequirementStatus.UNKNOWN
    elif assertions == {EvidenceAssertion.SUPPORTS}:
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
        and (
            isinstance(evidence.subject.value, str)
            and isinstance(requirement.subject.value, str)
            and locations_equivalent(evidence.subject.value, requirement.subject.value)
            if requirement.subject.kind is RequirementKind.LOCATION
            else _comparison_text(evidence.subject.value)
            == _comparison_text(requirement.subject.value)
        )
    )


def _derived_category_evidence(
    requirement: Requirement,
    profile: CandidateProfile,
) -> tuple[Evidence, ...]:
    if requirement.subject.kind is not RequirementKind.JOB_CATEGORY:
        return ()

    subject_value = requirement.subject.value
    if not isinstance(subject_value, JobCategory):
        return ()
    category = subject_value
    if category not in profile.target_categories:
        return ()

    return (
        Evidence(
            id=f"candidate-profile:target-category:{category.value}",
            subject=requirement.subject,
            statement=f"CandidateProfile declara {category.value} em target_categories.",
            assertion=EvidenceAssertion.SUPPORTS,
            provenance=Provenance(
                origin="candidate-profile",
                locator="target_categories",
            ),
        ),
    )


def _derived_search_criteria_evidence(
    requirement: Requirement,
    criteria: SearchCriteria,
) -> tuple[Evidence, ...]:
    if requirement.subject.kind is not RequirementKind.LOCATION:
        return ()

    subject_value = requirement.subject.value
    if not isinstance(subject_value, str) or not locations_equivalent(
        subject_value,
        criteria.location,
    ):
        return ()

    return (
        Evidence(
            id="search-criteria:location",
            subject=requirement.subject,
            statement=(
                f"A execução da busca solicita oportunidades em {criteria.location}; "
                "isso não declara residência do Candidate."
            ),
            assertion=EvidenceAssertion.SUPPORTS,
            provenance=Provenance(
                origin="search-criteria",
                locator="location",
            ),
        ),
    )


def _point_allocations(requirements: tuple[Requirement, ...]) -> dict[str, int]:
    allocations: dict[str, int] = {}
    for dimension, weight in _DIMENSION_WEIGHTS:
        dimension_requirements = tuple(
            requirement for requirement in requirements if requirement.dimension is dimension
        )
        if not dimension_requirements:
            continue
        base_points, remainder = divmod(weight, len(dimension_requirements))
        for index, requirement in enumerate(dimension_requirements):
            allocations[requirement.id] = base_points + (index < remainder)
    return allocations


def _requirement_sort_key(requirement: Requirement) -> tuple[int, str, str]:
    dimension_order = {dimension: index for index, (dimension, _) in enumerate(_DIMENSION_WEIGHTS)}
    return (
        dimension_order[requirement.dimension],
        requirement.subject.kind.value,
        requirement.subject.value or "",
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
            key=lambda group: min((posting.source_name, posting.external_id) for posting in group),
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
