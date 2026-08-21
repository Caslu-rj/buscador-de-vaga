import json
import subprocess
import sys
from pathlib import Path


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
