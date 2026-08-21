"""Interface profunda para descobrir e organizar oportunidades."""

from dataclasses import dataclass
from typing import Protocol

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
        opportunities = tuple(_to_opportunity(posting) for posting in postings)

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


def _to_opportunity(posting: JobPosting) -> Opportunity:
    return Opportunity(
        id=f"{posting.source_name}:{posting.external_id}",
        title=_normalize_required_text(posting.title),
        company=_normalize_optional_text(posting.company),
        location=_normalize_optional_text(posting.location),
        source_url=_normalize_required_text(posting.source_url),
        postings=(posting,),
    )


def _normalize_required_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_required_text(value)
    return normalized or None
