"""Interface profunda para descobrir e organizar oportunidades."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol
from unicodedata import normalize as normalize_unicode
from urllib.parse import urlsplit, urlunsplit

from buscador_de_vaga.domain import (
    CandidateProfile,
    JobCategory,
    JobPosting,
    JobSourceQuery,
    Opportunity,
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
    shortlist: Shortlist


_CATEGORY_SEARCH_TERMS: dict[JobCategory, str] = {
    JobCategory.SOFTWARE_DEVELOPMENT: "desenvolvedor de software",
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: "suporte de TI infraestrutura",
    JobCategory.SYSTEMS: "analista de sistemas",
    JobCategory.QUALITY_ASSURANCE: "qualidade de software QA",
    JobCategory.DATA: "analista de dados",
}

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

        return DiscoveryResult(
            candidate_profile_id=profile.id,
            criteria=criteria,
            source_report=SourceReport(
                source_name=self._source.name,
                postings_received=len(postings),
            ),
            postings=postings,
            opportunities=opportunities,
            shortlist=Shortlist(items=opportunities),
        )


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
