from dataclasses import dataclass

from buscador_de_vaga.domain import Evidence


@dataclass(frozen=True)
class RawResumeText:
    """Representação estruturada e imutável do conteúdo textual extraído de um currículo."""

    source_file: str
    text: str
    page_count: int = 1


@dataclass(frozen=True)
class ResumeSection:
    """Segmento de texto do currículo referente a uma categoria específica."""

    name: str
    content: str
    lines: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class DraftEvidence:
    """Evidência sugerida com seu grau de confiança e campo sugerido no perfil."""

    evidence: Evidence
    confidence: str  # "high", "medium", "low"
    suggested_field: str  # "skills", "target_categories", "entry_program", "seniority", "languages"


@dataclass(frozen=True)
class CandidateProfileDraft:
    """Representação intermediária e revisável do CandidateProfile gerada pelo ResumeParser."""

    source_file: str
    raw_text_summary: str
    suggested_evidences: tuple[DraftEvidence, ...]
    unrecognized_sections: tuple[str, ...] = ()

