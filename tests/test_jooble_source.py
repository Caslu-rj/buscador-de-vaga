import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from buscador_de_vaga.discovery import JobSourceError, JobSourceFailureKind
from buscador_de_vaga.domain import JobPosting, JobSourceQuery
from buscador_de_vaga.sources.jooble import JoobleJobSource

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "jooble"
API_KEY = "jooble-test-key"
COLLECTED_AT = datetime(2026, 8, 21, 15, 0, tzinfo=UTC)


def test_jooble_search_mapeia_resposta_documentada_para_job_posting() -> None:
    request_received = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_received
        assert request_received is False, "a busca deve consultar somente uma página"
        request_received = True
        assert request.method == "POST"
        assert request.url == httpx.URL(f"https://jooble.org/api/{API_KEY}")
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept"] == "application/json"
        assert json.loads(request.content) == {
            "keywords": "desenvolvedor de software",
            "location": "Brasil",
            "page": 1,
            "ResultOnPage": 10,
        }
        return httpx.Response(200, json=_read_fixture("search-success.json"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = JoobleJobSource(
            api_key=API_KEY,
            client=client,
            clock=lambda: COLLECTED_AT,
        )

        postings = source.search(
            JobSourceQuery(
                keywords="desenvolvedor de software",
                location="Brasil",
                limit=10,
            )
        )

    assert request_received is True
    assert postings == (
        JobPosting(
            source_name="jooble-br",
            external_id="9000001",
            title="Pessoa Desenvolvedora Júnior",
            company="Empresa Exemplo",
            location="Brasil - remoto",
            source_url="https://example.invalid/jobs/9000001",
            collected_at=COLLECTED_AT,
            summary="Fixture sintética para validar a integração.",
            source_updated_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        ),
    )


def test_jooble_search_preserva_campos_ausentes_como_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalCount": 1,
                "jobs": [
                    {
                        "id": 9000002,
                        "title": "Estágio em QA",
                        "link": "https://example.invalid/jobs/9000002",
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        postings = JoobleJobSource(
            api_key=API_KEY,
            client=client,
            clock=lambda: COLLECTED_AT,
        ).search(JobSourceQuery(keywords="QA", location="Brasil", limit=5))

    assert postings == (
        JobPosting(
            source_name="jooble-br",
            external_id="9000002",
            title="Estágio em QA",
            company=None,
            location=None,
            source_url="https://example.invalid/jobs/9000002",
            collected_at=COLLECTED_AT,
            summary=None,
            source_updated_at=None,
        ),
    )


def test_jooble_search_traduz_403_para_falha_de_autenticacao_segura() -> None:
    raw_payload_sentinel = "RAW_PAYLOAD_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.AUTHENTICATION
    assert str(error) == "A credencial do Jooble foi rejeitada."
    assert error.action == "Solicite ou configure uma chave brasileira válida do Jooble."
    assert error.retryable is False
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_jooble_search_traduz_429_para_limite_sem_retry_automatico() -> None:
    raw_payload_sentinel = "RAW_PAYLOAD_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.RATE_LIMIT
    assert str(error) == "O Jooble limitou a busca."
    assert error.action == "Verifique a quota da chave e aguarde antes de tentar novamente."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_jooble_search_traduz_timeout_para_falha_temporaria_segura() -> None:
    timeout_sentinel = "TIMEOUT_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(timeout_sentinel, request=request)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.TIMEOUT
    assert str(error) == "O Jooble não respondeu dentro do tempo limite."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, timeout_sentinel)


def test_jooble_search_sanitiza_falha_de_transporte() -> None:
    transport_sentinel = "TRANSPORT_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(transport_sentinel, request=request)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.UNAVAILABLE
    assert str(error) == "Não foi possível conectar ao Jooble."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, transport_sentinel)


def test_jooble_search_traduz_5xx_para_indisponibilidade_segura() -> None:
    raw_payload_sentinel = "RAW_PAYLOAD_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.UNAVAILABLE
    assert str(error) == "O Jooble está temporariamente indisponível."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_jooble_search_traduz_outro_status_http_para_falha_de_contrato() -> None:
    raw_payload_sentinel = "RAW_PAYLOAD_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"totalCount": 0, "jobs": [], "detail": raw_payload_sentinel},
        )

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.CONTRACT
    assert str(error) == "A resposta do Jooble não corresponde ao formato esperado."
    assert error.retryable is False
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_jooble_search_rejeita_payload_incompativel_sem_expor_conteudo() -> None:
    raw_payload_sentinel = "RAW_PAYLOAD_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.CONTRACT
    assert str(error) == "A resposta do Jooble não corresponde ao formato esperado."
    assert error.action == (
        "Verifique se a integração está atualizada e reporte uma possível mudança no contrato."
    )
    assert error.retryable is False
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_jooble_search_retorna_tupla_vazia_quando_nao_ha_vagas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"totalCount": 0, "jobs": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        postings = JoobleJobSource(api_key=API_KEY, client=client).search(
            JobSourceQuery(keywords="Python", location="Brasil", limit=1)
        )

    assert postings == ()


def _read_fixture(name: str) -> object:
    return json.loads((FIXTURES_DIRECTORY / name).read_text(encoding="utf-8"))


def _capture_search_failure(
    handler: Callable[[httpx.Request], httpx.Response],
) -> JobSourceError:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = JoobleJobSource(api_key=API_KEY, client=client)

        with pytest.raises(JobSourceError) as captured:
            source.search(JobSourceQuery(keywords="Python", location="Brasil", limit=1))

    return captured.value


def _assert_failure_is_sanitized(error: JobSourceError, unsafe_marker: str) -> None:
    safe_surface = f"{error!r} {error.action}"
    assert API_KEY not in safe_surface
    assert unsafe_marker not in safe_surface
    assert error.__context__ is None
