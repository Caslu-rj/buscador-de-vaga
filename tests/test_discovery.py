from datetime import UTC, datetime

import pytest

from buscador_de_vaga.discovery import (
    DiscoveryResult,
    InvalidDiscoveryRequest,
    OpportunityDiscovery,
)
from buscador_de_vaga.domain import (
    CandidateProfile,
    Evidence,
    EvidenceAssertion,
    JobCategory,
    JobPosting,
    Provenance,
    RequirementKind,
    RequirementSubject,
    SearchCriteria,
)


class StubJobSource:
    name = "synthetic"

    def __init__(self, postings: tuple[JobPosting, ...]) -> None:
        self._postings = postings

    def search(self, query: object) -> tuple[JobPosting, ...]:
        return self._postings


def _discover(
    postings: tuple[JobPosting, ...],
    *,
    profile: CandidateProfile | None = None,
) -> DiscoveryResult:
    candidate_profile = profile or CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )
    return OpportunityDiscovery(source=StubJobSource(postings)).discover(
        candidate_profile,
        criteria,
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
    ) == (40, 40, "match-v1")
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
    assert (
        category_assessment.requirement.subject.value
        is JobCategory.SOFTWARE_DEVELOPMENT
    )
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
                        "CandidateProfile declara software-development em "
                        "target_categories."
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
    assert tuple(
        item.requirement.subject.kind.value for item in assessment.strengths
    ) == ("job-category", "skill")
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
    assert tuple(
        item.requirement.subject.kind.value for item in assessment.strengths
    ) == ("job-category",)
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
        summary=(
            "Requisitos: conhecimento em Python. "
            "Produto desenvolvido em SQL."
        ),
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
    assert tuple(
        item.requirement.subject.kind.value for item in assessment.strengths
    ) == ("job-category",)
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
    assert tuple(gap.requirement.subject.value for gap in assessment.skill_gaps) == (
        "sql",
    )
    assert tuple(
        item.requirement.subject.value for item in assessment.unknown_requirements
    ) == ("docker",)


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
    assert tuple(
        item.requirement.subject.kind.value for item in assessment.strengths
    ) == ("job-category", "seniority")


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
        ("location", "são paulo, sp", "met", 8),
        ("workplace-mode", "hybrid", "met", 7),
    )
    assert tuple(item.evidence for item in location_assessments) == (
        (location_evidence,),
        (hybrid_evidence,),
    )
    assert tuple(
        item.requirement.subject.kind.value for item in assessment.strengths
    ) == ("job-category", "location", "workplace-mode")


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
        ("são paulo, sp", False, "unknown", 7, 0, 0),
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
        ("alpha:a-001", 85, 85, "match-v1"),
        ("zeta:z-001", 60, 60, "match-v1"),
    )


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
