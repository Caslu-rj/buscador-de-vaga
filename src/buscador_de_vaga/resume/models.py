from dataclasses import dataclass


@dataclass(frozen=True)
class RawResumeText:
    """Representação estruturada e imutável do conteúdo textual extraído de um currículo."""

    source_file: str
    text: str
    page_count: int = 1
