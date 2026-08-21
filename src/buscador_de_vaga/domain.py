"""Vocabulário público do domínio de descoberta de vagas."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobCategory(StrEnum):
    """Categorias profissionais reconhecidas no primeiro marco."""

    SOFTWARE_DEVELOPMENT = "software-development"
    IT_SUPPORT_INFRASTRUCTURE = "it-support-infrastructure"
    SYSTEMS = "systems"
    QUALITY_ASSURANCE = "quality-assurance"
    DATA = "data"


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """Recorte inicial do perfil privado usado na descoberta."""

    id: str
    target_categories: tuple[JobCategory, ...]


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """Escopo explícito de uma execução de descoberta."""

    category: JobCategory
    location: str
    limit: int = 10


@dataclass(frozen=True, slots=True)
class JobSourceQuery:
    """Consulta independente de fornecedor enviada a um JobSource."""

    keywords: str
    location: str
    limit: int


@dataclass(frozen=True, slots=True)
class JobPosting:
    """Publicação preservada como recebida de um JobSource."""

    source_name: str
    external_id: str
    title: str
    company: str | None
    location: str | None
    source_url: str
    collected_at: datetime
    summary: str | None = None
    source_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Opportunity:
    """Vaga lógica normalizada apresentada ao Candidate."""

    id: str
    title: str
    company: str | None
    location: str | None
    source_url: str
    postings: tuple[JobPosting, ...]


@dataclass(frozen=True, slots=True)
class Shortlist:
    """Seleção ordenada produzida pela descoberta."""

    items: tuple[Opportunity, ...]
