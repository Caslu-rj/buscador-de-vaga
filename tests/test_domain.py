from buscador_de_vaga.domain import (
    CareerPreference,
    CareerPreferenceAssessment,
    CareerPriority,
    CareerRecommendation,
    FitScore,
    JobCategory,
    MatchAssessment,
    SearchCriteria,
)


def test_search_criteria_defaults_to_no_career_preference() -> None:
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
    )

    assert criteria.career_preference is None


def test_search_criteria_accepts_entry_level_career_preference() -> None:
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assert criteria.career_preference is CareerPreference.ENTRY_LEVEL


def test_match_assessment_defaults_to_no_career_preference_assessment() -> None:
    assessment = MatchAssessment(
        opportunity_id="synthetic:job-001",
        requirement_assessments=(),
        fit_score=FitScore(
            value=0,
            evidence_coverage=0,
            policy_version="match-v2",
            breakdown=(),
        ),
    )

    assert assessment.career_preference_assessment is None


def test_career_preference_assessment_exposes_the_versioned_policy_result() -> None:
    assessment = CareerPreferenceAssessment(
        preference=CareerPreference.ENTRY_LEVEL,
        priority=CareerPriority.INTERNSHIP,
        recommendation=CareerRecommendation.RECOMMENDED,
        policy_version="career-entry-v1",
        reason="A Opportunity possui sinal explícito de estágio.",
    )

    assert (
        assessment.preference.value,
        assessment.priority.value,
        assessment.recommendation.value,
        assessment.policy_version,
        assessment.reason,
    ) == (
        "entry-level",
        "internship",
        "recommended",
        "career-entry-v1",
        "A Opportunity possui sinal explícito de estágio.",
    )
