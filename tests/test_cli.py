import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from buscador_de_vaga.cli import main


def test_cli_exibe_o_resultado_principal_de_uma_descoberta_sintetica(
    tmp_path: Path,
) -> None:
    profile_path = _write_profile(tmp_path)
    postings_path = _write_fixture(
        tmp_path,
        keywords="desenvolvedor de software",
        location="Rio de Janeiro, RJ",
        postings=[
            {
                "external_id": "job-001",
                "title": "  Desenvolvedor(a)   Python Júnior  ",
                "company": "  ACME   Tecnologia ",
                "location": " Rio de Janeiro, RJ ",
                "source_url": "  https://jobs.example.invalid/job-001  ",
                "collected_at": "2026-08-21T12:00:00Z",
                "source_updated_at": "2026-08-20T18:30:00-03:00",
            }
        ],
    )

    completed = _run_cli(
        profile_path,
        postings_path,
        location="Rio de Janeiro, RJ",
    )

    assert completed.returncode == 0
    assert "1 oportunidade encontrada" in completed.stdout
    assert "Desenvolvedor(a) Python Júnior" in completed.stdout
    assert "ACME Tecnologia" in completed.stdout
    assert "Rio de Janeiro, RJ" in completed.stdout
    assert "https://jobs.example.invalid/job-001" in completed.stdout
    assert completed.stderr == ""


def test_cli_trata_resultado_vazio_como_sucesso(tmp_path: Path) -> None:
    completed = _run_cli(
        _write_profile(tmp_path),
        _write_fixture(
            tmp_path,
            keywords="desenvolvedor de software",
            location="Brasil",
        ),
        location="Brasil",
    )

    assert completed.returncode == 0
    assert completed.stdout == "Nenhuma oportunidade encontrada.\n"
    assert completed.stderr == ""


def test_cli_retorna_erro_acionavel_quando_o_perfil_nao_pode_ser_lido(
    tmp_path: Path,
) -> None:
    completed = _run_cli(
        tmp_path / "candidate-profile-ausente.json",
        tmp_path / "job-postings.json",
        location="Brasil",
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "não foi possível ler CandidateProfile" in completed.stderr
    assert "Ação: verifique o caminho e o formato do CandidateProfile." in completed.stderr


def test_cli_retorna_erro_acionavel_para_categoria_fora_do_perfil(tmp_path: Path) -> None:
    completed = _run_cli(
        _write_profile(tmp_path),
        _write_fixture(
            tmp_path,
            keywords="analista de dados",
            location="Brasil",
        ),
        category="data",
        location="Brasil",
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "JobCategory data não pertence ao CandidateProfile" in completed.stderr
    assert "Ação: escolha uma JobCategory declarada no perfil." in completed.stderr
    assert "Traceback" not in completed.stderr


def test_cli_rejeita_fixture_preparada_para_outra_consulta(tmp_path: Path) -> None:
    completed = _run_cli(
        _write_profile(tmp_path),
        _write_fixture(
            tmp_path,
            keywords="desenvolvedor de software",
            location="Rio de Janeiro, RJ",
        ),
        location="São Paulo, SP",
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "fixture sintética foi preparada para outra consulta" in completed.stderr
    assert "Ação: use uma fixture correspondente aos argumentos da busca." in completed.stderr


def test_cli_rejeita_schema_version_booleano_no_candidate_profile(tmp_path: Path) -> None:
    completed = _run_cli(
        _write_profile(tmp_path, schema_version=True),
        tmp_path / "job-postings.json",
        location="Brasil",
    )

    assert completed.returncode == 2
    assert "schema_version deve ser o inteiro 1" in completed.stderr
    assert "Ação: verifique o caminho e o formato do CandidateProfile." in completed.stderr


def test_cli_explica_como_configurar_jooble_api_key(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "buscador_de_vaga.cli",
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--jooble",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            name: value for name, value in os.environ.items() if name.casefold() != "jooble_api_key"
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Erro: JOOBLE_API_KEY não está configurada.\n"
        "Ação: defina JOOBLE_API_KEY no ambiente antes da busca live.\n"
    )
    assert "Traceback" not in completed.stderr


def test_cli_exibe_resultado_do_jooble_com_mock_transport(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalCount": 1,
                "jobs": [
                    {
                        "id": 9000003,
                        "title": "Desenvolvedor(a) Python Júnior",
                        "company": "Empresa Exemplo",
                        "location": "Brasil - remoto",
                        "link": "https://example.invalid/jobs/9000003",
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        exit_code = main(
            [
                "--profile",
                str(_write_profile(tmp_path)),
                "--category",
                "software-development",
                "--location",
                "Brasil",
                "--jooble",
            ],
            http_client=client,
            environ={"JOOBLE_API_KEY": "jooble-test-key"},
        )

    output = capsys.readouterr()
    assert exit_code == 0
    assert "1 oportunidade encontrada" in output.out
    assert "Desenvolvedor(a) Python Júnior" in output.out
    assert "Empresa Exemplo" in output.out
    assert "Brasil - remoto" in output.out
    assert "https://example.invalid/jobs/9000003" in output.out
    assert output.err == ""


def test_cli_apresenta_falha_do_jooble_sem_expor_segredos(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="RAW_PAYLOAD_SENTINEL")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        exit_code = main(
            [
                "--profile",
                str(_write_profile(tmp_path)),
                "--category",
                "software-development",
                "--location",
                "Brasil",
                "--jooble",
            ],
            http_client=client,
            environ={"JOOBLE_API_KEY": "jooble-test-key"},
        )

    output = capsys.readouterr()
    assert exit_code == 1
    assert output.out == ""
    assert "A credencial do Jooble foi rejeitada." in output.err
    assert "Ação:" in output.err
    assert "jooble-test-key" not in output.err
    assert "RAW_PAYLOAD_SENTINEL" not in output.err
    assert "Traceback" not in output.err


def _write_profile(
    tmp_path: Path,
    *,
    schema_version: object = 1,
) -> Path:
    return _write_json(
        tmp_path / "candidate-profile.json",
        {
            "schema_version": schema_version,
            "id": "candidate-example",
            "target_categories": ["software-development"],
        },
    )


def _write_fixture(
    tmp_path: Path,
    *,
    keywords: str,
    location: str,
    postings: list[dict[str, object]] | None = None,
) -> Path:
    return _write_json(
        tmp_path / "job-postings.json",
        {
            "schema_version": 1,
            "source_name": "synthetic",
            "query": {
                "keywords": keywords,
                "location": location,
            },
            "postings": postings or [],
        },
    )


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run_cli(
    profile_path: Path,
    postings_path: Path,
    *,
    location: str,
    category: str = "software-development",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "buscador_de_vaga.cli",
            "--profile",
            str(profile_path),
            "--category",
            category,
            "--location",
            location,
            "--postings-file",
            str(postings_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
