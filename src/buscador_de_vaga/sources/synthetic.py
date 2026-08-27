"""JobSource offline para demonstrações e testes do tracer bullet."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from buscador_de_vaga.domain import JobPosting, JobSourceQuery


class SyntheticSourceError(ValueError):
    """Indica que uma fixture sintética não representa uma busca válida."""


@dataclass(frozen=True, slots=True)
class SyntheticJobSource:
    """Adapter que reproduz uma resposta externa previamente filtrada."""

    name: str
    _expected_keywords: str
    _expected_location: str
    _postings: tuple[JobPosting, ...]

    @classmethod
    def from_file(cls, path: Path) -> "SyntheticJobSource":
        """Cria o Adapter a partir de uma fixture JSON versionada."""
        raw = _read_json(path)
        if not isinstance(raw, dict):
            raise SyntheticSourceError("a fixture sintética deve ser um objeto JSON")

        schema_version: object = raw.get("schema_version")
        if not isinstance(schema_version, int) or isinstance(schema_version, bool):
            raise SyntheticSourceError("schema_version da fixture deve ser o inteiro 1")
        if schema_version != 1:
            raise SyntheticSourceError("schema_version da fixture deve ser 1")

        source_name = _metadata_text(raw.get("source_name"), field="source_name")
        raw_query: object = raw.get("query")
        if not isinstance(raw_query, dict):
            raise SyntheticSourceError("query da fixture deve ser um objeto JSON")
        keywords = _metadata_text(raw_query.get("keywords"), field="query.keywords")
        location = _metadata_text(raw_query.get("location"), field="query.location")

        raw_postings: object = raw.get("postings")
        if not isinstance(raw_postings, list):
            raise SyntheticSourceError("postings da fixture deve ser uma lista JSON")
        postings = tuple(
            _decode_posting(item, index=index, source_name=source_name)
            for index, item in enumerate(raw_postings)
        )

        return cls(
            name=source_name,
            _expected_keywords=keywords,
            _expected_location=location,
            _postings=postings,
        )

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        """Reproduz a resposta declarada e trata outros termos como vazios."""
        if _normalize_text(query.location) != _normalize_text(self._expected_location):
            raise SyntheticSourceError("a fixture sintética foi preparada para outra consulta")
        if query.limit < 1:
            raise SyntheticSourceError("o limite da consulta deve ser maior que zero")
        if _normalize_text(query.keywords) != _normalize_text(self._expected_keywords):
            return ()
        return self._postings[: query.limit]


def _read_json(path: Path) -> object:
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SyntheticSourceError(
            f"não foi possível ler a fixture de JobPostings em {path}"
        ) from error
    try:
        value: object = json.loads(contents)
    except json.JSONDecodeError as error:
        raise SyntheticSourceError("a fixture de JobPostings não contém JSON válido") from error
    return value


def _decode_posting(value: object, *, index: int, source_name: str) -> JobPosting:
    if not isinstance(value, dict):
        raise SyntheticSourceError(f"JobPosting {index} deve ser um objeto JSON")

    return JobPosting(
        source_name=source_name,
        external_id=_posting_text(value.get("external_id"), "external_id", index),
        title=_posting_text(value.get("title"), "title", index),
        company=_optional_posting_text(value.get("company"), "company", index),
        location=_optional_posting_text(value.get("location"), "location", index),
        source_url=_posting_text(value.get("source_url"), "source_url", index),
        collected_at=_posting_datetime(value.get("collected_at"), "collected_at", index),
        summary=_optional_posting_text(value.get("summary"), "summary", index),
        source_updated_at=_optional_posting_datetime(
            value.get("source_updated_at"),
            "source_updated_at",
            index,
        ),
    )


def _metadata_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SyntheticSourceError(f"{field} deve ser um texto não vazio")
    return value.strip()


def _posting_text(value: object, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SyntheticSourceError(f"{field} do JobPosting {index} deve ser um texto não vazio")
    return value


def _optional_posting_text(value: object, field: str, index: int) -> str | None:
    if value is None:
        return None
    return _posting_text(value, field, index)


def _posting_datetime(value: object, field: str, index: int) -> datetime:
    text = _posting_text(value, field, index)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise SyntheticSourceError(
            f"{field} do JobPosting {index} deve estar em formato ISO 8601"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SyntheticSourceError(f"{field} do JobPosting {index} deve conter timezone")
    return parsed


def _optional_posting_datetime(
    value: object,
    field: str,
    index: int,
) -> datetime | None:
    if value is None:
        return None
    return _posting_datetime(value, field, index)


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()
