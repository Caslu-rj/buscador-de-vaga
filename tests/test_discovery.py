from datetime import UTC, datetime

import pytest

from buscador_de_vaga.discovery import (
    DiscoveryResult,
    InvalidDiscoveryRequest,
    OpportunityDiscovery,
)
from buscador_de_vaga.domain import (
    CandidateProfile,
    CareerPreference,
    CareerPriority,
    CareerRecommendation,
    EligibilityStatus,
    EntryProgram,
    Evidence,
    EvidenceAssertion,
    JobCategory,
    JobPosting,
    JobSourceQuery,
    Provenance,
    RequirementKind,
    RequirementStatus,
    RequirementSubject,
    SearchCriteria,
    Seniority,
    WorkplaceMode,
)
from buscador_de_vaga.sources.multi import MultiSourceJobSource


class StubJobSource:
    name = "synthetic"

    def __init__(self, postings: tuple[JobPosting, ...]) -> None:
        self._postings = postings

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        if query.keywords == "desenvolvedor de software":
            return self._postings
        return ()


class RecordingJobSource:
    name = "recording"

    def __init__(
        self,
        responses_by_keywords: dict[str, tuple[JobPosting, ...]] | None = None,
    ) -> None:
        self._responses_by_keywords = responses_by_keywords or {}
        self.received_queries: list[JobSourceQuery] = []

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        self.received_queries.append(query)
        return self._responses_by_keywords.get(query.keywords, ())


def _discover(
    postings: tuple[JobPosting, ...],
    *,
    profile: CandidateProfile | None = None,
    limit: int = 10,
    location: str = "Brasil",
    career_preference: CareerPreference | None = None,
) -> DiscoveryResult:
    candidate_profile = profile or CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location=location,
        limit=limit,
        career_preference=career_preference,
    )
    return OpportunityDiscovery(source=StubJobSource(postings)).discover(
        candidate_profile,
        criteria,
    )


def test_entry_level_preference_recommends_an_explicit_internship() -> None:
    result = _discover(
        (_synthetic_posting(title="Estágio Desenvolvedor Python"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert career_assessment.reason
    assert (
        career_assessment.preference,
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
    ) == (
        CareerPreference.ENTRY_LEVEL,
        CareerPriority.INTERNSHIP,
        CareerRecommendation.RECOMMENDED,
        "career-entry-v1",
        "A Opportunity possui sinal explícito de programa de estágio.",
    )


def test_entry_level_preference_recommends_an_explicit_junior_role() -> None:
    result = _discover(
        (_synthetic_posting(title="Desenvolvedor Python Júnior"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
    ) == (
        CareerPriority.JUNIOR,
        CareerRecommendation.RECOMMENDED,
        "career-entry-v1",
        "A Opportunity possui sinal explícito de nível júnior.",
    )


def test_entry_level_preference_recommends_an_explicit_trainee_role() -> None:
    result = _discover(
        (_synthetic_posting(title="Trainee em Desenvolvimento de Software"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
    ) == (
        CareerPriority.TRAINEE,
        CareerRecommendation.RECOMMENDED,
        "career-entry-v1",
        "A Opportunity possui sinal explícito de programa trainee.",
    )


def test_entry_level_preference_keeps_missing_seniority_auditable_as_unknown() -> None:
    result = _discover(
        (_synthetic_posting(title="Desenvolvedor de Software"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
    ) == (
        CareerPriority.UNKNOWN,
        CareerRecommendation.REVIEW,
        "career-entry-v1",
        "A Opportunity não possui nível de carreira explícito.",
    )


def test_entry_level_preference_marks_mid_level_as_low_priority() -> None:
    result = _discover(
        (_synthetic_posting(title="Desenvolvedor de Software Pleno"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
    ) == (
        CareerPriority.MID_LEVEL,
        CareerRecommendation.LOW_PRIORITY,
        "career-entry-v1",
        (
            "A Opportunity possui sinal explícito de nível pleno, "
            "fora da prioridade de início de carreira."
        ),
    )


def test_entry_level_preference_does_not_recommend_an_explicit_senior_role() -> None:
    result = _discover(
        (_synthetic_posting(title="Desenvolvedor de Software Sênior"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assessment = result.match_assessments[0]
    career_assessment = assessment.career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
        career_assessment.policy_version,
        career_assessment.reason,
        assessment.eligibility_status,
        tuple(item.id for item in result.shortlist.items),
    ) == (
        CareerPriority.SENIOR,
        CareerRecommendation.NOT_RECOMMENDED,
        "career-entry-v1",
        (
            "A Opportunity possui sinal explícito de nível sênior, "
            "incompatível com início de carreira."
        ),
        EligibilityStatus.UNCERTAIN,
        ("synthetic:job-001",),
    )


def test_entry_level_policy_gives_explicit_senior_priority_in_conflicts() -> None:
    result = _discover(
        (_synthetic_posting(title="Estágio Desenvolvedor Python Júnior/Sênior"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
    ) == (
        CareerPriority.SENIOR,
        CareerRecommendation.NOT_RECOMMENDED,
    )


def test_entry_level_policy_gives_mid_level_priority_over_entry_signals() -> None:
    result = _discover(
        (_synthetic_posting(title="Estágio Desenvolvedor Python Júnior Pleno"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert (
        career_assessment.priority,
        career_assessment.recommendation,
    ) == (
        CareerPriority.MID_LEVEL,
        CareerRecommendation.LOW_PRIORITY,
    )


def test_entry_level_policy_gives_internship_priority_over_junior_and_trainee() -> None:
    result = _discover(
        (_synthetic_posting(title="Estágio Desenvolvedor Júnior Trainee"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert career_assessment.priority is CareerPriority.INTERNSHIP


def test_entry_level_policy_gives_junior_priority_over_trainee() -> None:
    result = _discover(
        (_synthetic_posting(title="Desenvolvedor Júnior Trainee"),),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    career_assessment = result.match_assessments[0].career_preference_assessment
    assert career_assessment is not None
    assert career_assessment.priority is CareerPriority.JUNIOR


def test_entry_level_ranking_orders_recommendation_buckets_before_score_tiebreakers() -> None:
    postings = (
        _synthetic_posting(
            external_id="a-senior",
            title="Desenvolvedor de Software Sênior",
            location="Niterói, RJ",
        ),
        _synthetic_posting(
            external_id="b-mid-level",
            title="Desenvolvedor de Software Pleno",
            location="Niterói, RJ",
        ),
        _synthetic_posting(
            external_id="c-unknown",
            title="Desenvolvedor de Software",
            location="Niterói, RJ",
        ),
        _synthetic_posting(
            external_id="d-junior",
            title="Desenvolvedor de Software Júnior",
            location="Niterói, RJ",
        ),
    )

    result = _discover(postings, career_preference=CareerPreference.ENTRY_LEVEL)

    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:d-junior",
        "synthetic:c-unknown",
        "synthetic:b-mid-level",
        "synthetic:a-senior",
    )


def test_entry_level_ranking_uses_career_priority_after_equal_fit_scores() -> None:
    result = _discover(
        (
            _synthetic_posting(
                external_id="a-trainee",
                title="Trainee Desenvolvedor de Software",
                location="Niterói, RJ",
            ),
            _synthetic_posting(
                external_id="b-junior",
                title="Desenvolvedor de Software Júnior",
                location="Niterói, RJ",
            ),
            _synthetic_posting(
                external_id="c-internship",
                title="Estágio Desenvolvedor de Software",
                location="Niterói, RJ",
            ),
        ),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:c-internship",
        "synthetic:b-junior",
        "synthetic:a-trainee",
    )


def test_entry_level_ranking_uses_fit_score_before_priority_in_the_same_bucket() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="candidate-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate possui evidência de Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/python",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence,),
    )
    result = _discover(
        (
            _synthetic_posting(
                external_id="internship",
                title="Estágio Desenvolvedor de Software",
                location="Niterói, RJ",
            ),
            _synthetic_posting(
                external_id="junior-python",
                title="Desenvolvedor Python Júnior",
                location="Niterói, RJ",
            ),
        ),
        profile=profile,
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:junior-python",
        "synthetic:internship",
    )


def test_entry_level_ranking_keeps_eligibility_before_career_recommendation() -> None:
    result = _discover(
        (
            _synthetic_posting(
                external_id="junior-uncertain",
                title="Desenvolvedor de Software Júnior",
            ),
            _synthetic_posting(
                external_id="unknown-eligible",
                title="Desenvolvedor de Software",
            ),
        ),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:unknown-eligible",
        "synthetic:junior-uncertain",
    )


@pytest.mark.parametrize(
    ("title", "expected_priority", "expected_recommendation"),
    (
        (
            "Desenvolvedor Fullstack Python",
            CareerPriority.UNKNOWN,
            CareerRecommendation.REVIEW,
        ),
        (
            "Desenvolvedor Fullstack Python Senior",
            CareerPriority.SENIOR,
            CareerRecommendation.NOT_RECOMMENDED,
        ),
        (
            "Desenvolvedor Fullstack Python Junior",
            CareerPriority.JUNIOR,
            CareerRecommendation.RECOMMENDED,
        ),
    ),
)
def test_entry_level_preference_keeps_real_technical_fit_80_separate_from_career(
    title: str,
    expected_priority: CareerPriority,
    expected_recommendation: CareerRecommendation,
) -> None:
    python_evidence = _candidate_evidence(
        evidence_id="candidate-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate possui evidência de Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/python",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence,),
    )
    result = _discover(
        (
            _synthetic_posting(
                title=title,
                location="Rio de Janeiro, Estado do Rio de Janeiro",
            ),
        ),
        profile=profile,
        location="Rio de Janeiro",
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assessment = result.match_assessments[0]
    career_assessment = assessment.career_preference_assessment
    assert career_assessment is not None
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
        tuple((item.dimension.value, item.weight) for item in assessment.fit_score.breakdown),
        career_assessment.priority,
        career_assessment.recommendation,
        profile.evidence,
    ) == (
        80,
        80,
        (
            ("job-category", 40),
            ("skills", 25),
            ("entry-program-seniority", 20),
            ("location-workplace-mode", 15),
        ),
        expected_priority,
        expected_recommendation,
        (python_evidence,),
    )


def test_career_preference_does_not_change_fit_score_coverage_or_evidence() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="candidate-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate possui evidência de Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/python",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence,),
    )
    posting = _synthetic_posting(
        title="Desenvolvedor Python Júnior",
        location="Rio de Janeiro, RJ",
    )

    without_preference = _discover(
        (posting,),
        profile=profile,
        location="Rio de Janeiro",
    ).match_assessments[0]
    with_preference = _discover(
        (posting,),
        profile=profile,
        location="Rio de Janeiro",
        career_preference=CareerPreference.ENTRY_LEVEL,
    ).match_assessments[0]

    assert with_preference.fit_score == without_preference.fit_score
    assert (
        with_preference.requirement_assessments,
        profile.evidence,
    ) == (
        without_preference.requirement_assessments,
        (python_evidence,),
    )


def test_career_preference_assessments_do_not_leak_between_discoveries() -> None:
    posting = _synthetic_posting(title="Desenvolvedor Python Júnior")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    discovery = OpportunityDiscovery(source=StubJobSource((posting,)))

    active_result = discovery.discover(
        profile,
        SearchCriteria(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Brasil",
            career_preference=CareerPreference.ENTRY_LEVEL,
        ),
    )
    default_result = discovery.discover(
        profile,
        SearchCriteria(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Brasil",
        ),
    )

    assert active_result.match_assessments[0].career_preference_assessment is not None
    assert default_result.match_assessments[0].career_preference_assessment is None


def test_entry_level_policy_is_deterministic_and_has_a_stable_version() -> None:
    postings = (
        _synthetic_posting(
            external_id="senior",
            title="Desenvolvedor Python Senior",
        ),
        _synthetic_posting(
            external_id="junior",
            title="Desenvolvedor Python Junior",
        ),
    )

    first = _discover(postings, career_preference=CareerPreference.ENTRY_LEVEL)
    second = _discover(postings, career_preference=CareerPreference.ENTRY_LEVEL)

    assert first.match_assessments == second.match_assessments
    assert first.shortlist == second.shortlist
    assert tuple(
        assessment.career_preference_assessment.policy_version
        for assessment in first.match_assessments
        if assessment.career_preference_assessment is not None
    ) == ("career-entry-v1", "career-entry-v1")


def test_entry_level_ranking_puts_junior_above_senior_at_the_same_fit_80() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="candidate-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate possui evidência de Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/python",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence,),
    )
    result = _discover(
        (
            _synthetic_posting(
                external_id="a-senior",
                title="Desenvolvedor Python Sênior",
                location="Rio de Janeiro, RJ",
            ),
            _synthetic_posting(
                external_id="z-junior",
                title="Desenvolvedor Python Júnior",
                location="Rio de Janeiro, RJ",
            ),
        ),
        profile=profile,
        location="Rio de Janeiro",
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assessments_by_id = {
        assessment.opportunity_id: assessment for assessment in result.match_assessments
    }
    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:z-junior",
        "synthetic:a-senior",
    )
    assert tuple(
        assessments_by_id[item.id].fit_score.value for item in result.shortlist.items
    ) == (80, 80)


def test_entry_level_ranking_uses_update_and_stable_id_as_final_tiebreakers() -> None:
    result = _discover(
        (
            _synthetic_posting(
                external_id="unknown-update",
                title="Desenvolvedor de Software Júnior",
            ),
            _synthetic_posting(
                external_id="z-tied",
                title="Desenvolvedor de Software Júnior",
                source_updated_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            ),
            _synthetic_posting(
                external_id="newest",
                title="Desenvolvedor de Software Júnior",
                source_updated_at=datetime(2026, 8, 22, 12, tzinfo=UTC),
            ),
            _synthetic_posting(
                external_id="a-tied",
                title="Desenvolvedor de Software Júnior",
                source_updated_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            ),
        ),
        career_preference=CareerPreference.ENTRY_LEVEL,
    )

    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:newest",
        "synthetic:a-tied",
        "synthetic:z-tied",
        "synthetic:unknown-update",
    )


def _candidate_evidence(
    *,
    evidence_id: str,
    subject: RequirementSubject,
    statement: str,
    assertion: EvidenceAssertion,
    locator: str,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        subject=subject,
        statement=statement,
        assertion=assertion,
        provenance=Provenance(origin="candidate-profile", locator=locator),
    )


def _synthetic_posting(
    *,
    external_id: str = "job-001",
    title: str = "Software Engineer",
    company: str | None = "ACME Tecnologia",
    location: str | None = None,
    summary: str | None = None,
    source_updated_at: datetime | None = None,
) -> JobPosting:
    return JobPosting(
        source_name="synthetic",
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        source_url=f"https://jobs.example.invalid/{external_id}",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary=summary,
        source_updated_at=source_updated_at,
    )


def test_discover_normaliza_um_job_posting_e_o_inclui_na_shortlist() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="  Desenvolvedor(a)   Python Júnior  ",
        company="  ACME   Tecnologia ",
        location=" Rio de Janeiro, RJ ",
        source_url="  https://jobs.example.invalid/job-001  ",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    source = StubJobSource((posting,))
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro, RJ",
        limit=10,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert result.criteria == criteria
    assert result.source_report.source_name == "synthetic"
    assert result.source_report.postings_received == 1
    assert result.postings == (posting,)
    assert len(result.opportunities) == 1
    opportunity = result.opportunities[0]
    assert opportunity.id == "synthetic:job-001"
    assert opportunity.title == "Desenvolvedor(a) Python Júnior"
    assert opportunity.company == "ACME Tecnologia"
    assert opportunity.location == "Rio de Janeiro, RJ"
    assert opportunity.source_url == "https://jobs.example.invalid/job-001"
    assert opportunity.postings == (posting,)
    assert result.shortlist.items == (opportunity,)


def test_discover_consolida_postings_da_mesma_fonte_com_o_mesmo_id() -> None:
    first_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="  Desenvolvedor Python Júnior  ",
        company=" ACME Tecnologia ",
        location=" Rio de Janeiro, RJ ",
        source_url=" https://jobs.example.invalid/job-001 ",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    repeated_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://mirror.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    result = _discover((first_posting, repeated_posting))

    assert result.postings == (first_posting, repeated_posting)
    assert result.source_report.postings_received == 2
    assert len(result.opportunities) == 1
    opportunity = result.opportunities[0]
    assert opportunity.id == "synthetic:job-001"
    assert opportunity.title == "Desenvolvedor Python Júnior"
    assert opportunity.company == "ACME Tecnologia"
    assert opportunity.location == "Rio de Janeiro, RJ"
    assert opportunity.source_url == "https://jobs.example.invalid/job-001"
    assert opportunity.postings == (first_posting, repeated_posting)
    assert result.shortlist.items == (opportunity,)


def test_discover_consolida_postings_com_a_mesma_url_canonica() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="a-42",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url=" HTTPS://JOBS.EXAMPLE.INVALID:443/vagas/42#descricao ",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="b-42",
        title="Backend Engineer",
        company="ACME Labs",
        location="Brasil",
        source_url="https://jobs.example.invalid/vagas/42#descricao",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    result = _discover((first_posting, second_posting))

    assert len(result.opportunities) == 1
    opportunity = result.opportunities[0]
    assert opportunity.id == "alpha:a-42"
    assert opportunity.source_url == "https://jobs.example.invalid/vagas/42#descricao"
    assert opportunity.postings == (first_posting, second_posting)
    assert result.shortlist.items == (opportunity,)


def test_discover_nao_consolida_hash_routes_distintas() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://jobs.example.invalid/#/jobs/1",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="Backend Engineer",
        company="Beta Labs",
        location="São Paulo, SP",
        source_url="https://jobs.example.invalid/#/jobs/2",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    result = _discover((first_posting, second_posting))

    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "alpha:a-001",
        "beta:b-001",
    )


def test_discover_consolida_tripla_completa_apos_normalizacao_exata() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title=" Desenvolvedor   Python ",
        company=" ACME   TECNOLOGIA ",
        location=" Sa\u0303o Paulo, SP ",
        source_url="https://alpha.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="desenvolvedor python",
        company="acme tecnologia",
        location="SÃO PAULO, SP",
        source_url="https://beta.example.invalid/b-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    result = _discover((first_posting, second_posting))

    assert len(result.opportunities) == 1
    opportunity = result.opportunities[0]
    assert opportunity.id == "alpha:a-001"
    assert opportunity.title == "Desenvolvedor Python"
    assert opportunity.company == "ACME TECNOLOGIA"
    assert opportunity.location == "São Paulo, SP"
    assert opportunity.postings == (first_posting, second_posting)
    assert result.shortlist.items == (opportunity,)


def test_discover_nao_consolida_tripla_com_localizacao_ausente() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location=None,
        source_url="https://alpha.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="desenvolvedor python",
        company="acme tecnologia",
        location=None,
        source_url="https://beta.example.invalid/b-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    result = _discover((first_posting, second_posting))

    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "alpha:a-001",
        "beta:b-001",
    )


def test_discover_nao_consolida_titulos_apenas_parecidos() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Desenvolvedor Python Júnior",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://alpha.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="Desenvolvedor Python Jr.",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://beta.example.invalid/b-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    result = _discover((first_posting, second_posting))

    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "alpha:a-001",
        "beta:b-001",
    )


def test_discover_nao_confunde_external_id_entre_job_sources() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="job-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://alpha.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    second_posting = JobPosting(
        source_name="beta",
        external_id="job-001",
        title="Backend Engineer",
        company="Beta Labs",
        location="São Paulo, SP",
        source_url="https://beta.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    result = _discover((first_posting, second_posting))

    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "alpha:job-001",
        "beta:job-001",
    )


def test_discover_nao_expande_componente_forte_com_triplas_conflitantes() -> None:
    python_posting = JobPosting(
        source_name="alpha",
        external_id="job-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://alpha.example.invalid/python",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    conflicting_posting = JobPosting(
        source_name="alpha",
        external_id="job-001",
        title="Desenvolvedor Java",
        company="Beta Labs",
        location="São Paulo, SP",
        source_url="https://alpha.example.invalid/java",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    possible_duplicate = JobPosting(
        source_name="gamma",
        external_id="job-999",
        title="desenvolvedor python",
        company="acme tecnologia",
        location="RIO DE JANEIRO, RJ",
        source_url="https://gamma.example.invalid/job-999",
        collected_at=datetime(2026, 8, 21, 14, tzinfo=UTC),
    )

    result = _discover((python_posting, conflicting_posting, possible_duplicate))

    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "alpha:job-001",
        "gamma:job-999",
    )
    assert result.opportunities[0].postings == (conflicting_posting, python_posting)
    assert result.opportunities[1].postings == (possible_duplicate,)


def test_discover_aplica_fecho_transitivo_das_identidades_fortes() -> None:
    first_posting = JobPosting(
        source_name="alpha",
        external_id="job-001",
        title="Desenvolvedor Python",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://alpha.example.invalid/first",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    id_bridge = JobPosting(
        source_name="alpha",
        external_id="job-001",
        title="Backend Engineer",
        company="Beta Labs",
        location="São Paulo, SP",
        source_url="https://jobs.example.invalid/bridge#details",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    url_bridge = JobPosting(
        source_name="gamma",
        external_id="job-999",
        title="Software Engineer",
        company="Gamma Labs",
        location="Brasil",
        source_url="HTTPS://JOBS.EXAMPLE.INVALID:443/bridge#details",
        collected_at=datetime(2026, 8, 21, 14, tzinfo=UTC),
    )

    result = _discover((first_posting, id_bridge, url_bridge))

    assert len(result.opportunities) == 1
    assert result.opportunities[0].id == "alpha:job-001"
    assert result.opportunities[0].postings == (
        first_posting,
        id_bridge,
        url_bridge,
    )


def test_discover_mantem_ids_representantes_e_ordem_ao_permutar_postings() -> None:
    beta_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="backend engineer",
        company="acme tecnologia",
        location="BRASIL",
        source_url="https://beta.example.invalid/b-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    alpha_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Backend Engineer",
        company="ACME Tecnologia",
        location="Brasil",
        source_url="https://alpha.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    independent_posting = JobPosting(
        source_name="zeta",
        external_id="z-001",
        title="Analista de Sistemas",
        company="Zeta Labs",
        location="Brasil",
        source_url="https://zeta.example.invalid/z-001",
        collected_at=datetime(2026, 8, 21, 14, tzinfo=UTC),
    )
    postings = (independent_posting, beta_posting, alpha_posting)

    direct_result = _discover(postings)
    reversed_result = _discover(tuple(reversed(postings)))

    assert tuple(opportunity.id for opportunity in direct_result.opportunities) == (
        "alpha:a-001",
        "zeta:z-001",
    )
    assert direct_result.opportunities == reversed_result.opportunities
    assert direct_result.opportunities[0].postings == (alpha_posting, beta_posting)
    assert direct_result.shortlist == reversed_result.shortlist


def test_discover_expoe_match_assessment_versionado_com_quatro_dimensoes() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    result = _discover((posting,))

    assert len(result.match_assessments) == 1
    assessment = result.match_assessments[0]
    assert assessment.opportunity_id == "synthetic:job-001"
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
        assessment.fit_score.policy_version,
    ) == (40, 40, "match-v2")
    assert tuple(
        (
            breakdown.dimension.value,
            breakdown.weight,
            breakdown.awarded_points,
            breakdown.covered_weight,
        )
        for breakdown in assessment.fit_score.breakdown
    ) == (
        ("job-category", 40, 40, 40),
        ("skills", 25, 0, 0),
        ("entry-program-seniority", 20, 0, 0),
        ("location-workplace-mode", 15, 0, 0),
    )
    assert len(assessment.requirement_assessments) == 1
    category_assessment = assessment.requirement_assessments[0]
    assert (
        category_assessment.requirement.subject.kind.value,
        category_assessment.requirement.subject.value,
        category_assessment.status.value,
        category_assessment.maximum_points,
        category_assessment.awarded_points,
        category_assessment.covered_points,
    ) == ("job-category", "software-development", "met", 40, 40, 40)
    assert category_assessment.requirement.subject.value is JobCategory.SOFTWARE_DEVELOPMENT
    assert tuple(
        (
            evidence.assertion.value,
            evidence.provenance.origin,
            evidence.provenance.locator,
        )
        for evidence in category_assessment.evidence
    ) == (("supports", "candidate-profile", "target_categories"),)
    assert assessment.strengths == (category_assessment,)
    assert assessment.skill_gaps == ()
    assert assessment.unknown_requirements == ()


def test_discover_mantem_categorias_ambiguas_como_unknown() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="QA Developer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    assessment = _discover((posting,)).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (0, 0)
    category_breakdown = assessment.fit_score.breakdown[0]
    assert (
        category_breakdown.awarded_points,
        category_breakdown.covered_weight,
    ) == (0, 0)
    category_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.JOB_CATEGORY
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.is_resolved,
            item.status.value,
            item.maximum_points,
            item.evidence,
        )
        for item in category_assessments
    ) == (
        ("quality-assurance", False, "unknown", 20, ()),
        (
            "software-development",
            False,
            "unknown",
            20,
            (
                Evidence(
                    id="candidate-profile:target-category:software-development",
                    subject=RequirementSubject(
                        kind=RequirementKind.JOB_CATEGORY,
                        value="software-development",
                    ),
                    statement=(
                        "CandidateProfile declara software-development em target_categories."
                    ),
                    assertion=EvidenceAssertion.SUPPORTS,
                    provenance=Provenance(
                        origin="candidate-profile",
                        locator="target_categories",
                    ),
                ),
            ),
        ),
    )
    assert assessment.strengths == ()
    assert assessment.skill_gaps == ()
    assert assessment.unknown_requirements == category_assessments


def test_discover_nao_infere_categoria_unmet_da_ausencia_nas_targets() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="QA Analyst",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    assessment = _discover((posting,)).match_assessments[0]

    category_assessment = assessment.requirement_assessments[0]
    assert (
        category_assessment.requirement.subject.value,
        category_assessment.status.value,
        category_assessment.evidence,
        category_assessment.awarded_points,
        category_assessment.covered_points,
    ) == ("quality-assurance", "unknown", (), 0, 0)
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (0, 0)
    assert assessment.strengths == ()
    assert assessment.skill_gaps == ()
    assert assessment.unknown_requirements == (category_assessment,)


def test_discover_explicita_job_category_nao_identificada_como_unknown() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Assistente de Tecnologia",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    assessment = _discover((posting,)).match_assessments[0]

    assert len(assessment.requirement_assessments) == 1
    category_assessment = assessment.requirement_assessments[0]
    assert (
        category_assessment.requirement.subject.kind.value,
        category_assessment.requirement.subject.value,
        category_assessment.requirement.is_resolved,
        category_assessment.requirement.statement,
        category_assessment.status.value,
        category_assessment.evidence,
        category_assessment.maximum_points,
        category_assessment.awarded_points,
        category_assessment.covered_points,
    ) == (
        "job-category",
        None,
        False,
        "A JobCategory da Opportunity não pôde ser identificada.",
        "unknown",
        (),
        40,
        0,
        0,
    )
    assert category_assessment.requirement.provenance == (
        Provenance(origin="synthetic", locator="job-001#title"),
    )
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (0, 0)
    assert assessment.unknown_requirements == (category_assessment,)


def test_discover_classifica_skill_sustentada_como_met() -> None:
    python_evidence = Evidence(
        id="project-api-python",
        subject=RequirementSubject(
            kind=RequirementKind.SKILL,
            value="python",
        ),
        statement="Projeto de API desenvolvido em Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="projects/api-python",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence,),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimento em Python.",
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (65, 65)
    skills_breakdown = assessment.fit_score.breakdown[1]
    assert (
        skills_breakdown.dimension.value,
        skills_breakdown.weight,
        skills_breakdown.awarded_points,
        skills_breakdown.covered_weight,
    ) == ("skills", 25, 25, 25)
    skill_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert (
        skill_assessment.requirement.subject.value,
        skill_assessment.status.value,
        skill_assessment.maximum_points,
        skill_assessment.awarded_points,
        skill_assessment.covered_points,
    ) == ("python", "met", 25, 25, 25)
    assert skill_assessment.evidence == (python_evidence,)
    assert skill_assessment.requirement.provenance == (
        Provenance(origin="synthetic", locator="job-001#summary"),
    )
    assert tuple(item.requirement.subject.kind.value for item in assessment.strengths) == (
        "job-category",
        "skill",
    )
    assert assessment.skill_gaps == ()
    assert assessment.unknown_requirements == ()


def test_discover_classifica_skill_contradita_como_unmet() -> None:
    sql_evidence = Evidence(
        id="self-assessment-sql",
        subject=RequirementSubject(
            kind=RequirementKind.SKILL,
            value="sql",
        ),
        statement="Candidate ainda não possui conhecimento de SQL.",
        assertion=EvidenceAssertion.CONTRADICTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="self-assessment/sql",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(sql_evidence,),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimento em SQL.",
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 65)
    skills_breakdown = assessment.fit_score.breakdown[1]
    assert (
        skills_breakdown.awarded_points,
        skills_breakdown.covered_weight,
    ) == (0, 25)
    assert len(assessment.skill_gaps) == 1
    skill_gap = assessment.skill_gaps[0]
    assert skill_gap.requirement.subject.value == "sql"
    assert skill_gap.evidence == (sql_evidence,)
    assert tuple(item.requirement.subject.kind.value for item in assessment.strengths) == (
        "job-category",
    )
    assert assessment.unknown_requirements == ()


def test_discover_exige_contexto_de_requisito_na_mesma_clausula_da_skill() -> None:
    sql_evidence = Evidence(
        id="self-assessment-sql",
        subject=RequirementSubject(
            kind=RequirementKind.SKILL,
            value="sql",
        ),
        statement="Candidate ainda não possui conhecimento de SQL.",
        assertion=EvidenceAssertion.CONTRADICTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="self-assessment/sql",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(sql_evidence,),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary=("Requisitos: conhecimento em Python. Produto desenvolvido em SQL."),
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    skill_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.status.value,
            item.evidence,
        )
        for item in skill_assessments
    ) == (("python", "unknown", ()),)
    assert assessment.skill_gaps == ()
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)


def test_discover_classifica_skill_sem_evidence_como_unknown() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimento em Docker.",
    )

    assessment = _discover((posting,)).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)
    skills_breakdown = assessment.fit_score.breakdown[1]
    assert (
        skills_breakdown.awarded_points,
        skills_breakdown.covered_weight,
    ) == (0, 0)
    assert assessment.skill_gaps == ()
    assert len(assessment.unknown_requirements) == 1
    unknown = assessment.unknown_requirements[0]
    assert (
        unknown.requirement.subject.value,
        unknown.status.value,
        unknown.evidence,
    ) == ("docker", "unknown", ())


def test_discover_classifica_evidence_ambigua_como_unknown() -> None:
    supports_python = Evidence(
        id="course-python",
        subject=RequirementSubject(kind=RequirementKind.SKILL, value="python"),
        statement="Curso introdutório de Python concluído.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="courses/python",
        ),
    )
    contradicts_python = Evidence(
        id="self-assessment-python",
        subject=RequirementSubject(kind=RequirementKind.SKILL, value="python"),
        statement="Candidate ainda não se considera apto em Python.",
        assertion=EvidenceAssertion.CONTRADICTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="self-assessment/python",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(contradicts_python, supports_python),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimento em Python.",
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)
    unknown = assessment.unknown_requirements[0]
    assert unknown.requirement.subject.value == "python"
    assert unknown.status.value == "unknown"
    assert unknown.evidence == (supports_python, contradicts_python)
    assert tuple(item.requirement.subject.kind.value for item in assessment.strengths) == (
        "job-category",
    )
    assert assessment.skill_gaps == ()


def test_discover_distribui_pontos_e_cobertura_entre_skills_explicitas() -> None:
    python_evidence = Evidence(
        id="project-python",
        subject=RequirementSubject(kind=RequirementKind.SKILL, value="python"),
        statement="Projeto desenvolvido em Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(origin="candidate-profile", locator="projects/python"),
    )
    sql_evidence = Evidence(
        id="self-assessment-sql",
        subject=RequirementSubject(kind=RequirementKind.SKILL, value="sql"),
        statement="Candidate ainda não possui conhecimento de SQL.",
        assertion=EvidenceAssertion.CONTRADICTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="self-assessment/sql",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(sql_evidence, python_evidence),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimentos em Python, Docker e SQL.",
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (48, 56)
    skills_breakdown = assessment.fit_score.breakdown[1]
    assert (
        skills_breakdown.weight,
        skills_breakdown.awarded_points,
        skills_breakdown.covered_weight,
    ) == (25, 8, 16)
    skill_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.status.value,
            item.maximum_points,
            item.awarded_points,
            item.covered_points,
        )
        for item in skill_assessments
    ) == (
        ("docker", "unknown", 9, 0, 0),
        ("python", "met", 8, 8, 8),
        ("sql", "unmet", 8, 0, 8),
    )
    assert tuple(gap.requirement.subject.value for gap in assessment.skill_gaps) == ("sql",)
    assert tuple(item.requirement.subject.value for item in assessment.unknown_requirements) == (
        "docker",
    )


def test_discover_avalia_seniority_explicitamente_sustentada() -> None:
    junior_evidence = Evidence(
        id="career-goal-junior",
        subject=RequirementSubject(
            kind=RequirementKind.SENIORITY,
            value="junior",
        ),
        statement="Candidate busca posições de nível júnior.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="career-goals/seniority",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(junior_evidence,),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer Júnior",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (60, 60)
    entry_breakdown = assessment.fit_score.breakdown[2]
    assert (
        entry_breakdown.dimension.value,
        entry_breakdown.weight,
        entry_breakdown.awarded_points,
        entry_breakdown.covered_weight,
    ) == ("entry-program-seniority", 20, 20, 20)
    seniority_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SENIORITY
    )
    assert (
        seniority_assessment.requirement.subject.value,
        seniority_assessment.status.value,
        seniority_assessment.evidence,
    ) == ("junior", "met", (junior_evidence,))
    assert tuple(item.requirement.subject.kind.value for item in assessment.strengths) == (
        "job-category",
        "seniority",
    )


def test_discover_mantem_senioridades_conflitantes_como_unknown() -> None:
    junior_evidence = Evidence(
        id="career-goal-junior",
        subject=RequirementSubject(
            kind=RequirementKind.SENIORITY,
            value="junior",
        ),
        statement="Candidate busca posições de nível júnior.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="career-goals/seniority",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(junior_evidence,),
    )
    junior_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer Júnior",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    senior_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer Sênior",
        company="ACME Tecnologia",
        location=None,
        source_url="https://mirror.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    assessment = _discover(
        (junior_posting, senior_posting),
        profile=profile,
    ).match_assessments[0]

    seniority_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SENIORITY
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.is_resolved,
            item.status.value,
            item.maximum_points,
            item.awarded_points,
            item.covered_points,
        )
        for item in seniority_assessments
    ) == (
        ("junior", False, "unknown", 10, 0, 0),
        ("senior", False, "unknown", 10, 0, 0),
    )
    assert seniority_assessments[0].evidence == (junior_evidence,)
    assert seniority_assessments[1].evidence == ()
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)
    assert assessment.unknown_requirements == seniority_assessments


def test_discover_avalia_localizacao_e_workplace_mode_sustentados() -> None:
    location_evidence = Evidence(
        id="accepted-location-sao-paulo",
        subject=RequirementSubject(
            kind=RequirementKind.LOCATION,
            value="são paulo, sp",
        ),
        statement="Candidate aceita oportunidades em São Paulo, SP.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="accepted-locations/sao-paulo",
        ),
    )
    hybrid_evidence = Evidence(
        id="accepted-mode-hybrid",
        subject=RequirementSubject(
            kind=RequirementKind.WORKPLACE_MODE,
            value="hybrid",
        ),
        statement="Candidate aceita trabalho híbrido.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="accepted-workplace-modes/hybrid",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(hybrid_evidence, location_evidence),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="São Paulo, SP",
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Modelo híbrido.",
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (55, 55)
    location_breakdown = assessment.fit_score.breakdown[3]
    assert (
        location_breakdown.dimension.value,
        location_breakdown.weight,
        location_breakdown.awarded_points,
        location_breakdown.covered_weight,
    ) == ("location-workplace-mode", 15, 15, 15)
    location_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.dimension.value == "location-workplace-mode"
    )
    assert tuple(
        (
            item.requirement.subject.kind.value,
            item.requirement.subject.value,
            item.status.value,
            item.maximum_points,
        )
        for item in location_assessments
    ) == (
        ("location", "sao paulo, sp", "met", 8),
        ("workplace-mode", "hybrid", "met", 7),
    )
    assert tuple(item.evidence for item in location_assessments) == (
        (location_evidence,),
        (hybrid_evidence,),
    )
    assert tuple(item.requirement.subject.kind.value for item in assessment.strengths) == (
        "job-category",
        "location",
        "workplace-mode",
    )


def test_discover_marks_equivalent_search_criteria_location_as_met() -> None:
    posting = _synthetic_posting(location="Rio de Janeiro, RJ")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    location_assessment = next(
        item
        for item in result.match_assessments[0].requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    assert location_assessment.status.value == "met"


def test_discover_normalizes_full_state_name_only_for_location_matching() -> None:
    original_location = "Rio de Janeiro, Estado do Rio de Janeiro"
    posting = _synthetic_posting(location=original_location)
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    location_assessment = next(
        item
        for item in result.match_assessments[0].requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    assert (
        location_assessment.requirement.subject.value,
        location_assessment.status.value,
        result.postings[0].location,
        result.opportunities[0].location,
    ) == (
        "rio de janeiro, rj",
        "met",
        original_location,
        original_location,
    )


def test_discover_merges_equivalent_location_variants_into_one_requirement() -> None:
    city_only = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="Rio de Janeiro",
        source_url="https://jobs.example.invalid/shared",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    with_state = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://jobs.example.invalid/shared",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((city_only, with_state))).discover(
        profile,
        criteria,
    )

    location_assessments = tuple(
        item
        for item in result.match_assessments[0].requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.is_resolved,
            item.status.value,
            len(item.requirement.provenance),
        )
        for item in location_assessments
    ) == (("rio de janeiro, rj", True, "met", 2),)


def test_search_criteria_location_evidence_is_explicit_and_temporary() -> None:
    posting = _synthetic_posting(location="Rio de Janeiro, RJ")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    location_assessment = next(
        item
        for item in result.match_assessments[0].requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    derived_evidence = location_assessment.evidence[0]
    assert (
        derived_evidence.assertion,
        derived_evidence.subject,
        derived_evidence.provenance.origin,
        derived_evidence.provenance.locator,
        "execução da busca" in derived_evidence.statement,
        "não declara residência" in derived_evidence.statement,
        profile.evidence,
    ) == (
        EvidenceAssertion.SUPPORTS,
        location_assessment.requirement.subject,
        "search-criteria",
        "location",
        True,
        True,
        (),
    )


def test_equivalent_location_receives_the_full_location_dimension_weight() -> None:
    posting = _synthetic_posting(location="Rio de Janeiro, Estado do Rio de Janeiro")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    location_breakdown = next(
        item
        for item in result.match_assessments[0].fit_score.breakdown
        if item.dimension.value == "location-workplace-mode"
    )
    assert (
        location_breakdown.weight,
        location_breakdown.awarded_points,
        location_breakdown.covered_weight,
    ) == (15, 15, 15)


def test_different_city_stays_unknown_without_search_criteria_evidence() -> None:
    posting = _synthetic_posting(location="Niterói, RJ")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    location_assessment = next(
        item
        for item in result.match_assessments[0].requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    assert (
        location_assessment.status,
        location_assessment.evidence,
        result.match_assessments[0].eligibility_status,
    ) == (
        RequirementStatus.UNKNOWN,
        (),
        EligibilityStatus.UNCERTAIN,
    )


def test_search_criteria_location_evidence_does_not_leak_between_discoveries() -> None:
    posting = _synthetic_posting(location="Rio de Janeiro, RJ")
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    discovery = OpportunityDiscovery(source=StubJobSource((posting,)))

    matching_result = discovery.discover(
        profile,
        SearchCriteria(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Rio de Janeiro",
            limit=10,
        ),
    )
    different_result = discovery.discover(
        profile,
        SearchCriteria(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Niterói",
            limit=10,
        ),
    )

    statuses = tuple(
        next(
            item.status
            for item in result.match_assessments[0].requirement_assessments
            if item.requirement.subject.kind is RequirementKind.LOCATION
        )
        for result in (matching_result, different_result)
    )
    assert statuses == (RequirementStatus.MET, RequirementStatus.UNKNOWN)


def test_real_full_stack_case_matches_location_without_inferring_junior_evidence() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="candidate-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate possui evidência de Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/python",
    )
    sql_evidence = _candidate_evidence(
        evidence_id="candidate-sql",
        subject=RequirementSubject.skill("sql"),
        statement="Candidate possui evidência de SQL.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="skills/sql",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence, sql_evidence),
    )
    posting = _synthetic_posting(
        title="DESENVOLVEDOR FULL STACK - JÚNIOR (SQL | Python)",
        location="Rio de Janeiro, Estado do Rio de Janeiro",
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro",
        limit=10,
    )

    result = OpportunityDiscovery(source=StubJobSource((posting,))).discover(profile, criteria)

    assessment = result.match_assessments[0]
    location_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    junior_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SENIORITY
        and item.requirement.subject.value is Seniority.JUNIOR
    )
    assert (
        location_assessment.status,
        junior_assessment.status,
        junior_assessment.evidence,
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
        assessment.eligibility_status,
        tuple(item.id for item in result.shortlist.items),
        tuple(
            (item.dimension.value, item.weight)
            for item in assessment.fit_score.breakdown
        ),
    ) == (
        RequirementStatus.MET,
        RequirementStatus.UNKNOWN,
        (),
        80,
        80,
        EligibilityStatus.UNCERTAIN,
        ("synthetic:job-001",),
        (
            ("job-category", 40),
            ("skills", 25),
            ("entry-program-seniority", 20),
            ("location-workplace-mode", 15),
        ),
    )


def test_discover_nao_mistura_modalidade_no_assunto_de_localizacao() -> None:
    remote_evidence = Evidence(
        id="accepted-mode-remote",
        subject=RequirementSubject(
            kind=RequirementKind.WORKPLACE_MODE,
            value="remote",
        ),
        statement="Candidate aceita trabalho remoto.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="accepted-workplace-modes/remote",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(remote_evidence,),
    )
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="Brasil - remoto",
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    assessment = _discover((posting,), profile=profile).match_assessments[0]

    location_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.dimension.value == "location-workplace-mode"
    )
    assert tuple(
        (
            item.requirement.subject.kind.value,
            item.requirement.subject.value,
            item.status.value,
            item.maximum_points,
        )
        for item in location_assessments
    ) == (("workplace-mode", "remote", "met", 15),)
    assert location_assessments[0].evidence == (remote_evidence,)
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (55, 55)
    assert assessment.unknown_requirements == ()


def test_discover_mantem_localizacoes_conflitantes_como_unknown() -> None:
    sao_paulo_evidence = Evidence(
        id="accepted-location-sao-paulo",
        subject=RequirementSubject(
            kind=RequirementKind.LOCATION,
            value="são paulo, sp",
        ),
        statement="Candidate aceita oportunidades em São Paulo, SP.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="accepted-locations/sao-paulo",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(sao_paulo_evidence,),
    )
    sao_paulo_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="São Paulo, SP",
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    rio_posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location="Rio de Janeiro, RJ",
        source_url="https://mirror.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    assessment = _discover(
        (sao_paulo_posting, rio_posting),
        profile=profile,
    ).match_assessments[0]

    location_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.LOCATION
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.is_resolved,
            item.status.value,
            item.maximum_points,
            item.awarded_points,
            item.covered_points,
        )
        for item in location_assessments
    ) == (
        ("rio de janeiro, rj", False, "unknown", 8, 0, 0),
        ("sao paulo, sp", False, "unknown", 7, 0, 0),
    )
    assert location_assessments[0].evidence == ()
    assert location_assessments[1].evidence == (sao_paulo_evidence,)
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)
    assert assessment.unknown_requirements == location_assessments


def test_discover_produz_match_assessments_deterministicos() -> None:
    python_evidence = Evidence(
        id="project-python",
        subject=RequirementSubject(kind=RequirementKind.SKILL, value="python"),
        statement="Projeto desenvolvido em Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(origin="candidate-profile", locator="projects/python"),
    )
    junior_evidence = Evidence(
        id="career-goal-junior",
        subject=RequirementSubject(kind=RequirementKind.SENIORITY, value="junior"),
        statement="Candidate busca posições de nível júnior.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="career-goals/seniority",
        ),
    )
    alpha_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Software Engineer Júnior",
        company="ACME Tecnologia",
        location=None,
        source_url="https://alpha.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Conhecimento em Python.",
    )
    zeta_posting = JobPosting(
        source_name="zeta",
        external_id="z-001",
        title="QA Júnior",
        company="Zeta Labs",
        location=None,
        source_url="https://zeta.example.invalid/z-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )
    direct_profile = CandidateProfile(
        id="candidate-example",
        target_categories=(
            JobCategory.SOFTWARE_DEVELOPMENT,
            JobCategory.QUALITY_ASSURANCE,
        ),
        evidence=(python_evidence, junior_evidence),
    )
    reversed_profile = CandidateProfile(
        id="candidate-example",
        target_categories=(
            JobCategory.QUALITY_ASSURANCE,
            JobCategory.SOFTWARE_DEVELOPMENT,
        ),
        evidence=(junior_evidence, python_evidence),
    )

    direct_result = _discover(
        (zeta_posting, alpha_posting),
        profile=direct_profile,
    )
    reversed_result = _discover(
        (alpha_posting, zeta_posting),
        profile=reversed_profile,
    )

    assert direct_result.match_assessments == reversed_result.match_assessments
    assert tuple(
        (
            assessment.opportunity_id,
            assessment.fit_score.value,
            assessment.fit_score.evidence_coverage,
            assessment.fit_score.policy_version,
        )
        for assessment in direct_result.match_assessments
    ) == (
        ("alpha:a-001", 85, 85, "match-v2"),
        ("zeta:z-001", 60, 60, "match-v2"),
    )


def test_discover_exclui_blocking_unmet_sem_alterar_fit_score() -> None:
    docker_evidence = _candidate_evidence(
        evidence_id="self-assessment-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate ainda não possui conhecimento de Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/docker",
    )
    python_evidence = _candidate_evidence(
        evidence_id="self-assessment-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate ainda não possui conhecimento de Python.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/python",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence, docker_evidence),
    )
    posting = _synthetic_posting(
        summary="Requisito obrigatório: Docker. Python é desejável.",
    )

    result = _discover((posting,), profile=profile)

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    skill_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.importance.value,
            item.status.value,
        )
        for item in skill_assessments
    ) == (
        ("docker", "blocking", "unmet"),
        ("python", "preferred", "unmet"),
    )
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 65)
    assert assessment.eligibility_status.value == "ineligible"
    assert len(assessment.blocking_requirements) == 1
    assert assessment.blocking_requirements[0].assessment == skill_assessments[0]
    assert assessment.possible_blockers == ()
    assert result.opportunities == (opportunity,)
    assert result.match_assessments == (assessment,)
    assert result.shortlist.items == ()


def test_discover_mantem_blocking_unknown_como_possible_blocker() -> None:
    posting = _synthetic_posting(
        summary="Requisito obrigatório: Docker.",
    )

    result = _discover((posting,))

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    docker_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value == "docker"
    )
    assert (
        docker_assessment.requirement.importance.value,
        docker_assessment.status.value,
        docker_assessment.evidence,
    ) == ("blocking", "unknown", ())
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 40)
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert len(assessment.possible_blockers) == 1
    assert assessment.possible_blockers[0].assessment == docker_assessment
    assert result.shortlist.items == (opportunity,)


@pytest.mark.parametrize(
    "summary",
    (
        "Conhecimento em Docker não é obrigatório.",
        "Conhecimentos não são obrigatórios: Docker.",
    ),
)
def test_discover_nao_trata_requisito_negado_como_blocking(summary: str) -> None:
    docker_evidence = _candidate_evidence(
        evidence_id="self-assessment-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate ainda não possui conhecimento de Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/docker",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(docker_evidence,),
    )
    posting = _synthetic_posting(summary=summary)

    result = _discover((posting,), profile=profile)

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    docker_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value == "docker"
    )
    assert (
        docker_assessment.requirement.importance.value,
        docker_assessment.status.value,
    ) == ("unknown", "unmet")
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert assessment.possible_blockers[0].assessment == docker_assessment
    assert result.shortlist.items == (opportunity,)


def test_discover_aplica_importancia_blocking_ao_workplace_mode() -> None:
    remote_evidence = _candidate_evidence(
        evidence_id="availability-remote",
        subject=RequirementSubject.workplace_mode(WorkplaceMode.REMOTE),
        statement="Candidate não possui disponibilidade para trabalho remoto.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="availability/workplace-mode/remote",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(remote_evidence,),
    )
    posting = _synthetic_posting(summary="Trabalho remoto obrigatório.")

    result = _discover((posting,), profile=profile)

    assessment = result.match_assessments[0]
    remote_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value is WorkplaceMode.REMOTE
    )
    assert (
        remote_assessment.requirement.importance.value,
        remote_assessment.status.value,
    ) == ("blocking", "unmet")
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 55)
    assert assessment.eligibility_status.value == "ineligible"
    assert assessment.blocking_requirements[0].assessment == remote_assessment
    assert result.shortlist.items == ()


@pytest.mark.parametrize(
    "summary",
    (
        "Python obrigatório para trabalho remoto.",
        "Trabalho remoto não é obrigatório.",
    ),
)
def test_discover_nao_classifica_workplace_ambiguo_como_blocking(
    summary: str,
) -> None:
    remote_evidence = _candidate_evidence(
        evidence_id="availability-remote",
        subject=RequirementSubject.workplace_mode(WorkplaceMode.REMOTE),
        statement="Candidate não possui disponibilidade para trabalho remoto.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="availability/workplace-mode/remote",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(remote_evidence,),
    )
    posting = _synthetic_posting(summary=summary)

    result = _discover((posting,), profile=profile)

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    remote_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value is WorkplaceMode.REMOTE
    )
    assert (
        remote_assessment.requirement.importance.value,
        remote_assessment.status.value,
    ) == ("unknown", "unmet")
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert remote_assessment in tuple(
        blocker.assessment for blocker in assessment.possible_blockers
    )
    assert result.shortlist.items == (opportunity,)


def test_discover_trata_lista_entry_level_unmet_como_possible_blocker() -> None:
    internship_evidence = _candidate_evidence(
        evidence_id="career-goal-internship",
        subject=RequirementSubject.entry_program(EntryProgram.INTERNSHIP),
        statement="Candidate busca oportunidades de estágio.",
        assertion=EvidenceAssertion.SUPPORTS,
        locator="career-goals/entry-program",
    )
    docker_evidence = _candidate_evidence(
        evidence_id="self-assessment-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate ainda não possui conhecimento de Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/docker",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(docker_evidence, internship_evidence),
    )
    posting = _synthetic_posting(
        title="Estagiário Desenvolvedor",
        summary="Requisitos: Docker.",
    )

    result = _discover((posting,), profile=profile)

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    docker_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value == "docker"
    )
    assert (
        docker_assessment.requirement.importance.value,
        docker_assessment.status.value,
    ) == ("unknown", "unmet")
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (60, 85)
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert len(assessment.possible_blockers) == 1
    assert assessment.possible_blockers[0].assessment == docker_assessment
    assert result.shortlist.items == (opportunity,)


def test_discover_nao_cria_blocker_para_requirement_preferred_unmet() -> None:
    docker_evidence = _candidate_evidence(
        evidence_id="self-assessment-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate ainda não possui conhecimento de Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/docker",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(docker_evidence,),
    )
    posting = _synthetic_posting(summary="Conhecimento em Docker é desejável.")

    result = _discover((posting,), profile=profile)

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    docker_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value == "docker"
    )
    assert (
        docker_assessment.requirement.importance.value,
        docker_assessment.status.value,
    ) == ("preferred", "unmet")
    assert (
        assessment.fit_score.value,
        assessment.fit_score.evidence_coverage,
    ) == (40, 65)
    assert assessment.eligibility_status.value == "eligible"
    assert assessment.blocking_requirements == ()
    assert assessment.possible_blockers == ()
    assert result.shortlist.items == (opportunity,)


def test_discover_mantem_importancia_conflitante_como_possible_blocker() -> None:
    docker_evidence = _candidate_evidence(
        evidence_id="self-assessment-docker",
        subject=RequirementSubject.skill("docker"),
        statement="Candidate ainda não possui conhecimento de Docker.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/docker",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(docker_evidence,),
    )
    blocking_posting = JobPosting(
        source_name="alpha",
        external_id="a-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/shared",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        summary="Requisito obrigatório: Docker.",
    )
    preferred_posting = JobPosting(
        source_name="beta",
        external_id="b-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/shared",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
        summary="Docker é desejável.",
    )

    result = _discover(
        (preferred_posting, blocking_posting),
        profile=profile,
    )

    opportunity = result.opportunities[0]
    assessment = result.match_assessments[0]
    docker_assessment = next(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.value == "docker"
    )
    assert (
        docker_assessment.requirement.importance.value,
        docker_assessment.status.value,
    ) == ("unknown", "unmet")
    assert docker_assessment.requirement.provenance == (
        Provenance(origin="alpha", locator="a-001#summary"),
        Provenance(origin="beta", locator="b-001#summary"),
    )
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert assessment.possible_blockers[0].assessment == docker_assessment
    assert result.shortlist.items == (opportunity,)


def test_discover_nao_propaga_marcador_blocking_ambiguo_entre_skills() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="self-assessment-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate ainda não possui conhecimento de Python.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/python",
    )
    sql_evidence = _candidate_evidence(
        evidence_id="self-assessment-sql",
        subject=RequirementSubject.skill("sql"),
        statement="Candidate ainda não possui conhecimento de SQL.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/sql",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(sql_evidence, python_evidence),
    )
    posting = _synthetic_posting(summary="Python obrigatório e SQL.")

    result = _discover((posting,), profile=profile)

    assessment = result.match_assessments[0]
    skill_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.importance.value,
            item.status.value,
        )
        for item in skill_assessments
    ) == (
        ("python", "unknown", "unmet"),
        ("sql", "unknown", "unmet"),
    )
    assert assessment.eligibility_status.value == "uncertain"
    assert assessment.blocking_requirements == ()
    assert (
        tuple(blocker.assessment for blocker in assessment.possible_blockers) == skill_assessments
    )
    assert result.shortlist.items == result.opportunities


def test_discover_aplica_header_blocking_coletivo_a_todas_as_skills() -> None:
    python_evidence = _candidate_evidence(
        evidence_id="self-assessment-python",
        subject=RequirementSubject.skill("python"),
        statement="Candidate ainda não possui conhecimento de Python.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/python",
    )
    sql_evidence = _candidate_evidence(
        evidence_id="self-assessment-sql",
        subject=RequirementSubject.skill("sql"),
        statement="Candidate ainda não possui conhecimento de SQL.",
        assertion=EvidenceAssertion.CONTRADICTS,
        locator="self-assessment/sql",
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(python_evidence, sql_evidence),
    )
    posting = _synthetic_posting(summary="Requisitos obrigatórios: Python e SQL.")

    result = _discover((posting,), profile=profile)

    assessment = result.match_assessments[0]
    skill_assessments = tuple(
        item
        for item in assessment.requirement_assessments
        if item.requirement.subject.kind is RequirementKind.SKILL
    )
    assert tuple(
        (
            item.requirement.subject.value,
            item.requirement.importance.value,
            item.status.value,
        )
        for item in skill_assessments
    ) == (
        ("python", "blocking", "unmet"),
        ("sql", "blocking", "unmet"),
    )
    assert assessment.eligibility_status.value == "ineligible"
    assert (
        tuple(blocker.assessment for blocker in assessment.blocking_requirements)
        == skill_assessments
    )
    assert assessment.possible_blockers == ()
    assert result.shortlist.items == ()


def test_discover_ordena_shortlist_por_status_score_data_e_id() -> None:
    python_evidence = Evidence(
        id="project-python",
        subject=RequirementSubject.skill("python"),
        statement="Projeto desenvolvido em Python.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="projects/python",
        ),
    )
    junior_evidence = Evidence(
        id="career-goal-junior",
        subject=RequirementSubject.seniority(Seniority.JUNIOR),
        statement="Candidate busca posições de nível júnior.",
        assertion=EvidenceAssertion.SUPPORTS,
        provenance=Provenance(
            origin="candidate-profile",
            locator="career-goals/seniority",
        ),
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(junior_evidence, python_evidence),
    )

    def posting(
        external_id: str,
        *,
        title: str = "Software Engineer",
        summary: str | None = None,
        source_updated_at: datetime | None = None,
    ) -> JobPosting:
        return JobPosting(
            source_name="rank",
            external_id=external_id,
            title=title,
            company=f"Company {external_id}",
            location=None,
            source_url=f"https://jobs.example.invalid/{external_id}",
            collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            summary=summary,
            source_updated_at=source_updated_at,
        )

    postings = (
        posting(
            "uncertain-40",
            summary="Requisito obrigatório: Docker.",
            source_updated_at=datetime(2026, 8, 23, 12, tzinfo=UTC),
        ),
        posting("beta"),
        posting(
            "updated-old",
            source_updated_at=datetime(2026, 8, 20, 12, tzinfo=UTC),
        ),
        posting(
            "uncertain-60",
            title="Software Engineer Júnior",
            summary="Requisito obrigatório: Docker.",
            source_updated_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
        ),
        posting("alpha"),
        posting(
            "score-65",
            summary="Python é desejável.",
            source_updated_at=datetime(2026, 8, 19, 12, tzinfo=UTC),
        ),
        posting(
            "updated-new",
            source_updated_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        ),
    )

    direct_result = _discover(postings, profile=profile)
    reversed_result = _discover(tuple(reversed(postings)), profile=profile)

    expected_ids = (
        "rank:score-65",
        "rank:updated-new",
        "rank:updated-old",
        "rank:alpha",
        "rank:beta",
        "rank:uncertain-60",
        "rank:uncertain-40",
    )
    assert tuple(item.id for item in direct_result.shortlist.items) == expected_ids
    assert tuple(item.id for item in reversed_result.shortlist.items) == expected_ids
    assert direct_result.criteria.career_preference is None
    assert all(
        assessment.career_preference_assessment is None
        for assessment in direct_result.match_assessments
    )


def test_discover_trata_atualizacao_sem_timezone_como_desconhecida() -> None:
    naive_newer = JobPosting(
        source_name="rank",
        external_id="naive-newer",
        title="Software Engineer",
        company="Naive Company",
        location=None,
        source_url="https://jobs.example.invalid/naive-newer",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        source_updated_at=datetime(2026, 8, 22, 12),
    )
    aware_older = JobPosting(
        source_name="rank",
        external_id="aware-older",
        title="Software Engineer",
        company="Aware Company",
        location=None,
        source_url="https://jobs.example.invalid/aware-older",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        source_updated_at=datetime(2026, 8, 20, 12, tzinfo=UTC),
    )

    result = _discover((naive_newer, aware_older))

    assert tuple(item.id for item in result.shortlist.items) == (
        "rank:aware-older",
        "rank:naive-newer",
    )


def test_discover_ordena_por_atualizacao_mais_recente_dos_postings_consolidados() -> None:
    consolidated_old = JobPosting(
        source_name="rank",
        external_id="consolidated",
        title="Software Engineer",
        company="Consolidated Company",
        location=None,
        source_url="https://a.example.invalid/consolidated",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        source_updated_at=datetime(2026, 8, 19, 12, tzinfo=UTC),
    )
    consolidated_new = JobPosting(
        source_name="rank",
        external_id="consolidated",
        title="Software Engineer",
        company="Consolidated Company",
        location=None,
        source_url="https://z.example.invalid/consolidated",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
        source_updated_at=datetime(2026, 8, 22, 12, tzinfo=UTC),
    )
    single = JobPosting(
        source_name="rank",
        external_id="single",
        title="Software Engineer",
        company="Single Company",
        location=None,
        source_url="https://jobs.example.invalid/single",
        collected_at=datetime(2026, 8, 21, 14, tzinfo=UTC),
        source_updated_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    result = _discover((consolidated_old, single, consolidated_new))

    assert tuple(item.id for item in result.shortlist.items) == (
        "rank:consolidated",
        "rank:single",
    )
    assert result.shortlist.items[0].postings == (
        consolidated_old,
        consolidated_new,
    )


def test_discover_limita_shortlist_sem_truncar_resultado_auditavel() -> None:
    postings = tuple(
        JobPosting(
            source_name="synthetic",
            external_id=external_id,
            title="Software Engineer",
            company=f"Company {external_id}",
            location=None,
            source_url=f"https://jobs.example.invalid/{external_id}",
            collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        )
        for external_id in ("charlie", "bravo", "alpha")
    )

    result = _discover(postings, limit=2)

    assert result.postings == postings
    assert tuple(item.id for item in result.opportunities) == (
        "synthetic:alpha",
        "synthetic:bravo",
        "synthetic:charlie",
    )
    assert tuple(item.opportunity_id for item in result.match_assessments) == (
        "synthetic:alpha",
        "synthetic:bravo",
        "synthetic:charlie",
    )
    assert tuple(item.id for item in result.shortlist.items) == (
        "synthetic:alpha",
        "synthetic:bravo",
    )


def test_discover_expoe_versao_da_politica_de_matching_e_ordering() -> None:
    posting = JobPosting(
        source_name="synthetic",
        external_id="job-001",
        title="Software Engineer",
        company="ACME Tecnologia",
        location=None,
        source_url="https://jobs.example.invalid/job-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )

    result = _discover((posting,))

    assert result.policy_version == "match-v2"
    assert result.match_assessments[0].fit_score.policy_version == result.policy_version


def test_discover_rejeita_categoria_que_nao_pertence_ao_candidate_profile() -> None:
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.DATA,
        location="Brasil",
        limit=10,
    )

    with pytest.raises(
        InvalidDiscoveryRequest,
        match="JobCategory data não pertence ao CandidateProfile",
    ):
        OpportunityDiscovery(source=StubJobSource(())).discover(profile, criteria)


def test_discover_executa_fluxo_normal_com_multi_source_job_source() -> None:
    p1 = JobPosting(
        source_name="synthetic-a",
        external_id="a-001",
        title="Desenvolvedor Python Júnior",
        company="Empresa Alpha",
        location="Rio de Janeiro, RJ",
        source_url="https://jobs-a.example.invalid/a-001",
        collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
    )
    p2 = JobPosting(
        source_name="synthetic-b",
        external_id="b-001",
        title="Desenvolvedor Python Pleno",
        company="Empresa Beta",
        location="São Paulo, SP",
        source_url="https://jobs-b.example.invalid/b-001",
        collected_at=datetime(2026, 8, 21, 13, tzinfo=UTC),
    )

    class NamedStubJobSource:
        def __init__(
            self,
            name: str,
            responses_by_keywords: dict[str, tuple[JobPosting, ...]],
        ) -> None:
            self._name = name
            self._responses_by_keywords = responses_by_keywords
            self.received_queries: list[JobSourceQuery] = []

        @property
        def name(self) -> str:
            return self._name

        def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
            self.received_queries.append(query)
            return self._responses_by_keywords.get(query.keywords, ())

    source_a = NamedStubJobSource("synthetic-a", {"estágio desenvolvimento": (p1,)})
    source_b = NamedStubJobSource(
        "synthetic-b",
        {"desenvolvedor python júnior": (p2,)},
    )
    multi = MultiSourceJobSource((source_a, source_b))

    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    result = OpportunityDiscovery(source=multi).discover(profile, criteria)

    assert result.postings == (p1, p2)
    assert len(result.opportunities) == 2
    assert len(result.match_assessments) == 2
    assert len(result.shortlist.items) == 2
    assert result.source_report.source_name == "multi-source"
    assert result.source_report.postings_received == 2
    expected_keywords = [
        "estágio desenvolvimento",
        "desenvolvedor python júnior",
        "desenvolvedor de software",
    ]
    assert [query.keywords for query in source_a.received_queries] == expected_keywords
    assert [query.keywords for query in source_b.received_queries] == expected_keywords


def test_discover_executes_every_strategy_query_in_order() -> None:
    source = RecordingJobSource()
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro, RJ",
        limit=7,
    )

    OpportunityDiscovery(source=source).discover(profile, criteria)

    assert source.received_queries == [
        JobSourceQuery("estágio desenvolvimento", "Rio de Janeiro, RJ", 7),
        JobSourceQuery("desenvolvedor python júnior", "Rio de Janeiro, RJ", 7),
        JobSourceQuery("desenvolvedor de software", "Rio de Janeiro, RJ", 7),
    ]


def test_discover_combines_results_from_different_queries() -> None:
    internship = _synthetic_posting(
        external_id="internship-001",
        title="Estágio em Desenvolvimento",
    )
    junior = _synthetic_posting(
        external_id="junior-001",
        title="Desenvolvedor Python Júnior",
    )
    source = RecordingJobSource(
        {
            "estágio desenvolvimento": (internship,),
            "desenvolvedor python júnior": (junior,),
        }
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert result.postings == (internship, junior)


def test_discover_consolidates_a_posting_repeated_between_queries() -> None:
    repeated = _synthetic_posting(
        external_id="repeated-001",
        title="Desenvolvedor Python Júnior",
    )
    source = RecordingJobSource(
        {
            "estágio desenvolvimento": (repeated,),
            "desenvolvedor python júnior": (repeated,),
        }
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert result.postings == (repeated, repeated)
    assert tuple(opportunity.id for opportunity in result.opportunities) == (
        "synthetic:repeated-001",
    )


def test_discover_assesses_opportunities_found_by_entry_level_queries() -> None:
    posting = _synthetic_posting(
        external_id="internship-001",
        title="Estágio em Desenvolvimento Python",
    )
    source = RecordingJobSource({"estágio desenvolvimento": (posting,)})
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert tuple(
        (assessment.opportunity_id, assessment.fit_score.policy_version)
        for assessment in result.match_assessments
    ) == (("synthetic:internship-001", "match-v2"),)


def test_discover_limits_the_combined_shortlist_to_criteria_limit() -> None:
    source = RecordingJobSource(
        {
            "estágio desenvolvimento": (
                _synthetic_posting(external_id="job-001"),
            ),
            "desenvolvedor de software": (
                _synthetic_posting(external_id="job-002"),
            ),
            "desenvolvedor python júnior": (
                _synthetic_posting(external_id="job-003"),
            ),
        }
    )
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=2,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert (len(result.opportunities), len(result.shortlist.items)) == (3, 2)


def test_discover_continues_after_queries_with_empty_results() -> None:
    generic = _synthetic_posting(
        external_id="generic-001",
        title="Desenvolvedor de Software",
    )
    source = RecordingJobSource({"desenvolvedor de software": (generic,)})
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    result = OpportunityDiscovery(source=source).discover(profile, criteria)

    assert result.postings == (generic,)

