from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from buscador_de_vaga.application_candidate import (
    APPLICATION_CANDIDATE_MIN_FIT_SCORE,
    APPLICATION_CANDIDATE_POLICY_VERSION,
    ApplicationCandidate,
    ApplicationCandidateStatus,
    select_application_candidates,
)
from buscador_de_vaga.candidate_positioning import (
    AutomaticSearchPlan,
    CandidateCareerAlignment,
    CandidateProfileAssessment,
)
from buscador_de_vaga.discovery import (
    AutomaticDiscoveryResult,
    DiscoveryResult,
    SourceReport,
)
from buscador_de_vaga.domain import (
    Evidence,
    EvidenceAssertion,
    FitDimension,
    FitScore,
    JobCategory,
    JobPosting,
    MatchAssessment,
    Opportunity,
    Provenance,
    Requirement,
    RequirementAssessment,
    RequirementImportance,
    RequirementStatus,
    RequirementSubject,
    SearchCriteria,
    Shortlist,
)


def _match_assessment(
    *,
    opportunity_id: str = "synthetic:job-001",
    score: int,
    requirement_assessments: tuple[RequirementAssessment, ...] = (),
) -> MatchAssessment:
    return MatchAssessment(
        opportunity_id=opportunity_id,
        requirement_assessments=requirement_assessments,
        fit_score=FitScore(
            value=score,
            evidence_coverage=100,
            policy_version="match-v2",
            breakdown=(),
        ),
    )


def test_fit_score_80_eligible_without_blocker_is_ready_in_manual_flow() -> None:
    candidates = select_application_candidates((_match_assessment(score=80),))

    assert APPLICATION_CANDIDATE_MIN_FIT_SCORE == 80
    assert APPLICATION_CANDIDATE_POLICY_VERSION == "application-candidate-v1"
    assert candidates == (
        ApplicationCandidate(
            opportunity_id="synthetic:job-001",
            status=ApplicationCandidateStatus.READY,
            fit_score=80,
            reason=(
                "FitScore 80, elegibilidade confirmada e critérios do fluxo manual atendidos."
            ),
            policy_version=APPLICATION_CANDIDATE_POLICY_VERSION,
        ),
    )


def test_fit_score_79_is_not_an_application_candidate() -> None:
    assert select_application_candidates((_match_assessment(score=79),)) == ()


def test_fit_score_100_is_an_application_candidate() -> None:
    candidates = select_application_candidates((_match_assessment(score=100),))

    assert tuple(candidate.fit_score for candidate in candidates) == (100,)


def test_uncertain_opportunity_is_not_an_application_candidate() -> None:
    uncertain_requirement = RequirementAssessment(
        requirement=_skill_requirement(importance=RequirementImportance.UNKNOWN),
        status=RequirementStatus.UNKNOWN,
        evidence=(),
        maximum_points=25,
        awarded_points=0,
        covered_points=0,
    )
    assessment = _match_assessment(
        score=100,
        requirement_assessments=(uncertain_requirement,),
    )

    assert select_application_candidates((assessment,)) == ()


def test_ineligible_opportunity_is_not_an_application_candidate() -> None:
    assessment = _match_assessment(
        score=100,
        requirement_assessments=(_confirmed_blocker(),),
    )

    assert select_application_candidates((assessment,)) == ()


def test_confirmed_blocking_requirement_prevents_application_candidate() -> None:
    assessment = _match_assessment(
        score=100,
        requirement_assessments=(_confirmed_blocker(),),
    )

    assert assessment.blocking_requirements
    assert select_application_candidates((assessment,)) == ()


def test_matching_career_alignment_is_ready() -> None:
    candidates = select_application_candidates(
        (_match_assessment(score=90),),
        alignments_by_opportunity_id={
            "synthetic:job-001": CandidateCareerAlignment.MATCH,
        },
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert all(
        item.status is not ApplicationCandidateStatus.REVIEW for item in candidates
    )
    assert candidate.status is ApplicationCandidateStatus.READY
    assert candidate.reason == (
        "FitScore 90, elegibilidade confirmada e alinhamento de carreira compatível."
    )


def test_review_career_alignment_requires_review() -> None:
    candidates = select_application_candidates(
        (_match_assessment(score=85),),
        alignments_by_opportunity_id={
            "synthetic:job-001": CandidateCareerAlignment.REVIEW,
        },
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.status is ApplicationCandidateStatus.REVIEW
    assert candidate.reason == (
        "FitScore 85 e elegibilidade confirmada, mas o nível da vaga requer revisão."
    )


def test_above_profile_career_alignment_is_not_an_application_candidate() -> None:
    candidates = select_application_candidates(
        (_match_assessment(score=100),),
        alignments_by_opportunity_id={
            "synthetic:job-001": CandidateCareerAlignment.ABOVE_PROFILE,
        },
    )

    assert candidates == ()


def test_below_profile_career_alignment_requires_review() -> None:
    candidates = select_application_candidates(
        (_match_assessment(score=100),),
        alignments_by_opportunity_id={
            "synthetic:job-001": CandidateCareerAlignment.BELOW_PROFILE,
        },
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.status is ApplicationCandidateStatus.REVIEW
    assert candidate.reason == (
        "FitScore 100 e elegibilidade confirmada, mas o nível da vaga está abaixo "
        "do perfil e requer revisão."
    )


def test_automatic_flow_does_not_invent_a_missing_career_alignment() -> None:
    candidates = select_application_candidates(
        (_match_assessment(score=100),),
        alignments_by_opportunity_id={},
    )

    assert candidates == ()


def test_automatic_alignment_results_are_identical_on_repeated_runs() -> None:
    assessments = (
        _match_assessment(opportunity_id="synthetic:match", score=90),
        _match_assessment(opportunity_id="synthetic:review", score=85),
        _match_assessment(opportunity_id="synthetic:below", score=100),
        _match_assessment(opportunity_id="synthetic:above", score=100),
    )
    alignments = {
        "synthetic:match": CandidateCareerAlignment.MATCH,
        "synthetic:review": CandidateCareerAlignment.REVIEW,
        "synthetic:below": CandidateCareerAlignment.BELOW_PROFILE,
        "synthetic:above": CandidateCareerAlignment.ABOVE_PROFILE,
    }

    first = select_application_candidates(
        assessments,
        alignments_by_opportunity_id=alignments,
    )
    second = select_application_candidates(
        assessments,
        alignments_by_opportunity_id=alignments,
    )

    assert first == second
    assert tuple((candidate.opportunity_id, candidate.status) for candidate in first) == (
        ("synthetic:match", ApplicationCandidateStatus.READY),
        ("synthetic:below", ApplicationCandidateStatus.REVIEW),
        ("synthetic:review", ApplicationCandidateStatus.REVIEW),
    )


def test_application_candidates_have_deterministic_policy_order() -> None:
    assessments = (
        _match_assessment(opportunity_id="synthetic:review-high", score=100),
        _match_assessment(opportunity_id="synthetic:ready-low", score=80),
        _match_assessment(opportunity_id="synthetic:ready-z", score=90),
        _match_assessment(opportunity_id="synthetic:ready-a", score=90),
    )
    alignments = {
        "synthetic:review-high": CandidateCareerAlignment.REVIEW,
        "synthetic:ready-low": CandidateCareerAlignment.MATCH,
        "synthetic:ready-z": CandidateCareerAlignment.MATCH,
        "synthetic:ready-a": CandidateCareerAlignment.MATCH,
    }

    direct = select_application_candidates(
        assessments,
        alignments_by_opportunity_id=alignments,
    )
    permuted = select_application_candidates(
        tuple(reversed(assessments)),
        alignments_by_opportunity_id=alignments,
    )

    expected_ids = (
        "synthetic:ready-a",
        "synthetic:ready-z",
        "synthetic:ready-low",
        "synthetic:review-high",
    )
    assert tuple(candidate.opportunity_id for candidate in direct) == expected_ids
    assert tuple(candidate.status for candidate in direct) == (
        ApplicationCandidateStatus.READY,
        ApplicationCandidateStatus.READY,
        ApplicationCandidateStatus.READY,
        ApplicationCandidateStatus.REVIEW,
    )
    assert permuted == direct


def test_selection_preserves_fit_score_and_match_assessment() -> None:
    assessment = _match_assessment(score=90)
    original_fit_score = assessment.fit_score
    original_assessment = assessment

    candidates = select_application_candidates((assessment,))

    assert candidates[0].fit_score == 90
    assert assessment.fit_score is original_fit_score
    assert assessment == original_assessment


def test_application_candidate_is_frozen_and_uses_slots() -> None:
    candidate = select_application_candidates((_match_assessment(score=90),))[0]

    with pytest.raises(FrozenInstanceError):
        candidate.fit_score = 0  # type: ignore[misc]

    assert not hasattr(candidate, "__dict__")


def test_reason_does_not_include_evidence_statement_or_personal_data() -> None:
    private_markers = (
        "Ana Silva",
        "ana@example.com",
        "21999999999",
        "Rua Privada, 123",
    )
    private_evidence = Evidence(
        id="candidate-private-data",
        subject=RequirementSubject.skill("python"),
        statement="; ".join(private_markers),
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(origin="candidate-profile", locator="private"),
    )
    met_requirement = RequirementAssessment(
        requirement=Requirement(
            id="skill:python",
            subject=RequirementSubject.skill("python"),
            statement="A Opportunity exige Python.",
            dimension=FitDimension.SKILLS,
            importance=RequirementImportance.PREFERRED,
            provenance=(Provenance(origin="synthetic", locator="job-001#summary"),),
        ),
        status=RequirementStatus.MET,
        evidence=(private_evidence,),
        maximum_points=25,
        awarded_points=25,
        covered_points=25,
    )
    assessment = _match_assessment(
        score=90,
        requirement_assessments=(met_requirement,),
    )

    reason = select_application_candidates((assessment,))[0].reason

    assert private_evidence.statement not in reason
    assert all(marker not in reason for marker in private_markers)


def test_manual_discovery_result_derives_candidates_without_changing_shortlist() -> None:
    ready = _opportunity("synthetic:ready", "Desenvolvedor Python")
    below_threshold = _opportunity("synthetic:visible", "Analista de Sistemas")
    shortlist = Shortlist(items=(below_threshold, ready))
    result = DiscoveryResult(
        candidate_profile_id="candidate-example",
        criteria=SearchCriteria(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Brasil",
        ),
        policy_version="match-v2",
        source_report=SourceReport(source_name="synthetic", postings_received=2),
        postings=(),
        opportunities=(ready, below_threshold),
        match_assessments=(
            _match_assessment(opportunity_id=ready.id, score=90),
            _match_assessment(opportunity_id=below_threshold.id, score=79),
        ),
        shortlist=shortlist,
    )

    candidates = result.application_candidates

    assert tuple(candidate.opportunity_id for candidate in candidates) == (ready.id,)
    assert candidates[0].status is ApplicationCandidateStatus.READY
    assert result.shortlist is shortlist
    assert below_threshold in result.shortlist.items
    assert result.application_candidates == candidates


def test_automatic_discovery_result_uses_existing_career_alignments() -> None:
    matching = _opportunity("synthetic:match", "Desenvolvedor Python Júnior")
    review = _opportunity("synthetic:review", "Estágio em Desenvolvimento")
    above_profile = _opportunity("synthetic:above", "Engenheiro de Software Sênior")
    shortlist = Shortlist(items=(above_profile, review, matching))
    result = AutomaticDiscoveryResult(
        candidate_profile_id="candidate-example",
        assessment=CandidateProfileAssessment(
            profile_id="candidate-example",
            policy_version="candidate-positioning-v1",
            category_assessments=(),
        ),
        plan=AutomaticSearchPlan(targets=(), queries=()),
        policy_version="match-v2",
        source_report=SourceReport(source_name="synthetic", postings_received=3),
        postings=(),
        opportunities=(matching, review, above_profile),
        match_assessments=(
            _match_assessment(opportunity_id=matching.id, score=90),
            _match_assessment(opportunity_id=review.id, score=85),
            _match_assessment(opportunity_id=above_profile.id, score=100),
        ),
        alignments_by_opportunity_id={
            matching.id: CandidateCareerAlignment.MATCH,
            review.id: CandidateCareerAlignment.REVIEW,
            above_profile.id: CandidateCareerAlignment.ABOVE_PROFILE,
        },
        shortlist=shortlist,
    )

    candidates = result.application_candidates

    assert tuple(
        (candidate.opportunity_id, candidate.status) for candidate in candidates
    ) == (
        (matching.id, ApplicationCandidateStatus.READY),
        (review.id, ApplicationCandidateStatus.REVIEW),
    )
    assert result.shortlist is shortlist
    assert above_profile in result.shortlist.items


def _skill_requirement(*, importance: RequirementImportance) -> Requirement:
    return Requirement(
        id="skill:docker",
        subject=RequirementSubject.skill("docker"),
        statement="A Opportunity exige Docker.",
        dimension=FitDimension.SKILLS,
        importance=importance,
        provenance=(Provenance(origin="synthetic", locator="job-001#summary"),),
    )


def _confirmed_blocker() -> RequirementAssessment:
    evidence = Evidence(
        id="candidate-without-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate confirmou não possuir experiência com Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        provenance=Provenance(origin="candidate-profile", locator="skills/docker"),
    )
    return RequirementAssessment(
        requirement=_skill_requirement(importance=RequirementImportance.BLOCKING),
        status=RequirementStatus.UNMET,
        evidence=(evidence,),
        maximum_points=25,
        awarded_points=0,
        covered_points=25,
    )


def _opportunity(opportunity_id: str, title: str) -> Opportunity:
    posting = JobPosting(
        source_name="synthetic",
        external_id=opportunity_id.removeprefix("synthetic:"),
        title=title,
        company="ACME",
        location="Brasil",
        source_url=f"https://example.invalid/{opportunity_id}",
        collected_at=datetime(2026, 8, 28, 12, tzinfo=UTC),
    )
    return Opportunity(
        id=opportunity_id,
        title=title,
        company=posting.company,
        location=posting.location,
        source_url=posting.source_url,
        postings=(posting,),
    )
