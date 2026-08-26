from datetime import UTC, datetime

import pytest

from buscador_de_vaga.discovery import JobSource, JobSourceError, JobSourceFailureKind
from buscador_de_vaga.domain import JobPosting, JobSourceQuery
from buscador_de_vaga.sources.multi import MultiSourceJobSource


class DummyJobSource:
    def __init__(self, name: str, postings: tuple[JobPosting, ...]) -> None:
        self._name = name
        self._postings = postings
        self.received_queries: list[JobSourceQuery] = []

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        self.received_queries.append(query)
        return self._postings


class FailingJobSource:
    @property
    def name(self) -> str:
        return "failing-source"

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        raise JobSourceError(
            "Fonte indisponível",
            source_name=self.name,
            kind=JobSourceFailureKind.UNAVAILABLE,
            action="Tente novamente mais tarde",
            retryable=True,
        )


def _make_posting(source_name: str, external_id: str, title: str) -> JobPosting:
    return JobPosting(
        source_name=source_name,
        external_id=external_id,
        title=title,
        company="Empresa Teste",
        location="Rio de Janeiro, RJ",
        source_url=f"https://example.invalid/{source_name}/{external_id}",
        collected_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
    )


def test_multi_source_raises_value_error_if_sources_empty() -> None:
    with pytest.raises(ValueError, match="pelo menos um JobSource"):
        MultiSourceJobSource(())


def test_multi_source_satisfies_job_source_protocol_and_has_stable_name() -> None:
    source1 = DummyJobSource("source1", ())
    multi = MultiSourceJobSource((source1,))

    job_source: JobSource = multi
    assert job_source.name == "multi-source"
    assert hasattr(multi, "search")
    assert callable(multi.search)


def test_multi_source_passes_exact_same_query_to_all_sources() -> None:
    source1 = DummyJobSource("source1", ())
    source2 = DummyJobSource("source2", ())
    multi = MultiSourceJobSource((source1, source2))

    query = JobSourceQuery(
        keywords="desenvolvedor python",
        location="Rio de Janeiro, RJ",
        limit=10,
    )
    multi.search(query)

    assert len(source1.received_queries) == 1
    assert len(source2.received_queries) == 1
    assert source1.received_queries[0] is query or source1.received_queries[0] == query
    assert source2.received_queries[0] is query or source2.received_queries[0] == query


def test_multi_source_combines_results_preserving_source_and_posting_order() -> None:
    p1 = _make_posting("source1", "s1-1", "Dev 1")
    p2 = _make_posting("source1", "s1-2", "Dev 2")
    p3 = _make_posting("source2", "s2-1", "Dev 3")
    p4 = _make_posting("source2", "s2-2", "Dev 4")

    source1 = DummyJobSource("source1", (p1, p2))
    source2 = DummyJobSource("source2", (p3, p4))
    multi = MultiSourceJobSource((source1, source2))

    query = JobSourceQuery(keywords="dev", location="Brasil", limit=10)
    result = multi.search(query)

    assert result == (p1, p2, p3, p4)


def test_multi_source_preserves_posting_identity_and_provenance() -> None:
    p1 = _make_posting("source1", "s1-1", "Dev 1")
    p2 = _make_posting("source2", "s2-1", "Dev 2")

    source1 = DummyJobSource("source1", (p1,))
    source2 = DummyJobSource("source2", (p2,))
    multi = MultiSourceJobSource((source1, source2))

    query = JobSourceQuery(keywords="dev", location="Brasil", limit=10)
    result = multi.search(query)

    assert result[0].source_name == "source1"
    assert result[0].external_id == "s1-1"
    assert result[0].source_url == "https://example.invalid/source1/s1-1"

    assert result[1].source_name == "source2"
    assert result[1].external_id == "s2-1"
    assert result[1].source_url == "https://example.invalid/source2/s2-1"


def test_multi_source_works_with_single_source() -> None:
    p1 = _make_posting("source1", "s1-1", "Dev 1")
    source1 = DummyJobSource("source1", (p1,))
    multi = MultiSourceJobSource((source1,))

    query = JobSourceQuery(keywords="dev", location="Brasil", limit=10)
    assert multi.search(query) == (p1,)


def test_multi_source_handles_source_with_empty_results() -> None:
    p1 = _make_posting("source2", "s2-1", "Dev 1")

    source1 = DummyJobSource("source1", ())
    source2 = DummyJobSource("source2", (p1,))
    multi = MultiSourceJobSource((source1, source2))

    query = JobSourceQuery(keywords="dev", location="Brasil", limit=10)
    assert multi.search(query) == (p1,)


def test_multi_source_propagates_job_source_error() -> None:
    source1 = FailingJobSource()
    source2 = DummyJobSource("source2", ())
    multi = MultiSourceJobSource((source1, source2))

    query = JobSourceQuery(keywords="dev", location="Brasil", limit=10)
    with pytest.raises(JobSourceError) as exc_info:
        multi.search(query)

    assert exc_info.value.source_name == "failing-source"
    assert exc_info.value.kind == JobSourceFailureKind.UNAVAILABLE
