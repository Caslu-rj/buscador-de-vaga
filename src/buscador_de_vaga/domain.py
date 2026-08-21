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


class EvidenceAssertion(StrEnum):
    """Direção explícita de uma Evidence em relação a um Requirement."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class RequirementImportance(StrEnum):
    """Importância declarada ou inferida de um Requirement."""

    BLOCKING = "blocking"
    PREFERRED = "preferred"
    UNKNOWN = "unknown"


class RequirementStatus(StrEnum):
    """Conclusão ternária sustentada pelas Evidence disponíveis."""

    MET = "met"
    UNMET = "unmet"
    UNKNOWN = "unknown"


class FitDimension(StrEnum):
    """Eixos versionados da política inicial de compatibilidade."""

    JOB_CATEGORY = "job-category"
    SKILLS = "skills"
    ENTRY_PROGRAM_SENIORITY = "entry-program-seniority"
    LOCATION_WORKPLACE_MODE = "location-workplace-mode"


class RequirementKind(StrEnum):
    """Natureza canônica de um Requirement dentro de uma FitDimension."""

    JOB_CATEGORY = "job-category"
    SKILL = "skill"
    ENTRY_PROGRAM = "entry-program"
    SENIORITY = "seniority"
    LOCATION = "location"
    WORKPLACE_MODE = "workplace-mode"


@dataclass(frozen=True, slots=True)
class Provenance:
    """Origem e localizador suficientes para auditar um fato."""

    origin: str
    locator: str


@dataclass(frozen=True, slots=True)
class RequirementSubject:
    """Identidade tipada e canônica compartilhada por Requirement e Evidence."""

    kind: RequirementKind
    value: str


@dataclass(frozen=True, slots=True)
class Evidence:
    """Fato verificável favorável ou contrário a um Requirement."""

    id: str
    subject: RequirementSubject
    statement: str
    assertion: EvidenceAssertion
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """Recorte inicial do perfil privado usado na descoberta."""

    id: str
    target_categories: tuple[JobCategory, ...]
    evidence: tuple[Evidence, ...] = ()


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
class Requirement:
    """Condição avaliável identificada em uma Opportunity."""

    id: str
    subject: RequirementSubject
    statement: str
    dimension: FitDimension
    importance: RequirementImportance
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class RequirementAssessment:
    """Conclusão explicável sobre um Requirement e seus pontos."""

    requirement: Requirement
    status: RequirementStatus
    evidence: tuple[Evidence, ...]
    maximum_points: int
    awarded_points: int
    covered_points: int


@dataclass(frozen=True, slots=True)
class FitBreakdown:
    """Parcela observável do FitScore para uma FitDimension."""

    dimension: FitDimension
    weight: int
    awarded_points: int
    covered_weight: int


@dataclass(frozen=True, slots=True)
class FitScore:
    """Score versionado acompanhado de cobertura e breakdown."""

    value: int
    evidence_coverage: int
    policy_version: str
    breakdown: tuple[FitBreakdown, ...]


@dataclass(frozen=True, slots=True)
class SkillGap:
    """Skill comprovadamente não atendida por Evidence contrária."""

    requirement: Requirement
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class MatchAssessment:
    """Avaliação determinística e auditável de uma Opportunity."""

    opportunity_id: str
    requirement_assessments: tuple[RequirementAssessment, ...]
    fit_score: FitScore

    @property
    def strengths(self) -> tuple[RequirementAssessment, ...]:
        return tuple(
            assessment
            for assessment in self.requirement_assessments
            if assessment.status is RequirementStatus.MET
        )

    @property
    def skill_gaps(self) -> tuple[SkillGap, ...]:
        return tuple(
            SkillGap(
                requirement=assessment.requirement,
                evidence=assessment.evidence,
            )
            for assessment in self.requirement_assessments
            if assessment.requirement.dimension is FitDimension.SKILLS
            and assessment.status is RequirementStatus.UNMET
        )

    @property
    def unknown_requirements(self) -> tuple[RequirementAssessment, ...]:
        return tuple(
            assessment
            for assessment in self.requirement_assessments
            if assessment.status is RequirementStatus.UNKNOWN
        )


@dataclass(frozen=True, slots=True)
class Shortlist:
    """Seleção ordenada produzida pela descoberta."""

    items: tuple[Opportunity, ...]
