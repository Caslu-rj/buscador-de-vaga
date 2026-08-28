"""Política determinística para recomendar oportunidades à candidatura."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from buscador_de_vaga.candidate_positioning import CandidateCareerAlignment
from buscador_de_vaga.domain import EligibilityStatus, MatchAssessment

APPLICATION_CANDIDATE_POLICY_VERSION: Final = "application-candidate-v1"
APPLICATION_CANDIDATE_MIN_FIT_SCORE: Final = 80


class ApplicationCandidateStatus(StrEnum):
    """Decisão sobre o próximo passo de uma Opportunity elegível."""

    READY = "ready"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ApplicationCandidate:
    """Recomendação auditável sem executar uma candidatura."""

    opportunity_id: str
    status: ApplicationCandidateStatus
    fit_score: int
    reason: str
    policy_version: str = APPLICATION_CANDIDATE_POLICY_VERSION


def select_application_candidates(
    match_assessments: tuple[MatchAssessment, ...],
    *,
    alignments_by_opportunity_id: Mapping[str, CandidateCareerAlignment] | None = None,
) -> tuple[ApplicationCandidate, ...]:
    """Seleciona recomendações manuais ou automáticas sem recalcular matching."""
    candidates: list[ApplicationCandidate] = []
    for assessment in match_assessments:
        if (
            assessment.fit_score.value < APPLICATION_CANDIDATE_MIN_FIT_SCORE
            or assessment.eligibility_status is not EligibilityStatus.ELIGIBLE
            or assessment.blocking_requirements
        ):
            continue

        if alignments_by_opportunity_id is None:
            status = ApplicationCandidateStatus.READY
            reason = (
                f"FitScore {assessment.fit_score.value}, elegibilidade confirmada "
                "e critérios do fluxo manual atendidos."
            )
        else:
            alignment = alignments_by_opportunity_id.get(assessment.opportunity_id)
            if alignment is CandidateCareerAlignment.MATCH:
                status = ApplicationCandidateStatus.READY
                reason = (
                    f"FitScore {assessment.fit_score.value}, elegibilidade confirmada "
                    "e alinhamento de carreira compatível."
                )
            elif alignment is CandidateCareerAlignment.REVIEW:
                status = ApplicationCandidateStatus.REVIEW
                reason = (
                    f"FitScore {assessment.fit_score.value} e elegibilidade confirmada, "
                    "mas o nível da vaga requer revisão."
                )
            elif alignment is CandidateCareerAlignment.BELOW_PROFILE:
                status = ApplicationCandidateStatus.REVIEW
                reason = (
                    f"FitScore {assessment.fit_score.value} e elegibilidade confirmada, "
                    "mas o nível da vaga está abaixo do perfil e requer revisão."
                )
            else:
                continue

        candidates.append(
            ApplicationCandidate(
                opportunity_id=assessment.opportunity_id,
                status=status,
                fit_score=assessment.fit_score.value,
                reason=reason,
            )
        )

    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                0 if candidate.status is ApplicationCandidateStatus.READY else 1,
                -candidate.fit_score,
                candidate.opportunity_id,
            ),
        )
    )
