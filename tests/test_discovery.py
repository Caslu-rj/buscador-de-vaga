from datetime import UTC, datetime

import pytest

from buscador_de_vaga.discovery import InvalidDiscoveryRequest, OpportunityDiscovery
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
