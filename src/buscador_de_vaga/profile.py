"""Carregamento e serialização seguros do CandidateProfile mantido localmente."""

import json
from pathlib import Path

from buscador_de_vaga.domain import (
    CandidateProfile,
    EntryProgram,
    Evidence,
    EvidenceAssertion,
    JobCategory,
    Provenance,
    RequirementKind,
    RequirementSubject,
    Seniority,
    WorkplaceMode,
)


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

    evidences: list[Evidence] = []
    if "evidence" in raw:
        raw_evidences: object = raw.get("evidence")
        if not isinstance(raw_evidences, list):
            raise CandidateProfileError("evidence deve ser uma lista")

        for item in raw_evidences:
            if not isinstance(item, dict):
                raise CandidateProfileError("cada item de evidence deve ser um objeto JSON")
            ev_id = _required_text(item.get("id"), field="evidence.id")
            statement = _required_text(item.get("statement"), field="evidence.statement")

            raw_assertion = _required_text(item.get("assertion"), field="evidence.assertion")
            try:
                assertion = EvidenceAssertion(raw_assertion)
            except ValueError as error:
                raise CandidateProfileError(
                    f"EvidenceAssertion não reconhecida: {raw_assertion}"
                ) from error

            raw_subject = item.get("subject")
            if not isinstance(raw_subject, dict):
                raise CandidateProfileError("evidence.subject deve ser um objeto JSON")
            kind_str = _required_text(raw_subject.get("kind"), field="evidence.subject.kind")
            val_str = _required_text(raw_subject.get("value"), field="evidence.subject.value")

            try:
                kind = RequirementKind(kind_str)
            except ValueError as error:
                raise CandidateProfileError(
                    f"RequirementKind não reconhecida: {kind_str}"
                ) from error

            try:
                if kind is RequirementKind.JOB_CATEGORY:
                    subj = RequirementSubject.job_category(JobCategory(val_str))
                elif kind is RequirementKind.SKILL:
                    subj = RequirementSubject.skill(val_str)
                elif kind is RequirementKind.ENTRY_PROGRAM:
                    subj = RequirementSubject.entry_program(EntryProgram(val_str))
                elif kind is RequirementKind.SENIORITY:
                    subj = RequirementSubject.seniority(Seniority(val_str))
                elif kind is RequirementKind.LOCATION:
                    subj = RequirementSubject.location(val_str)
                elif kind is RequirementKind.WORKPLACE_MODE:
                    subj = RequirementSubject.workplace_mode(WorkplaceMode(val_str))
                else:
                    raise CandidateProfileError(f"RequirementKind não suportada: {kind_str}")
            except ValueError as error:
                raise CandidateProfileError(
                    f"Valor inválido '{val_str}' para RequirementKind '{kind_str}': {error}"
                ) from error

            raw_provenance = item.get("provenance")
            if not isinstance(raw_provenance, dict):
                raise CandidateProfileError("evidence.provenance deve ser um objeto JSON")
            origin = _required_text(
                raw_provenance.get("origin"), field="evidence.provenance.origin"
            )
            locator = _required_text(
                raw_provenance.get("locator"), field="evidence.provenance.locator"
            )
            provenance = Provenance(origin=origin, locator=locator)

            try:
                evidence_obj = Evidence(
                    id=ev_id,
                    subject=subj,
                    statement=statement,
                    assertion=assertion,
                    provenance=provenance,
                )
            except ValueError as error:
                raise CandidateProfileError(f"Erro ao construir Evidence: {error}") from error

            evidences.append(evidence_obj)

    return CandidateProfile(
        id=candidate_id,
        target_categories=tuple(categories),
        evidence=tuple(evidences),
    )


def serialize_candidate_profile(profile: CandidateProfile) -> dict[str, object]:
    """Converte um CandidateProfile em um dicionário serializável em JSON (schema_version=1)."""
    data: dict[str, object] = {
        "schema_version": 1,
        "id": profile.id,
        "target_categories": [cat.value for cat in profile.target_categories],
    }
    if profile.evidence:
        serialized_evidences: list[dict[str, object]] = []
        for ev in profile.evidence:
            serialized_evidences.append(
                {
                    "id": ev.id,
                    "subject": {
                        "kind": ev.subject.kind.value,
                        "value": ev.subject.resolved_value,
                    },
                    "statement": ev.statement,
                    "assertion": ev.assertion.value,
                    "provenance": {
                        "origin": ev.provenance.origin,
                        "locator": ev.provenance.locator,
                    },
                }
            )
        data["evidence"] = serialized_evidences
    return data


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
