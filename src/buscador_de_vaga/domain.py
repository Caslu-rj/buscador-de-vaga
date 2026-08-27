"""Vocabulário público do domínio de descoberta de vagas."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Self


class JobCategory(StrEnum):
    """Categorias profissionais reconhecidas no primeiro marco."""

    SOFTWARE_DEVELOPMENT = "software-development"
    IT_SUPPORT_INFRASTRUCTURE = "it-support-infrastructure"
    SYSTEMS = "systems"
    QUALITY_ASSURANCE = "quality-assurance"
    DATA = "data"


class CareerPreference(StrEnum):
    """Preferências de carreira que podem orientar a ordenação."""

    ENTRY_LEVEL = "entry-level"


class CareerPriority(StrEnum):
    """Classificação observável de nível para uma preferência de carreira."""

    INTERNSHIP = "internship"
    JUNIOR = "junior"
    TRAINEE = "trainee"
    UNKNOWN = "unknown"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"


class CareerRecommendation(StrEnum):
    """Recomendação separada de elegibilidade e compatibilidade técnica."""

    RECOMMENDED = "recommended"
    REVIEW = "review"
    LOW_PRIORITY = "low-priority"
    NOT_RECOMMENDED = "not-recommended"


class EntryProgram(StrEnum):
    """Programas de entrada reconhecidos pela política inicial."""

    APPRENTICESHIP = "apprenticeship"
    INTERNSHIP = "internship"
    TRAINEE = "trainee"


class Seniority(StrEnum):
    """Níveis de senioridade reconhecidos pela política inicial."""

    JUNIOR = "junior"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"


class WorkplaceMode(StrEnum):
    """Modalidades de trabalho reconhecidas pela política inicial."""

    HYBRID = "hybrid"
    ONSITE = "onsite"
    REMOTE = "remote"


type RequirementSubjectValue = JobCategory | EntryProgram | Seniority | WorkplaceMode | str


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


class EligibilityStatus(StrEnum):
    """Conclusão de elegibilidade separada do FitScore."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


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
    value: RequirementSubjectValue | None

    def __post_init__(self) -> None:
        if self.value is None:
            return
        if not self.value or self.value != self.value.strip():
            raise ValueError("RequirementSubject requer value canônico não vazio")
        try:
            if self.kind is RequirementKind.JOB_CATEGORY:
                typed_value: RequirementSubjectValue = JobCategory(self.value)
            elif self.kind is RequirementKind.ENTRY_PROGRAM:
                typed_value = EntryProgram(self.value)
            elif self.kind is RequirementKind.SENIORITY:
                typed_value = Seniority(self.value)
            elif self.kind is RequirementKind.WORKPLACE_MODE:
                typed_value = WorkplaceMode(self.value)
            elif isinstance(self.value, StrEnum):
                raise ValueError
            else:
                typed_value = self.value
        except ValueError:
            raise ValueError(
                f"{self.value!r} não é válido para RequirementKind {self.kind.value}"
            ) from None
        object.__setattr__(self, "value", typed_value)

    @classmethod
    def job_category(cls, value: JobCategory | None) -> Self:
        return cls(
            kind=RequirementKind.JOB_CATEGORY,
            value=value,
        )

    @classmethod
    def skill(cls, value: str) -> Self:
        return cls(kind=RequirementKind.SKILL, value=value)

    @classmethod
    def entry_program(cls, value: EntryProgram) -> Self:
        return cls(kind=RequirementKind.ENTRY_PROGRAM, value=value)

    @classmethod
    def seniority(cls, value: Seniority) -> Self:
        return cls(kind=RequirementKind.SENIORITY, value=value)

    @classmethod
    def location(cls, value: str) -> Self:
        return cls(kind=RequirementKind.LOCATION, value=value)

    @classmethod
    def workplace_mode(cls, value: WorkplaceMode) -> Self:
        return cls(kind=RequirementKind.WORKPLACE_MODE, value=value)

    @property
    def resolved_value(self) -> str:
        if self.value is None:
            raise ValueError("RequirementSubject não resolvido não possui value")
        if isinstance(self.value, StrEnum):
            return self.value.value
        return self.value


@dataclass(frozen=True, slots=True)
class Evidence:
    """Fato verificável favorável ou contrário a um Requirement."""

    id: str
    subject: RequirementSubject
    statement: str
    assertion: EvidenceAssertion
    provenance: Provenance

    def __post_init__(self) -> None:
        if self.subject.value is None:
            raise ValueError("Evidence requer um RequirementSubject resolvido")


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
    career_preference: CareerPreference | None = None


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
    is_resolved: bool = True

    def __post_init__(self) -> None:
        if self.is_resolved and self.subject.value is None:
            raise ValueError("Requirement resolvido requer subject value")


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
class BlockingRequirement:
    """Requirement impeditivo comprovadamente não atendido."""

    assessment: RequirementAssessment


@dataclass(frozen=True, slots=True)
class PossibleBlocker:
    """Requirement que ainda pode impedir a Opportunity."""

    assessment: RequirementAssessment


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
class CareerPreferenceAssessment:
    """Aplicação auditável de uma política de preferência de carreira."""

    preference: CareerPreference
    priority: CareerPriority
    recommendation: CareerRecommendation
    policy_version: str
    reason: str


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
    career_preference_assessment: CareerPreferenceAssessment | None = None

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

    @property
    def blocking_requirements(self) -> tuple[BlockingRequirement, ...]:
        return tuple(
            BlockingRequirement(assessment=assessment)
            for assessment in self.requirement_assessments
            if assessment.requirement.importance is RequirementImportance.BLOCKING
            and assessment.status is RequirementStatus.UNMET
            and bool(assessment.evidence)
            and all(
                evidence.assertion is EvidenceAssertion.CONTRADICTS
                for evidence in assessment.evidence
            )
        )

    @property
    def possible_blockers(self) -> tuple[PossibleBlocker, ...]:
        return tuple(
            PossibleBlocker(assessment=assessment)
            for assessment in self.requirement_assessments
            if assessment.status is not RequirementStatus.MET
            and assessment.requirement.importance is not RequirementImportance.PREFERRED
            and not (
                assessment.requirement.importance is RequirementImportance.BLOCKING
                and assessment.status is RequirementStatus.UNMET
            )
        )

    @property
    def eligibility_status(self) -> EligibilityStatus:
        if self.blocking_requirements:
            return EligibilityStatus.INELIGIBLE
        if self.possible_blockers:
            return EligibilityStatus.UNCERTAIN
        return EligibilityStatus.ELIGIBLE


@dataclass(frozen=True, slots=True)
class Shortlist:
    """Seleção ordenada produzida pela descoberta."""

    items: tuple[Opportunity, ...]
