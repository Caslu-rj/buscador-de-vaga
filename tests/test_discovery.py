from datetime import UTC, datetime

import pytest

from buscador_de_vaga.discovery import (
    DiscoveryResult,
    InvalidDiscoveryRequest,
    OpportunityDiscovery,
)
from buscador_de_vaga.domain import (
    CandidateProfile,
    JobCategory,
    JobPosting,
    SearchCriteria,
)


class StubJobSource:
    name = "synthetic"

    def __init__(self, postings: tuple[JobPosting, ...]) -> None:
        self._postings = postings

    def search(self, query: object) -> tuple[JobPosting, ...]:
        return self._postings


def _discover(postings: tuple[JobPosting, ...]) -> DiscoveryResult:
    profile = CandidateProfile(
        id="candidate-example",
        target_categories=(JobCategory.SOFTWARE_DEVELOPMENT,),
    )
    criteria = SearchCriteria(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )
    return OpportunityDiscovery(source=StubJobSource(postings)).discover(profile, criteria)


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
