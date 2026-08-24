"""Testes de integração para o comando CLI de importação de currículo (TDD)."""

from pathlib import Path

import docx
import pytest
from pypdf import PdfWriter

from buscador_de_vaga.cli import main
from buscador_de_vaga.profile import load_candidate_profile


def create_synthetic_pdf(path: Path, text: str) -> Path:
    """Gera um PDF sintético contendo o texto especificado."""
    pdf_content = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>\n"
        "endobj\n"
        "4 0 obj\n"
        f"<< /Length {len(f'BT /F1 12 Tf 100 700 Td ({text}) Tj ET')} >>\n"
        "stream\n"
        f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET\n"
        "endstream\n"
        "endobj\n"
        "5 0 obj\n"
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        "endobj\n"
        "xref\n"
        "0 6\n"
        "0000000000 65535 f \n"
        "0000000009 00000 n \n"
        "0000000058 00000 n \n"
        "0000000115 00000 n \n"
        "0000000246 00000 n \n"
        "0000000360 00000 n \n"
        "trailer\n"
        "<< /Size 6 /Root 1 0 R >>\n"
        "startxref\n"
        "440\n"
        "%%EOF\n"
    )
    path.write_bytes(pdf_content.encode("latin1"))
    return path


def create_blank_pdf(path: Path) -> Path:
    """Gera um PDF válido sem camada de texto (escaneado/em branco)."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as f:
        writer.write(f)
    return path


def create_synthetic_docx(path: Path, lines: list[str]) -> Path:
    """Gera um DOCX sintético contendo as linhas de texto."""
    doc = docx.Document()
    for line in lines:
        doc.add_paragraph(line)
    doc.save(str(path))
    return path


def test_cli_importar_curriculo_review_pdf(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython, SQL, Docker.",
    )

    exit_code = main(["importar-curriculo", "--file", str(pdf_path), "--review"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "CandidateProfileDraft" in captured.out
    assert "curriculo.pdf" in captured.out
    assert "Python" in captured.out or "python" in captured.out
    assert captured.err == ""


def test_cli_importar_curriculo_review_docx(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docx_path = create_synthetic_docx(
        tmp_path / "curriculo.docx",
        ["# Technical Skills", "TypeScript, React, AWS."],
    )

    exit_code = main(["importar-curriculo", "--file", str(docx_path), "--review"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "CandidateProfileDraft" in captured.out
    assert "curriculo.docx" in captured.out
    assert captured.err == ""


def test_cli_importar_curriculo_review_nao_cria_arquivos(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython, Git.",
    )
    initial_files = set(tmp_path.iterdir())

    exit_code = main(["importar-curriculo", "--file", str(pdf_path), "--review"])

    assert exit_code == 0
    assert set(tmp_path.iterdir()) == initial_files


def test_cli_importar_curriculo_consolidacao_cria_candidate_profile_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Experiencia Profissional\nDesenvolvedor Python na Empresa A.",
    )
    output_json = tmp_path / "candidate-profile.json"

    exit_code = main(
        [
            "importar-curriculo",
            "--file",
            str(pdf_path),
            "--output",
            str(output_json),
        ]
    )

    assert exit_code == 0
    assert output_json.is_file()

    profile = load_candidate_profile(output_json)
    assert profile.id is not None
    assert len(profile.target_categories) > 0


def test_cli_importar_curriculo_json_produzido_e_carregavel_pela_busca(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Experiencia Profissional\nDesenvolvedor Python na Empresa A.",
    )
    output_json = tmp_path / "candidate-profile.json"

    # 1. Importa o currículo e gera candidate-profile.json
    exit_code_import = main(
        [
            "importar-curriculo",
            "--file",
            str(pdf_path),
            "--output",
            str(output_json),
        ]
    )
    assert exit_code_import == 0

    # 2. Cria fixture sintética de vagas
    postings_json = tmp_path / "postings.json"
    postings_json.write_text(
        """{
        "schema_version": 1,
        "source_name": "synthetic",
        "query": {
            "keywords": "desenvolvedor de software",
            "location": "Brasil"
        },
        "postings": [
            {
                "external_id": "job-001",
                "title": "Desenvolvedor Python",
                "company": "Tech Corp",
                "location": "Brasil",
                "source_url": "https://example.invalid/job-001",
                "collected_at": "2026-08-21T12:00:00Z"
            }
        ]
    }""",
        encoding="utf-8",
    )

    # 3. Executa a busca utilizando o CandidateProfile gerado
    exit_code_search = main(
        [
            "--profile",
            str(output_json),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_json),
        ]
    )
    assert exit_code_search == 0
    captured = capsys.readouterr()
    assert "1 oportunidade encontrada" in captured.out
    assert "Desenvolvedor Python" in captured.out


def test_cli_importar_curriculo_recusa_output_existente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython.",
    )
    output_json = tmp_path / "existing.json"
    output_json.write_text("{}", encoding="utf-8")

    exit_code = main(
        [
            "importar-curriculo",
            "--file",
            str(pdf_path),
            "--output",
            str(output_json),
        ]
    )

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "já existe" in captured.err
    assert "--force" in captured.err


def test_cli_importar_curriculo_force_permite_sobrescrever(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython.",
    )
    output_json = tmp_path / "existing.json"
    output_json.write_text("{}", encoding="utf-8")

    exit_code = main(
        [
            "importar-curriculo",
            "--file",
            str(pdf_path),
            "--output",
            str(output_json),
            "--force",
        ]
    )

    assert exit_code == 0
    profile = load_candidate_profile(output_json)
    assert profile.id is not None


def test_cli_importar_curriculo_pdf_sem_texto_erro_acionavel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blank_pdf = create_blank_pdf(tmp_path / "blank.pdf")

    exit_code = main(["importar-curriculo", "--file", str(blank_pdf), "--review"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "OCR" in captured.err or "camada de texto" in captured.err
    assert "Ação:" in captured.err


def test_cli_importar_curriculo_formato_invalido_erro_acionavel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    txt_path = tmp_path / "curriculo.txt"
    txt_path.write_text("Conteúdo de texto puro.", encoding="utf-8")

    exit_code = main(["importar-curriculo", "--file", str(txt_path), "--review"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "não suportado" in captured.err
    assert "Ação:" in captured.err


def test_cli_importar_curriculo_documento_vazio_erro_acionavel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")

    exit_code = main(["importar-curriculo", "--file", str(empty_pdf), "--review"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "vazio" in captured.err
    assert "Ação:" in captured.err


def test_cli_importar_curriculo_ausencia_de_output_e_review_erro_acionavel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython.",
    )

    exit_code = main(["importar-curriculo", "--file", str(pdf_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "--output" in captured.err or "--review" in captured.err
    assert "Ação:" in captured.err


def test_cli_importar_curriculo_sem_chamadas_de_rede(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Garante que nenhuma chamada de rede pode ser efetuada
    def raise_on_network(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Chamada de rede efetuada indevidamente durante a importação.")

    monkeypatch.setattr("httpx.Client", raise_on_network)

    pdf_path = create_synthetic_pdf(
        tmp_path / "curriculo.pdf",
        "# Habilidades\nPython.",
    )
    output_json = tmp_path / "out.json"

    exit_code = main(
        [
            "importar-curriculo",
            "--file",
            str(pdf_path),
            "--output",
            str(output_json),
        ]
    )

    assert exit_code == 0
    assert output_json.is_file()
