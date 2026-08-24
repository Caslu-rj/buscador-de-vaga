"""Testes unitários sintéticos para o DeterministicResumeParser (TDD)."""

from buscador_de_vaga.domain import (
    EntryProgram,
    EvidenceAssertion,
    RequirementKind,
    Seniority,
)
from buscador_de_vaga.resume.models import (
    CandidateProfileDraft,
    RawResumeText,
)
from buscador_de_vaga.resume.parser import DeterministicResumeParser


def test_resume_parser_segmentation_portuguese() -> None:
    """Verifica a segmentação de seções em português."""
    text = """
# Experiência Profissional
Desenvolvedor Python na Empresa X.

# Formação Acadêmica
Bacharelado em Ciência da Computação.

# Habilidades
Python, SQL, Docker.

# Idiomas
Inglês intermediário.
"""
    raw = RawResumeText(source_file="curriculo_pt.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    assert isinstance(draft, CandidateProfileDraft)
    assert draft.source_file == "curriculo_pt.pdf"
    assert len(draft.suggested_evidences) > 0

    # Deve ter extraído evidências das seções correspondentes
    skills = [
        e.evidence.subject.resolved_value
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
    ]
    assert "python" in skills
    assert "sql" in skills
    assert "docker" in skills


def test_resume_parser_segmentation_english() -> None:
    """Verifica a segmentação de seções em inglês."""
    text = """
## Work Experience
Backend Software Developer at Tech Co.

## Education
B.S. in Computer Science.

## Technical Skills
TypeScript, React, AWS.

## Languages
English fluent.
"""
    raw = RawResumeText(source_file="resume_en.docx", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    skills = [
        e.evidence.subject.resolved_value
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
    ]
    assert "typescript" in skills
    assert "react" in skills
    assert "aws" in skills


def test_resume_parser_explicit_skills_high_confidence() -> None:
    """Skills na seção de Habilidades devem ter alta confiança."""
    text = """
# Habilidades Técnicas
Python, FastApi, PostgreSQL, Linux, Git.
"""
    raw = RawResumeText(source_file="skills.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    python_ev = next(
        e
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
        and e.evidence.subject.resolved_value == "python"
    )
    assert python_ev.confidence == "high"
    assert python_ev.suggested_field == "skills"
    assert python_ev.evidence.assertion == EvidenceAssertion.SUPPORTS


def test_resume_parser_skills_in_experience_medium_confidence() -> None:
    """Skills mencionadas na experiência/projetos devem ter confiança média."""
    text = """
# Experiência Profissional
Desenvolvi APIs com Flask e Django para integração com Azure.
"""
    raw = RawResumeText(source_file="exp.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    flask_ev = next(
        e
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
        and e.evidence.subject.resolved_value == "flask"
    )
    assert flask_ev.confidence == "medium"
    assert flask_ev.suggested_field == "skills"


def test_resume_parser_languages() -> None:
    """Detecta idiomas explicitamente indicados com nível."""
    text = """
# Idiomas
Inglês intermediário
English B2
Espanhol avançado
"""
    raw = RawResumeText(source_file="languages.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    lang_evidences = [
        e for e in draft.suggested_evidences
        if e.suggested_field == "languages"
    ]
    assert len(lang_evidences) >= 2
    statements = [e.evidence.statement for e in lang_evidences]
    assert any("inglês" in s.lower() or "english" in s.lower() for s in statements)


def test_resume_parser_explicit_seniority_and_entry_program() -> None:
    """Detecta nível de senioridade e programas de entrada (estágio, júnior)."""
    text = """
# Experiência Profissional
Estagiário de desenvolvimento de software na Empresa Y.
Desenvolvedor Júnior na Empresa Z.
"""
    raw = RawResumeText(source_file="seniority.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    entry_ev = [
        e for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.ENTRY_PROGRAM
    ]
    assert len(entry_ev) > 0
    assert entry_ev[0].evidence.subject.resolved_value == EntryProgram.INTERNSHIP.value

    seniority_ev = [
        e for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SENIORITY
    ]
    assert len(seniority_ev) > 0
    assert seniority_ev[0].evidence.subject.resolved_value == Seniority.JUNIOR.value


def test_resume_parser_absence_remains_absent_never_contradicts() -> None:
    """Ausência de skill (ex: Docker) não deve gerar evidencia CONTRADICTS."""
    text = """
# Habilidades
Python, SQL.
"""
    raw = RawResumeText(source_file="no_docker.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    # Nenhuma evidência de Docker deve ser gerada
    docker_evidences = [
        e
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
        and e.evidence.subject.resolved_value == "docker"
    ]
    assert len(docker_evidences) == 0

    # Nenhuma evidência no draft pode ser CONTRADICTS por ausência
    assert all(
        e.evidence.assertion == EvidenceAssertion.SUPPORTS
        for e in draft.suggested_evidences
    )


def test_resume_parser_provenance() -> None:
    """Verifica se origin e locator são gerados corretamente."""
    text = """
# Habilidades
Python
"""
    raw = RawResumeText(source_file="curriculo.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    python_ev = next(
        e for e in draft.suggested_evidences
        if e.evidence.subject.resolved_value == "python"
    )
    prov = python_ev.evidence.provenance
    assert prov.origin == "resume:curriculo.pdf"
    assert "section:habilidades" in prov.locator
    assert "#line:" in prov.locator


def test_resume_parser_deduplication() -> None:
    """Termos repetidos na mesma seção não geram evidências duplicadas."""
    text = """
# Habilidades
Python, Python, python.
Desenvolvimento em Python.
"""
    raw = RawResumeText(source_file="dups.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    python_evidences = [
        e
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
        and e.evidence.subject.resolved_value == "python"
    ]
    assert len(python_evidences) == 1


def test_resume_parser_partial_resume() -> None:
    """Parser funciona com currículos incompletos sem todas as seções."""
    text = "Apenas uma linha com experiência em Java e SQL."
    raw = RawResumeText(source_file="partial.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    skills = [
        e.evidence.subject.resolved_value
        for e in draft.suggested_evidences
        if e.evidence.subject.kind == RequirementKind.SKILL
    ]
    assert "java" in skills
    assert "sql" in skills


def test_resume_parser_no_recognized_evidence() -> None:
    """Currículo sem evidências reconhecidas produz rascunho sem erros."""
    text = "Este é um texto genérico sem nenhuma habilidade técnica ou seção de interesse."
    raw = RawResumeText(source_file="empty_evidence.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    assert isinstance(draft, CandidateProfileDraft)
    assert len(draft.suggested_evidences) == 0


def test_resume_parser_unrecognized_sections() -> None:
    """Seções com títulos não reconhecidos entram em unrecognized_sections."""
    text = """
# Habilidades
Python

# Outros Conhecimentos Diversos
Alguma informação genérica.
"""
    raw = RawResumeText(source_file="unrec.pdf", text=text.strip())
    parser = DeterministicResumeParser()
    draft = parser.parse(raw)

    assert "Outros Conhecimentos Diversos" in draft.unrecognized_sections
