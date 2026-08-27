"""Testes unitários e de integração para posicionamento de perfil e busca autônoma (#48)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from buscador_de_vaga.candidate_positioning import (
    AUTOMATIC_CATEGORY_SELECTION_THRESHOLD,
    CandidateCareerAlignment,
    CandidateCareerLevel,
    CandidateProfileConfidence,
    assess_candidate_profile,
)
from buscador_de_vaga.cli import main
from buscador_de_vaga.discovery import _AutomaticOpportunityDiscovery
from buscador_de_vaga.domain import (
    CandidateProfile,
    EntryProgram,
    Evidence,
    EvidenceAssertion,
    FitDimension,
    JobCategory,
    JobPosting,
    JobSourceQuery,
    Provenance,
    RequirementKind,
    RequirementSubject,
    RequirementSubjectValue,
    Seniority,
)
from buscador_de_vaga.search_strategy import AutomaticCareerSearchStrategy
from buscador_de_vaga.sources import MultiSourceJobSource


class StubJobSource:
    name: str = "stub"

    def __init__(self, postings: tuple[JobPosting, ...] | list[JobPosting] = ()) -> None:
        self._postings = tuple(postings)
        self.queries_received: list[JobSourceQuery] = []

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        self.queries_received.append(query)
        return self._postings


def _make_posting(
    external_id: str,
    title: str,
    company: str | None = "ACME",
    location: str | None = "Brasil",
    source_url: str | None = None,
    collected_at: datetime | None = None,
) -> JobPosting:
    if source_url is None:
        source_url = f"https://example.invalid/job-{external_id}"
    if collected_at is None:
        collected_at = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    return JobPosting(
        source_name="stub",
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        source_url=source_url,
        collected_at=collected_at,
        summary=None,
        source_updated_at=None,
    )


def _create_sample_evidence(
    kind: RequirementKind,
    value: RequirementSubjectValue,
    assertion: EvidenceAssertion = EvidenceAssertion.SUPPORTS,
    ev_id: str = "ev-1",
    *,
    origin: str = "test",
    locator: str = "loc-1",
) -> Evidence:
    return Evidence(
        id=ev_id,
        statement=f"Evidence for {kind.value}:{value}",
        assertion=assertion,
        subject=RequirementSubject(kind=kind, value=value),
        provenance=Provenance(origin=origin, locator=locator),
    )


def test_1_analise_de_todas_as_categorias() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(),
    )
    assessment = assess_candidate_profile(profile)

    assert len(assessment.category_assessments) == len(JobCategory)
    assessed_categories = {a.category for a in assessment.category_assessments}
    assert assessed_categories == set(JobCategory)


def test_2_score_deterministico() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "python", ev_id="ev-py"),
            _create_sample_evidence(RequirementKind.SKILL, "git", ev_id="ev-git"),
        ),
    )
    res1 = assess_candidate_profile(profile)
    res2 = assess_candidate_profile(profile)
    assert res1 == res2


def test_3_python_e_git_favorecem_software() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(RequirementKind.SKILL, "python", ev_id="ev-py"),
            _create_sample_evidence(RequirementKind.SKILL, "git", ev_id="ev-git"),
        ),
    )
    assessment = assess_candidate_profile(profile)
    sw_cat = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert sw_cat is not None
    assert sw_cat.profile_score == 80
    assert sw_cat.confidence is CandidateProfileConfidence.HIGH


def test_4_sql_e_python_contribuem_para_data() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "sql", ev_id="ev-sql"),
            _create_sample_evidence(RequirementKind.SKILL, "python", ev_id="ev-py"),
        ),
    )
    assessment = assess_candidate_profile(profile)
    data_cat = assessment.get_assessment(JobCategory.DATA)
    assert data_cat is not None
    assert data_cat.profile_score == 20


def test_5_multiplas_categorias_sao_possiveis() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "python", ev_id="ev-py"),
            _create_sample_evidence(RequirementKind.SKILL, "git", ev_id="ev-git"),
            _create_sample_evidence(RequirementKind.SKILL, "sql", ev_id="ev-sql"),
        ),
    )
    assessment = assess_candidate_profile(profile)
    selected = assessment.selected_categories
    assert JobCategory.SOFTWARE_DEVELOPMENT in selected
    assert JobCategory.DATA in selected or JobCategory.SYSTEMS in selected


def test_6_ausencia_de_evidence_nao_gera_contradicts() -> None:
    profile = CandidateProfile(id="p-1", target_categories=(), evidence=())
    assessment = assess_candidate_profile(profile)
    for cat_ass in assessment.category_assessments:
        assert cat_ass.profile_score == 0
        assert cat_ass.confidence is CandidateProfileConfidence.NONE
        assert cat_ass.recommended_levels == (CandidateCareerLevel.UNKNOWN,)


def test_7_junior_explicito() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-level",
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    sw_cat = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert sw_cat is not None
    assert CandidateCareerLevel.JUNIOR in sw_cat.recommended_levels


def test_8_mid_level_explicito() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.MID_LEVEL,
                ev_id="ev-level",
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    sw_cat = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert sw_cat is not None
    assert CandidateCareerLevel.MID_LEVEL in sw_cat.recommended_levels


def test_9_senior_explicito() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.SENIOR,
                ev_id="ev-level",
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    sw_cat = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert sw_cat is not None
    assert CandidateCareerLevel.SENIOR in sw_cat.recommended_levels


def test_10_internship_explicito() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.ENTRY_PROGRAM,
                EntryProgram.INTERNSHIP,
                ev_id="ev-level",
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    sw_cat = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert sw_cat is not None
    assert CandidateCareerLevel.INTERNSHIP in sw_cat.recommended_levels


def test_senior_explicito_nao_vaza_para_categoria_descoberta_somente_por_skill() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.SENIOR,
                ev_id="ev-level",
            ),
            _create_sample_evidence(
                RequirementKind.SKILL,
                "python",
                ev_id="ev-python",
            ),
        ),
    )

    assessment = assess_candidate_profile(profile)

    software = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    data = assessment.get_assessment(JobCategory.DATA)
    assert software is not None
    assert data is not None
    assert software.recommended_levels == (CandidateCareerLevel.SENIOR,)
    assert CandidateCareerLevel.SENIOR not in data.recommended_levels


def test_senioridade_compartilha_provenance_somente_com_a_categoria_aplicavel() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-software",
                locator="section:experiencia#line:1",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.SENIOR,
                ev_id="ev-senior-software",
                locator="section:experiencia#line:1",
            ),
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.DATA,
                ev_id="ev-data",
                locator="section:experiencia#line:2",
            ),
        ),
    )

    assessment = assess_candidate_profile(profile)
    software = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    data = assessment.get_assessment(JobCategory.DATA)

    assert software is not None
    assert data is not None
    assert software.recommended_levels == (CandidateCareerLevel.SENIOR,)
    assert software.evidence_ids == ("ev-software", "ev-senior-software")
    assert data.recommended_levels == (
        CandidateCareerLevel.JUNIOR,
        CandidateCareerLevel.INTERNSHIP,
    )
    assert data.evidence_ids == ("ev-data",)


def test_senioridade_ambigua_nao_e_espalhada_por_categorias_explicitas() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-software",
                locator="line:1",
            ),
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.DATA,
                ev_id="ev-data",
                locator="line:2",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.SENIOR,
                ev_id="ev-senior-ambiguo",
                locator="line:3",
            ),
        ),
    )

    assessment = assess_candidate_profile(profile)
    software = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    data = assessment.get_assessment(JobCategory.DATA)

    assert software is not None
    assert data is not None
    assert CandidateCareerLevel.SENIOR not in software.recommended_levels
    assert CandidateCareerLevel.SENIOR not in data.recommended_levels
    assert "ev-senior-ambiguo" not in software.evidence_ids
    assert "ev-senior-ambiguo" not in data.evidence_ids


def test_categoria_explicita_unica_aceita_senioridade_sem_provenance_compartilhada() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.DATA,
                ev_id="ev-data",
                locator="line:1",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.MID_LEVEL,
                ev_id="ev-mid",
                locator="line:2",
            ),
        ),
    )

    data = assess_candidate_profile(profile).get_assessment(JobCategory.DATA)

    assert data is not None
    assert data.recommended_levels == (CandidateCareerLevel.MID_LEVEL,)
    assert data.evidence_ids == ("ev-data", "ev-mid")


def test_target_category_legada_unica_aceita_senioridade_explicita() -> None:
    profile = CandidateProfile(
        id="legacy",
        target_categories=(JobCategory.SYSTEMS,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
        ),
    )

    systems = assess_candidate_profile(profile).get_assessment(JobCategory.SYSTEMS)

    assert systems is not None
    assert systems.recommended_levels == (CandidateCareerLevel.JUNIOR,)
    assert systems.evidence_ids == ("ev-junior",)


@pytest.mark.parametrize(
    "left_level,right_level",
    [
        (Seniority.JUNIOR, Seniority.MID_LEVEL),
        (Seniority.JUNIOR, Seniority.SENIOR),
        (Seniority.MID_LEVEL, Seniority.SENIOR),
    ],
)
def test_senioridades_conflitantes_na_mesma_categoria_resultam_em_unknown(
    left_level: Seniority,
    right_level: Seniority,
) -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                left_level,
                ev_id=f"ev-{left_level.value}",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                right_level,
                ev_id=f"ev-{right_level.value}",
            ),
        ),
    )

    software = assess_candidate_profile(profile).get_assessment(
        JobCategory.SOFTWARE_DEVELOPMENT
    )

    assert software is not None
    assert software.recommended_levels == (CandidateCareerLevel.UNKNOWN,)
    assert "conflitantes" in software.reason


def test_junior_e_internship_podem_coexistir_na_mesma_categoria() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
            _create_sample_evidence(
                RequirementKind.ENTRY_PROGRAM,
                EntryProgram.INTERNSHIP,
                ev_id="ev-internship",
            ),
        ),
    )

    software = assess_candidate_profile(profile).get_assessment(
        JobCategory.SOFTWARE_DEVELOPMENT
    )

    assert software is not None
    assert software.recommended_levels == (
        CandidateCareerLevel.JUNIOR,
        CandidateCareerLevel.INTERNSHIP,
    )


def test_ordem_das_evidences_nao_altera_o_assessment() -> None:
    evidence = (
        _create_sample_evidence(
            RequirementKind.JOB_CATEGORY,
            JobCategory.SOFTWARE_DEVELOPMENT,
            ev_id="ev-category",
        ),
        _create_sample_evidence(
            RequirementKind.SENIORITY,
            Seniority.JUNIOR,
            ev_id="ev-junior",
        ),
        _create_sample_evidence(
            RequirementKind.ENTRY_PROGRAM,
            EntryProgram.INTERNSHIP,
            ev_id="ev-internship",
        ),
    )

    forward = assess_candidate_profile(
        CandidateProfile(id="p-1", target_categories=(), evidence=evidence)
    )
    reversed_assessment = assess_candidate_profile(
        CandidateProfile(id="p-1", target_categories=(), evidence=tuple(reversed(evidence)))
    )

    assert forward == reversed_assessment


def test_11_sem_senioridade_explicita_nunca_gerar_mid_level_ou_senior() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(_create_sample_evidence(RequirementKind.SKILL, "python"),),
    )
    assessment = assess_candidate_profile(profile)
    for cat_ass in assessment.category_assessments:
        assert CandidateCareerLevel.MID_LEVEL not in cat_ass.recommended_levels
        assert CandidateCareerLevel.SENIOR not in cat_ass.recommended_levels


def test_12_maximo_de_tres_categorias() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "python"),
            _create_sample_evidence(RequirementKind.SKILL, "git"),
            _create_sample_evidence(RequirementKind.SKILL, "sql"),
            _create_sample_evidence(RequirementKind.SKILL, "linux"),
        ),
    )
    assessment = assess_candidate_profile(profile)
    assert len(assessment.selected_categories) <= 3


def test_categoria_abaixo_do_threshold_nao_e_selecionada() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "react", ev_id="ev-react"),
        ),
    )

    assessment = assess_candidate_profile(profile)

    software = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert software is not None
    assert software.profile_score == 10
    assert AUTOMATIC_CATEGORY_SELECTION_THRESHOLD == 20
    assert assessment.selected_categories == ()


def test_categoria_no_threshold_e_selecionada() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "react", ev_id="ev-react"),
            _create_sample_evidence(
                RequirementKind.SKILL,
                "javascript",
                ev_id="ev-javascript",
            ),
        ),
    )

    assessment = assess_candidate_profile(profile)

    software = assessment.get_assessment(JobCategory.SOFTWARE_DEVELOPMENT)
    assert software is not None
    assert software.profile_score == 20
    assert assessment.selected_categories == (JobCategory.SOFTWARE_DEVELOPMENT,)


def test_13_maximo_de_seis_queries() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(RequirementKind.SKILL, "python"),
            _create_sample_evidence(RequirementKind.SKILL, "git"),
            _create_sample_evidence(RequirementKind.SKILL, "sql"),
            _create_sample_evidence(RequirementKind.SKILL, "linux"),
        ),
    )
    assessment = assess_candidate_profile(profile)
    strategy = AutomaticCareerSearchStrategy()
    queries = strategy.build_queries(
        assessment=assessment, location="Rio de Janeiro", limit=10, max_queries=6
    )
    assert len(queries) <= 6


def test_14_queries_deterministicas() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    strategy = AutomaticCareerSearchStrategy()
    q1 = strategy.build_queries(assessment=assessment, location="Brasil", limit=5)
    q2 = strategy.build_queries(assessment=assessment, location="Brasil", limit=5)
    assert q1
    assert q1 == q2


def test_15_deduplicacao_das_queries() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    strategy = AutomaticCareerSearchStrategy()
    queries = strategy.build_queries(assessment=assessment, location="Brasil", limit=5)
    unique_queries = set(queries)
    assert queries
    assert len(queries) == len(unique_queries)


def test_fallback_generico_e_adicionado_quando_ha_orcamento() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)

    queries = AutomaticCareerSearchStrategy().build_queries(
        assessment=assessment,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "desenvolvedor júnior",
        "estágio desenvolvimento",
        "desenvolvedor de software",
    )


def test_16_location_preservado() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)
    strategy = AutomaticCareerSearchStrategy()
    queries = strategy.build_queries(assessment=assessment, location="Curitiba, PR", limit=5)
    assert queries
    for q in queries:
        assert q.location == "Curitiba, PR"


def test_limit_e_preservado_em_todas_as_queries_automaticas() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
            ),
        ),
    )
    assessment = assess_candidate_profile(profile)

    queries = AutomaticCareerSearchStrategy().build_queries(
        assessment=assessment,
        location="Brasil",
        limit=7,
    )

    assert queries
    assert tuple(query.limit for query in queries) == (7, 7, 7)


def test_evidence_pessoal_nao_entra_nas_keywords_automaticas() -> None:
    private_statement = "Contato: candidate@example.com, telefone 21999999999"
    profile = CandidateProfile(
        id="candidate-private",
        target_categories=(),
        evidence=(
            Evidence(
                id="ev-private",
                subject=RequirementSubject.job_category(
                    JobCategory.SOFTWARE_DEVELOPMENT
                ),
                statement=private_statement,
                assertion=EvidenceAssertion.SUPPORTS,
                provenance=Provenance(origin="resume:private.pdf", locator="line:1"),
            ),
        ),
    )

    queries = AutomaticCareerSearchStrategy().build_queries(
        assessment=assess_candidate_profile(profile),
        location="Brasil",
        limit=10,
    )
    keywords = " ".join(query.keywords for query in queries)

    assert "candidate@example.com" not in keywords
    assert "21999999999" not in keywords
    assert "private" not in keywords


def test_automatic_search_plan_preserva_niveis_por_categoria() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
        ),
    )

    result = _AutomaticOpportunityDiscovery(source=StubJobSource()).discover(
        profile,
        location="Brasil",
    )

    assert tuple(
        (target.category, target.recommended_levels) for target in result.plan.targets
    ) == (
        (
            JobCategory.SOFTWARE_DEVELOPMENT,
            (CandidateCareerLevel.JUNIOR,),
        ),
    )


def test_fallback_generico_nao_ultrapassa_orcamento_com_multiplas_fontes() -> None:
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=tuple(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                category,
                ev_id=f"ev-{category.value}",
                locator=f"line:{index}",
            )
            for index, category in enumerate(
                (
                    JobCategory.SOFTWARE_DEVELOPMENT,
                    JobCategory.DATA,
                    JobCategory.SYSTEMS,
                ),
                start=1,
            )
        ),
    )
    first_source = StubJobSource()
    second_source = StubJobSource()
    source = MultiSourceJobSource((first_source, second_source))

    result = _AutomaticOpportunityDiscovery(source=source).discover(
        profile,
        location="Brasil",
        limit=10,
    )

    assert len(result.plan.queries) == 6
    assert len(first_source.queries_received) == 6
    assert len(second_source.queries_received) == 6
    assert all(query.location == "Brasil" for query in result.plan.queries)
    assert all(query.limit == 10 for query in result.plan.queries)


def test_17_modo_manual_continua_funcionando(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(
        '{"schema_version": 1, "id": "p-1",'
        ' "target_categories": ["software-development"], "evidence": []}',
        encoding="utf-8",
    )
    postings_file = tmp_path / "postings.json"
    postings_file.write_text(
        '{"schema_version": 1, "source_name": "synthetic",'
        ' "query": {"keywords": "desenvolvedor de software", "location": "Brasil"},'
        ' "postings": []}',
        encoding="utf-8",
    )
    exit_code = main(
        [
            "--profile",
            str(profile_file),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_file),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Nenhuma oportunidade encontrada" in out


def test_18_ausencia_de_category_ativa_modo_automatico(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(
        '{"schema_version": 1, "id": "p-1",'
        ' "target_categories": ["software-development"], "evidence": []}',
        encoding="utf-8",
    )
    postings_file = tmp_path / "postings.json"
    postings_file.write_text(
        '{"schema_version": 1, "source_name": "synthetic",'
        ' "query": {"keywords": "desenvolvedor júnior", "location": "Brasil"},'
        ' "postings": []}',
        encoding="utf-8",
    )
    exit_code = main(
        [
            "--profile",
            str(profile_file),
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_file),
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Análise automática do currículo" in out
    assert "Compatibilidade do perfil: 10/100" in out
    assert "Confiança: Baixa" in out
    assert "Níveis recomendados: Júnior, Estágio" in out
    assert "Categorias pesquisadas:" in out
    assert "software-development" in out
    assert "Consultas geradas:" in out
    assert "desenvolvedor júnior" in out
    assert "estágio desenvolvimento" in out
    assert "desenvolvedor de software" in out
    assert out.index("Análise automática do currículo") < out.index(
        "Nenhuma oportunidade encontrada"
    )


def test_cli_automatica_mostra_analise_antes_das_vagas_sem_expor_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "candidate-private",
                "target_categories": ["software-development"],
                "evidence": [
                    {
                        "id": "ev-category",
                        "subject": {
                            "kind": "job-category",
                            "value": "software-development",
                        },
                        "statement": "Contato privado: candidate@example.com",
                        "assertion": "supports",
                        "provenance": {
                            "origin": "resume:private.pdf",
                            "locator": "section:experiencia#line:1",
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    postings_file = tmp_path / "postings.json"
    postings_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_name": "synthetic",
                "query": {
                    "keywords": "desenvolvedor júnior",
                    "location": "Brasil",
                },
                "postings": [
                    {
                        "external_id": "job-1",
                        "title": "Desenvolvedor Python Júnior",
                        "company": "ACME",
                        "location": "Brasil",
                        "source_url": "https://example.invalid/job-1",
                        "collected_at": "2026-08-27T12:00:00+00:00",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--profile",
            str(profile_file),
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_file),
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert output.err == ""
    assert output.out.index("Análise automática do currículo") < output.out.index(
        "1 oportunidade encontrada"
    )
    assert "Categorias pesquisadas:" in output.out
    assert "Consultas geradas:" in output.out
    assert "candidate@example.com" not in output.out
    assert "resume:private.pdf" not in output.out


def test_19_candidate_profile_nao_e_mutado() -> None:
    evidence = (_create_sample_evidence(RequirementKind.SKILL, "python"),)
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=evidence,
    )
    original_id = profile.id
    original_targets = profile.target_categories
    original_evidence = profile.evidence

    assess_candidate_profile(profile)

    assert profile.id == original_id
    assert profile.target_categories == original_targets
    assert profile.evidence == original_evidence


def test_20_evidence_nao_e_mutada() -> None:
    ev = _create_sample_evidence(RequirementKind.SKILL, "python")
    profile = CandidateProfile(id="p-1", target_categories=(), evidence=(ev,))
    original_id = ev.id
    original_statement = ev.statement
    original_assertion = ev.assertion

    assess_candidate_profile(profile)

    assert ev.id == original_id
    assert ev.statement == original_statement
    assert ev.assertion == original_assertion


def test_21_deduplicacao_global_das_vagas() -> None:
    source = StubJobSource(
        [
            _make_posting("p-1", "Desenvolvedor Python"),
            _make_posting("p-1", "Desenvolvedor Python"),
        ]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY, JobCategory.SOFTWARE_DEVELOPMENT
            ),
        ),
    )
    discovery = _AutomaticOpportunityDiscovery(source=source)
    res = discovery.discover(profile, location="Brasil")
    assert len(res.opportunities) == 1


def test_22_ranking_automatico_deterministico() -> None:
    source = StubJobSource(
        [
            _make_posting("p-1", "Desenvolvedor Python Júnior"),
            _make_posting("p-2", "Desenvolvedor Python Sênior"),
        ]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY, JobCategory.SOFTWARE_DEVELOPMENT
            ),
        ),
    )
    discovery = _AutomaticOpportunityDiscovery(source=source)
    res1 = discovery.discover(profile, location="Brasil")
    res2 = discovery.discover(profile, location="Brasil")
    assert res1.shortlist.items == res2.shortlist.items


def test_23_senior_e_rebaixado_perante_junior_comparavel_quando_perfil_e_de_entrada() -> None:
    source = StubJobSource(
        [
            _make_posting("p-senior", "Desenvolvedor Python Sênior"),
            _make_posting("p-junior", "Desenvolvedor Python Júnior"),
        ]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY, JobCategory.SOFTWARE_DEVELOPMENT
            ),
        ),
    )
    discovery = _AutomaticOpportunityDiscovery(source=source)
    res = discovery.discover(profile, location="Brasil")
    items = res.shortlist.items
    assert len(items) == 2
    assert "Júnior" in items[0].title
    assert "Sênior" in items[1].title


def test_24_senior_continua_visivel_se_nao_houver_blocker() -> None:
    source = StubJobSource(
        [
            _make_posting("p-senior", "Desenvolvedor Python Sênior"),
        ]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY, JobCategory.SOFTWARE_DEVELOPMENT
            ),
        ),
    )
    discovery = _AutomaticOpportunityDiscovery(source=source)
    res = discovery.discover(profile, location="Brasil")
    items = res.shortlist.items
    assert len(items) == 1
    assert "Sênior" in items[0].title


def test_vaga_com_junior_e_senior_tem_alinhamento_review() -> None:
    source = StubJobSource(
        [_make_posting("p-conflict", "Desenvolvedor Python Júnior Sênior")]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
        ),
    )

    result = _AutomaticOpportunityDiscovery(source=source).discover(
        profile,
        location="Brasil",
    )

    assert result.alignments_by_opportunity_id["stub:p-conflict"] is (
        CandidateCareerAlignment.REVIEW
    )
    assert result.shortlist.items[0].id == "stub:p-conflict"


@pytest.mark.parametrize(
    "title",
    [
        "Programa de Estágio para Desenvolvedor Sênior",
        "Desenvolvedor Pleno Sênior",
    ],
)
def test_vaga_com_sinais_de_nivel_incompativeis_tem_alinhamento_review(
    title: str,
) -> None:
    source = StubJobSource([_make_posting("p-conflict", title)])
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
        ),
    )

    result = _AutomaticOpportunityDiscovery(source=source).discover(
        profile,
        location="Brasil",
    )

    assert result.alignments_by_opportunity_id["stub:p-conflict"] is (
        CandidateCareerAlignment.REVIEW
    )


def test_candidate_level_unknown_e_vaga_senior_tem_alinhamento_review() -> None:
    source = StubJobSource([_make_posting("p-senior", "Desenvolvedor Python Sênior")])
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.SENIOR,
                ev_id="ev-senior",
            ),
        ),
    )

    result = _AutomaticOpportunityDiscovery(source=source).discover(
        profile,
        location="Brasil",
    )

    assert result.alignments_by_opportunity_id["stub:p-senior"] is (
        CandidateCareerAlignment.REVIEW
    )


def test_candidate_junior_e_vaga_senior_tem_alinhamento_above_profile() -> None:
    source = StubJobSource([_make_posting("p-senior", "Desenvolvedor Python Sênior")])
    profile = CandidateProfile(
        id="p-1",
        target_categories=(),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY,
                JobCategory.SOFTWARE_DEVELOPMENT,
                ev_id="ev-category",
            ),
            _create_sample_evidence(
                RequirementKind.SENIORITY,
                Seniority.JUNIOR,
                ev_id="ev-junior",
            ),
        ),
    )

    result = _AutomaticOpportunityDiscovery(source=source).discover(
        profile,
        location="Brasil",
    )

    assert result.alignments_by_opportunity_id["stub:p-senior"] is (
        CandidateCareerAlignment.ABOVE_PROFILE
    )


def test_26_perfis_antigos_continuam_validos() -> None:
    legacy_profile = CandidateProfile(
        id="legacy-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(),
    )
    assessment = assess_candidate_profile(legacy_profile)
    assert assessment.profile_id == "legacy-1"
    assert JobCategory.SOFTWARE_DEVELOPMENT in assessment.selected_categories


def test_27_fit_score_permanece_inalterado() -> None:
    source = StubJobSource(
        [
            _make_posting("p-1", "Desenvolvedor Python Júnior"),
        ]
    )
    profile = CandidateProfile(
        id="p-1",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
        evidence=(
            _create_sample_evidence(
                RequirementKind.JOB_CATEGORY, JobCategory.SOFTWARE_DEVELOPMENT
            ),
        ),
    )
    discovery = _AutomaticOpportunityDiscovery(source=source)
    res = discovery.discover(profile, location="Brasil")
    assert len(res.match_assessments) == 1
    fit = res.match_assessments[0].fit_score
    # Dimension weights check: job-category (40), skills (25),
    # entry-program-seniority (20), location-workplace-mode (15)
    weights = {b.dimension: b.weight for b in fit.breakdown}
    assert weights[FitDimension.JOB_CATEGORY] == 40
    assert weights[FitDimension.SKILLS] == 25
    assert weights[FitDimension.ENTRY_PROGRAM_SENIORITY] == 20
    assert weights[FitDimension.LOCATION_WORKPLACE_MODE] == 15
    assert fit.policy_version == "match-v2"

