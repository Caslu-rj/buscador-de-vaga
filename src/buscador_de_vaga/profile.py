"""Carregamento seguro do CandidateProfile mantido localmente."""

import json
from pathlib import Path

from buscador_de_vaga.domain import CandidateProfile, JobCategory


class CandidateProfileError(ValueError):
    """Indica que o arquivo de CandidateProfile não pode ser usado."""


def load_candidate_profile(path: Path) -> CandidateProfile:
    """Lê e valida a versão inicial do CandidateProfile em JSON."""
    raw = _read_json(path, document_name="CandidateProfile")
    if not isinstance(raw, dict):
        raise CandidateProfileError("o CandidateProfile deve ser um objeto JSON")

    schema_version: object = raw.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise CandidateProfileError("schema_version deve ser o inteiro 1")
    if schema_version != 1:
        raise CandidateProfileError("schema_version deve ser 1")

    candidate_id = _required_text(raw.get("id"), field="id")
    raw_categories: object = raw.get("target_categories")
    if not isinstance(raw_categories, list) or not raw_categories:
        raise CandidateProfileError("target_categories deve ser uma lista não vazia")

    categories: list[JobCategory] = []
    for value in raw_categories:
        category_value = _required_text(value, field="target_categories")
        try:
            categories.append(JobCategory(category_value))
        except ValueError as error:
            raise CandidateProfileError(f"JobCategory não reconhecida: {category_value}") from error

    return CandidateProfile(id=candidate_id, target_categories=tuple(categories))


def _read_json(path: Path, *, document_name: str) -> object:
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CandidateProfileError(f"não foi possível ler {document_name} em {path}") from error

    try:
        value: object = json.loads(contents)
    except json.JSONDecodeError as error:
        raise CandidateProfileError(f"{document_name} não contém JSON válido") from error
    return value


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateProfileError(f"{field} deve ser um texto não vazio")
    return value.strip()
