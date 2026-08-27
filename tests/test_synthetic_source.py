import json
from datetime import UTC, datetime
from pathlib import Path

from buscador_de_vaga.domain import JobPosting, JobSourceQuery
from buscador_de_vaga.sources.synthetic import SyntheticJobSource


def test_synthetic_source_decodifica_a_fixture_e_preserva_timestamps(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "job-postings.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_name": "synthetic",
                "query": {
                    "keywords": "desenvolvedor de software",
                    "location": "Rio de Janeiro, RJ",
                },
                "postings": [
                    {
                        "external_id": "job-001",
                        "title": "Desenvolvedor(a) Python Júnior",
                        "company": "ACME Tecnologia",
                        "location": "Rio de Janeiro, RJ",
                        "source_url": "https://jobs.example.invalid/job-001",
                        "collected_at": "2026-08-21T12:00:00Z",
                        "source_updated_at": "2026-08-20T18:30:00-03:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    source = SyntheticJobSource.from_file(fixture_path)
    postings = source.search(
        JobSourceQuery(
            keywords="desenvolvedor de software",
            location="Rio de Janeiro, RJ",
            limit=10,
        )
    )

    assert source.name == "synthetic"
    assert postings == (
        JobPosting(
            source_name="synthetic",
            external_id="job-001",
            title="Desenvolvedor(a) Python Júnior",
            company="ACME Tecnologia",
            location="Rio de Janeiro, RJ",
            source_url="https://jobs.example.invalid/job-001",
            collected_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            source_updated_at=datetime.fromisoformat("2026-08-20T18:30:00-03:00"),
        ),
    )


def test_synthetic_source_returns_empty_for_other_keywords_in_the_same_search(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "job-postings.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_name": "synthetic",
                "query": {
                    "keywords": "desenvolvedor de software",
                    "location": "Brasil",
                },
                "postings": [],
            }
        ),
        encoding="utf-8",
    )
    source = SyntheticJobSource.from_file(fixture_path)

    postings = source.search(
        JobSourceQuery(
            keywords="estágio desenvolvimento",
            location="Brasil",
            limit=10,
        )
    )

    assert postings == ()
