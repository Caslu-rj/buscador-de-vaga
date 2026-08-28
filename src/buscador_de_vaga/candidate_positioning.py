"""Posicionamento automático do perfil do candidato e avaliação por categoria."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from buscador_de_vaga.domain import (
    CandidateProfile,
    EntryProgram,
    Evidence,
    EvidenceAssertion,
    JobCategory,
    JobSourceQuery,
    RequirementKind,
    Seniority,
)

POSITIONING_POLICY_VERSION = "candidate-positioning-v1"
AUTOMATIC_CATEGORY_SELECTION_THRESHOLD: Final = 20
MAX_AUTOMATIC_CATEGORIES: Final = 3
MAX_AUTOMATIC_QUERIES: Final = 6


class CandidateCareerLevel(StrEnum):
    """Nível de carreira inferido para o candidato em uma categoria."""

    INTERNSHIP = "internship"
    JUNIOR = "junior"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"
    UNKNOWN = "unknown"


class CandidateProfileConfidence(StrEnum):
    """Nível de confiança da avaliação de compatibilidade do perfil."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class CandidateCareerAlignment(StrEnum):
    """Alinhamento entre o nível da oportunidade e a recomendação do candidato."""

    MATCH = "match"
    REVIEW = "review"
    ABOVE_PROFILE = "above-profile"
    BELOW_PROFILE = "below-profile"


@dataclass(frozen=True, slots=True)
class CandidateCategoryAssessment:
    """Avaliação de posicionamento do candidato para uma JobCategory específica."""

    category: JobCategory
    profile_score: int
    confidence: CandidateProfileConfidence
    recommended_levels: tuple[CandidateCareerLevel, ...]
    evidence_ids: tuple[str, ...]
    reason: str
    policy_version: str = POSITIONING_POLICY_VERSION


@dataclass(frozen=True, slots=True)
class CandidateProfileAssessment:
    """Avaliação completa do perfil do candidato cobrindo todas as categorias."""

    profile_id: str
    policy_version: str
    category_assessments: tuple[CandidateCategoryAssessment, ...]
    legacy_target_categories: tuple[JobCategory, ...] = ()

    def get_assessment(self, category: JobCategory) -> CandidateCategoryAssessment | None:
        for assessment in self.category_assessments:
            if assessment.category is category:
                return assessment
        return None

    @property
    def selected_categories(self) -> tuple[JobCategory, ...]:
        """Categorias recomendadas ordenadas por profile_score (máximo 3)."""
        qualifying = [
            assessment
            for assessment in self.category_assessments
            if assessment.profile_score >= AUTOMATIC_CATEGORY_SELECTION_THRESHOLD
        ]
        if not qualifying:
            qualifying = [
                assessment
                for assessment in self.category_assessments
                if assessment.category in self.legacy_target_categories
            ]
        sorted_assessments = sorted(
            qualifying,
            key=lambda item: (-item.profile_score, item.category.value),
        )
        return tuple(
            item.category for item in sorted_assessments[:MAX_AUTOMATIC_CATEGORIES]
        )


@dataclass(frozen=True, slots=True)
class AutomaticSearchTarget:
    """Categoria e níveis que fundamentam uma parcela do plano automático."""

    category: JobCategory
    recommended_levels: tuple[CandidateCareerLevel, ...]


@dataclass(frozen=True, slots=True)
class AutomaticSearchPlan:
    """Plano auditável derivado do posicionamento do perfil do candidato."""

    targets: tuple[AutomaticSearchTarget, ...]
    queries: tuple[JobSourceQuery, ...]
    policy_version: str = POSITIONING_POLICY_VERSION


_CATEGORY_SKILLS: dict[JobCategory, set[str]] = {
    JobCategory.SOFTWARE_DEVELOPMENT: {
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "flask",
        "django",
        "fastapi",
        "git",
    },
    JobCategory.DATA: {
        "sql",
        "python",
    },
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: {
        "linux",
        "docker",
        "aws",
        "azure",
        "gcp",
        "git",
    },
    JobCategory.SYSTEMS: {
        "sql",
        "python",
        "git",
    },
    JobCategory.QUALITY_ASSURANCE: set(),
}


def assess_candidate_profile(profile: CandidateProfile) -> CandidateProfileAssessment:
    """Avalia o CandidateProfile em TODAS as JobCategory conhecidas."""
    supports_evidence = tuple(
        ev for ev in profile.evidence if ev.assertion is EvidenceAssertion.SUPPORTS
    )
    category_evidence = tuple(
        ev
        for ev in supports_evidence
        if ev.subject.kind is RequirementKind.JOB_CATEGORY
        and isinstance(ev.subject.value, JobCategory)
    )
    explicit_categories = frozenset(
        ev.subject.value
        for ev in category_evidence
        if isinstance(ev.subject.value, JobCategory)
    )
    level_evidence = tuple(
        ev
        for ev in supports_evidence
        if (
            ev.subject.kind is RequirementKind.SENIORITY
            and isinstance(ev.subject.value, Seniority)
        )
        or (
            ev.subject.kind is RequirementKind.ENTRY_PROGRAM
            and ev.subject.value is EntryProgram.INTERNSHIP
        )
    )
    has_category_or_skill_evidence = any(
        ev.subject.kind in {RequirementKind.JOB_CATEGORY, RequirementKind.SKILL}
        for ev in supports_evidence
    )

    assessments: list[CandidateCategoryAssessment] = []

    for category in JobCategory:
        category_ev_ids: list[str] = []

        # 1. JobCategory evidence score (60 pts)
        category_evidences = tuple(
            ev for ev in category_evidence if ev.subject.value is category
        )
        has_category_ev = bool(category_evidences)
        category_ev_ids.extend(ev.id for ev in category_evidences)

        category_score = 60 if has_category_ev else 0

        # 2. Skill evidence score (10 pts per matching skill, max 30)
        matching_skill_names: list[str] = []
        for ev in supports_evidence:
            if ev.subject.kind is RequirementKind.SKILL and isinstance(
                ev.subject.value, str
            ):
                skill_name = ev.subject.value.casefold()
                if skill_name in _CATEGORY_SKILLS[category]:
                    if skill_name not in matching_skill_names:
                        matching_skill_names.append(skill_name)
                    if ev.id not in category_ev_ids:
                        category_ev_ids.append(ev.id)

        skill_score = min(30, 10 * len(matching_skill_names))

        # 3. target_categories score (10 pts)
        is_target = category in profile.target_categories
        target_score = 10 if is_target else 0

        total_score = min(100, category_score + skill_score + target_score)

        # Confidence calculation
        if total_score >= 70:
            confidence = CandidateProfileConfidence.HIGH
        elif total_score >= 40:
            confidence = CandidateProfileConfidence.MEDIUM
        elif total_score > 0:
            confidence = CandidateProfileConfidence.LOW
        else:
            confidence = CandidateProfileConfidence.NONE

        applicable_level_evidence = _level_evidence_for_category(
            category=category,
            category_evidence=category_evidence,
            explicit_categories=explicit_categories,
            level_evidence=level_evidence,
            target_categories=profile.target_categories,
        )
        explicit_seniorities = {
            ev.subject.value
            for ev in applicable_level_evidence
            if ev.subject.kind is RequirementKind.SENIORITY
            and isinstance(ev.subject.value, Seniority)
        }
        has_internship = any(
            ev.subject.kind is RequirementKind.ENTRY_PROGRAM
            and ev.subject.value is EntryProgram.INTERNSHIP
            for ev in applicable_level_evidence
        )
        is_seniority_conflict = (
            len(explicit_seniorities) > 1
            or (
                has_internship
                and bool(explicit_seniorities & {Seniority.MID_LEVEL, Seniority.SENIOR})
            )
        )

        reasons: list[str] = []
        rec_levels: tuple[CandidateCareerLevel, ...]
        base_evidence_ids = tuple(sorted(set(category_ev_ids)))

        if total_score == 0:
            rec_levels = (CandidateCareerLevel.UNKNOWN,)
            used_ev_ids = base_evidence_ids
            reasons.append("Perfil sem evidência aplicável para esta categoria.")
        elif applicable_level_evidence:
            used_ev_ids = base_evidence_ids + tuple(
                ev.id
                for ev in sorted(applicable_level_evidence, key=lambda item: item.id)
                if ev.id not in base_evidence_ids
            )

            if is_seniority_conflict:
                rec_levels = (CandidateCareerLevel.UNKNOWN,)
                reasons.append(
                    "Sinais explícitos conflitantes de senioridade no perfil "
                    "para esta categoria."
                )
            else:
                rec_list: list[CandidateCareerLevel] = []
                if Seniority.JUNIOR in explicit_seniorities:
                    rec_list.append(CandidateCareerLevel.JUNIOR)
                elif Seniority.MID_LEVEL in explicit_seniorities:
                    rec_list.append(CandidateCareerLevel.MID_LEVEL)
                elif Seniority.SENIOR in explicit_seniorities:
                    rec_list.append(CandidateCareerLevel.SENIOR)

                if has_internship:
                    rec_list.append(CandidateCareerLevel.INTERNSHIP)

                rec_levels = tuple(rec_list)
                reasons.append(
                    f"Níveis {', '.join(level.value for level in rec_levels)} "
                    "recomendados com base em evidência explícita do perfil."
                )
        else:
            used_ev_ids = base_evidence_ids
            rec_levels = (
                CandidateCareerLevel.JUNIOR,
                CandidateCareerLevel.INTERNSHIP,
            )
            reasons.append(
                "Recomendação conservadora de início de carreira (Júnior, Estágio) "
                "devido à ausência de evidência explícita de senioridade."
            )

        category_assessment = CandidateCategoryAssessment(
            category=category,
            profile_score=total_score,
            confidence=confidence,
            recommended_levels=rec_levels,
            evidence_ids=used_ev_ids,
            reason=" ".join(reasons),
            policy_version=POSITIONING_POLICY_VERSION,
        )
        assessments.append(category_assessment)

    return CandidateProfileAssessment(
        profile_id=profile.id,
        policy_version=POSITIONING_POLICY_VERSION,
        category_assessments=tuple(assessments),
        legacy_target_categories=(
            () if has_category_or_skill_evidence else profile.target_categories
        ),
    )


def _level_evidence_for_category(
    *,
    category: JobCategory,
    category_evidence: tuple[Evidence, ...],
    explicit_categories: frozenset[JobCategory],
    level_evidence: tuple[Evidence, ...],
    target_categories: tuple[JobCategory, ...],
) -> tuple[Evidence, ...]:
    applicable: list[Evidence] = []
    for level in level_evidence:
        categories_at_same_provenance = {
            evidence.subject.value
            for evidence in category_evidence
            if evidence.provenance == level.provenance
            and isinstance(evidence.subject.value, JobCategory)
        }
        if categories_at_same_provenance:
            if category in categories_at_same_provenance:
                applicable.append(level)
            continue

        if len(explicit_categories) == 1 and category in explicit_categories:
            applicable.append(level)
            continue

        if (
            not explicit_categories
            and len(target_categories) == 1
            and category is target_categories[0]
        ):
            applicable.append(level)

    return tuple(applicable)
