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


def test_cli_exibe_uma_unica_opportunity_para_postings_consolidados(
    tmp_path: Path,
) -> None:
    profile_path = _write_profile(tmp_path)
    postings_path = _write_fixture(
        tmp_path,
        keywords="desenvolvedor de software",
        location="Brasil",
        postings=[
            {
                "external_id": "job-001",
                "title": "Desenvolvedor Python",
                "company": "ACME Tecnologia",
                "location": "Brasil",
                "source_url": "https://jobs.example.invalid/job-001",
                "collected_at": "2026-08-21T12:00:00Z",
            },
            {
                "external_id": "job-001",
                "title": "Backend Engineer",
                "company": "ACME Tecnologia",
                "location": "Brasil",
                "source_url": "https://mirror.example.invalid/job-001",
                "collected_at": "2026-08-21T13:00:00Z",
            },
        ],
    )

    completed = _run_cli(profile_path, postings_path, location="Brasil")

    assert completed.returncode == 0
    assert "1 oportunidade encontrada" in completed.stdout
    assert completed.stdout.count("\n1. ") == 1
    assert completed.stdout.count("   URL: ") == 1
    assert "Desenvolvedor Python" in completed.stdout
    assert "Backend Engineer" not in completed.stdout
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


def test_cli_exibe_detalhes_completos_do_match_assessment(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    profile_path = _write_profile(tmp_path)
    postings_path = _write_fixture(
        tmp_path,
        keywords="desenvolvedor de software",
        location="Rio de Janeiro, RJ",
        postings=[
            {
                "external_id": "job-001",
                "title": "Desenvolvedor Python Júnior",
                "company": "ACME Tecnologia",
                "location": "Rio de Janeiro, RJ - remoto",
                "source_url": "https://jobs.example.invalid/job-001",
                "collected_at": "2026-08-21T12:00:00Z",
                "summary": "Requisitos obrigatórios: conhecimento em Python.",
            }
        ],
    )

    exit_code = main(
        [
            "--profile",
            str(profile_path),
            "--category",
            "software-development",
            "--location",
            "Rio de Janeiro, RJ",
            "--postings-file",
            str(postings_path),
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert "1 oportunidade encontrada." in output.out
    assert "Desenvolvedor Python Júnior" in output.out
    assert "Empresa: ACME Tecnologia" in output.out
    assert "Local: Rio de Janeiro, RJ - remoto" in output.out
    assert "URL: https://jobs.example.invalid/job-001" in output.out
    assert "Elegibilidade: " in output.out
    assert "FitScore: " in output.out
    assert "Breakdown:" in output.out
    assert "job-category:" in output.out
    assert "skills:" in output.out
    assert "entry-program-seniority:" in output.out
    assert "location-workplace-mode:" in output.out
    assert "Pontos fortes:" in output.out
    assert "Skill Gaps:" in output.out
    assert "Requisitos não informados:" in output.out
    assert "Possíveis impeditivos:" in output.out


def test_cli_exibe_resultado_da_adzuna_com_mock_transport(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.adzuna.com" in str(request.url)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "adz-101",
                        "title": "Desenvolvedor(a) Python Júnior - Adzuna",
                        "company": {"display_name": "Empresa Adzuna"},
                        "location": {"display_name": "Brasil"},
                        "redirect_url": "https://adzuna.example.invalid/jobs/adz-101",
                        "created": "2026-08-26T10:00:00Z",
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
                "--adzuna",
            ],
            http_client=client,
            environ={"ADZUNA_APP_ID": "test-app-id", "ADZUNA_APP_KEY": "test-app-key"},
        )

    output = capsys.readouterr()
    assert exit_code == 0
    assert "1 oportunidade encontrada." in output.out
    assert "Desenvolvedor(a) Python Júnior - Adzuna" in output.out
    assert "Empresa Adzuna" in output.out
    assert "https://adzuna.example.invalid/jobs/adz-101" in output.out
    assert output.err == ""


def test_cli_exibe_resultado_de_jooble_e_adzuna_em_multi_source_consultando_na_ordem(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests_made: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "br.jooble.org" in url_str:
            requests_made.append("jooble")
            return httpx.Response(
                200,
                json={
                    "totalCount": 1,
                    "jobs": [
                        {
                            "id": 9000001,
                            "title": "Dev Python Jooble",
                            "company": "Empresa Jooble",
                            "location": "Brasil",
                            "link": "https://jooble.example.invalid/jobs/9000001",
                        }
                    ],
                },
            )
        if "api.adzuna.com" in url_str:
            requests_made.append("adzuna")
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "adz-9000002",
                            "title": "Dev Python Adzuna",
                            "company": {"display_name": "Empresa Adzuna"},
                            "location": {"display_name": "Brasil"},
                            "redirect_url": "https://adzuna.example.invalid/jobs/adz-9000002",
                        }
                    ],
                },
            )
        return httpx.Response(404)

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
                "--adzuna",
            ],
            http_client=client,
            environ={
                "JOOBLE_API_KEY": "jooble-key",
                "ADZUNA_APP_ID": "adzuna-id",
                "ADZUNA_APP_KEY": "adzuna-key",
            },
        )

    output = capsys.readouterr()
    assert exit_code == 0
    assert requests_made == ["jooble", "adzuna"] * 3
    assert "2 oportunidades encontradas." in output.out
    assert "Dev Python Jooble" in output.out
    assert "Dev Python Adzuna" in output.out
    assert output.err == ""


def test_cli_explica_como_configurar_adzuna_app_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--adzuna",
        ],
        environ={"ADZUNA_APP_KEY": "some-key"},
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "Erro: ADZUNA_APP_ID não está configurada." in output.err
    assert "Ação: defina ADZUNA_APP_ID no ambiente antes da busca live." in output.err


def test_cli_explica_como_configurar_adzuna_app_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--adzuna",
        ],
        environ={"ADZUNA_APP_ID": "some-id"},
    )

    output = capsys.readouterr()
    assert exit_code == 2
    assert "Erro: ADZUNA_APP_KEY não está configurada." in output.err
    assert "Ação: defina ADZUNA_APP_KEY no ambiente antes da busca live." in output.err


def test_cli_nao_faz_requisicao_de_rede_se_faltar_credencial_em_multi_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"jobs": [], "results": []})

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
                "--adzuna",
            ],
            http_client=client,
            environ={"JOOBLE_API_KEY": "jooble-key", "ADZUNA_APP_ID": "adzuna-id"},
        )

    output = capsys.readouterr()
    assert exit_code == 2
    assert len(calls) == 0
    assert "Erro: ADZUNA_APP_KEY não está configurada." in output.err


def test_cli_nao_expoe_credenciais_da_adzuna_ou_jooble_em_erros(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_id = "SECRET_ADZUNA_ID_999"
    secret_key = "SECRET_ADZUNA_KEY_999"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"Unauthorized for {secret_id}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        exit_code = main(
            [
                "--profile",
                str(_write_profile(tmp_path)),
                "--category",
                "software-development",
                "--location",
                "Brasil",
                "--adzuna",
            ],
            http_client=client,
            environ={"ADZUNA_APP_ID": secret_id, "ADZUNA_APP_KEY": secret_key},
        )

    output = capsys.readouterr()
    assert exit_code == 1
    assert secret_id not in output.out and secret_id not in output.err
    assert secret_key not in output.out and secret_key not in output.err


def test_cli_rejeita_combinacao_de_postings_file_com_jooble(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postings_path = _write_fixture(
        tmp_path, keywords="desenvolvedor de software", location="Brasil"
    )
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_path),
            "--jooble",
        ],
        environ={"JOOBLE_API_KEY": "test-key"},
    )
    output = capsys.readouterr()
    assert exit_code == 2
    assert "--postings-file não pode ser combinado com fontes live" in output.err


def test_cli_rejeita_combinacao_de_postings_file_com_adzuna(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postings_path = _write_fixture(
        tmp_path, keywords="desenvolvedor de software", location="Brasil"
    )
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_path),
            "--adzuna",
        ],
        environ={"ADZUNA_APP_ID": "id", "ADZUNA_APP_KEY": "key"},
    )
    output = capsys.readouterr()
    assert exit_code == 2
    assert "--postings-file não pode ser combinado com fontes live" in output.err


def test_cli_rejeita_combinacao_de_postings_file_com_jooble_e_adzuna(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postings_path = _write_fixture(
        tmp_path, keywords="desenvolvedor de software", location="Brasil"
    )
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
            "--postings-file",
            str(postings_path),
            "--jooble",
            "--adzuna",
        ],
        environ={
            "JOOBLE_API_KEY": "jkey",
            "ADZUNA_APP_ID": "id",
            "ADZUNA_APP_KEY": "key",
        },
    )
    output = capsys.readouterr()
    assert exit_code == 2
    assert "--postings-file não pode ser combinado com fontes live" in output.err


def test_cli_rejeita_execucao_sem_nenhuma_fonte_selecionada(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--profile",
            str(_write_profile(tmp_path)),
            "--category",
            "software-development",
            "--location",
            "Brasil",
        ]
    )
    output = capsys.readouterr()
    assert exit_code == 2
    assert "Erro: Nenhuma fonte de vagas foi selecionada." in output.err
    assert "Ação: informe --jooble, --adzuna ou --postings-file <caminho>" in output.err


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
