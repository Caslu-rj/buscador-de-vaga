from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from buscador_de_vaga.discovery import JobSourceError, JobSourceFailureKind
from buscador_de_vaga.domain import JobPosting, JobSourceQuery
from buscador_de_vaga.sources.adzuna import AdzunaJobSource

APP_ID = "test-app-id"
APP_KEY = "test-app-key"
COLLECTED_AT = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)


def test_adzuna_configuration_error_when_credentials_empty() -> None:
    with httpx.Client() as client:
        with pytest.raises(JobSourceError) as captured1:
            AdzunaJobSource(app_id="", app_key=APP_KEY, client=client)
        assert captured1.value.kind is JobSourceFailureKind.CONFIGURATION

        with pytest.raises(JobSourceError) as captured2:
            AdzunaJobSource(app_id=APP_ID, app_key="   ", client=client)
        assert captured2.value.kind is JobSourceFailureKind.CONFIGURATION


def test_adzuna_search_sends_correct_get_request() -> None:
    request_received = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_received
        request_received = True
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.url.host == "api.adzuna.com"
        assert request.url.path == "/v1/api/jobs/br/search/1"
        assert request.headers["accept"] == "application/json"

        params = request.url.params
        assert params["app_id"] == APP_ID
        assert params["app_key"] == APP_KEY
        assert params["what"] == "desenvolvedor python"
        assert params["where"] == "Rio de Janeiro"
        assert params["results_per_page"] == "10"

        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "12345",
                        "title": "Desenvolvedor Python",
                        "company": {"display_name": "Empresa X"},
                        "location": {"display_name": "Rio de Janeiro, RJ"},
                        "redirect_url": "https://www.adzuna.com.br/details/12345",
                        "description": "Vaga para Dev Python",
                        "created": "2026-08-25T10:00:00Z",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(
            app_id=APP_ID,
            app_key=APP_KEY,
            client=client,
            clock=lambda: COLLECTED_AT,
        )
        postings = source.search(
            JobSourceQuery(
                keywords="desenvolvedor python",
                location="Rio de Janeiro",
                limit=10,
            )
        )

    assert request_received is True
    assert postings == (
        JobPosting(
            source_name="adzuna-br",
            external_id="12345",
            title="Desenvolvedor Python",
            company="Empresa X",
            location="Rio de Janeiro, RJ",
            source_url="https://www.adzuna.com.br/details/12345",
            collected_at=COLLECTED_AT,
            summary="Vaga para Dev Python",
            source_updated_at=datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        ),
    )


def test_adzuna_search_omits_where_when_location_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "where" not in request.url.params
        return httpx.Response(200, json={"results": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(app_id=APP_ID, app_key=APP_KEY, client=client)
        postings = source.search(
            JobSourceQuery(keywords="python", location="", limit=5)
        )

    assert postings == ()


def test_adzuna_search_converts_multiple_postings_preserving_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "1",
                        "title": "Job 1",
                        "redirect_url": "https://example.invalid/1",
                    },
                    {
                        "id": "2",
                        "title": "Job 2",
                        "redirect_url": "https://example.invalid/2",
                    },
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(
            app_id=APP_ID,
            app_key=APP_KEY,
            client=client,
            clock=lambda: COLLECTED_AT,
        )
        postings = source.search(JobSourceQuery(keywords="dev", location="", limit=5))

    assert len(postings) == 2
    assert postings[0].external_id == "1"
    assert postings[1].external_id == "2"


def test_adzuna_search_preserves_missing_optional_fields_as_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 999,
                        "title": "Engenheiro de Dados",
                        "redirect_url": "https://example.invalid/999",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(
            app_id=APP_ID,
            app_key=APP_KEY,
            client=client,
            clock=lambda: COLLECTED_AT,
        )
        postings = source.search(JobSourceQuery(keywords="dados", location="", limit=5))

    assert postings == (
        JobPosting(
            source_name="adzuna-br",
            external_id="999",
            title="Engenheiro de Dados",
            company=None,
            location=None,
            source_url="https://example.invalid/999",
            collected_at=COLLECTED_AT,
            summary=None,
            source_updated_at=None,
        ),
    )


def test_adzuna_search_returns_empty_tuple_when_results_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(app_id=APP_ID, app_key=APP_KEY, client=client)
        postings = source.search(JobSourceQuery(keywords="ruby", location="", limit=5))

    assert postings == ()


def test_adzuna_search_translates_authentication_failure() -> None:
    raw_payload_sentinel = "UNSAFE_CREDENTIAL_PAYLOAD"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.AUTHENTICATION
    assert str(error) == "As credenciais da Adzuna foram rejeitadas."
    assert error.action == "Solicite ou configure app_id e app_key válidos da Adzuna."
    assert error.retryable is False
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_adzuna_search_translates_rate_limit() -> None:
    raw_payload_sentinel = "UNSAFE_RATE_LIMIT_PAYLOAD"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.RATE_LIMIT
    assert str(error) == "A Adzuna limitou a busca."
    assert error.action == "Verifique a quota da conta e aguarde antes de tentar novamente."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_adzuna_search_translates_timeout() -> None:
    timeout_sentinel = "TIMEOUT_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(timeout_sentinel, request=request)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.TIMEOUT
    assert str(error) == "A Adzuna não respondeu dentro do tempo limite."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, timeout_sentinel)


def test_adzuna_search_translates_transport_failure() -> None:
    transport_sentinel = "TRANSPORT_SENTINEL"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(transport_sentinel, request=request)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.UNAVAILABLE
    assert str(error) == "Não foi possível conectar à Adzuna."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, transport_sentinel)


def test_adzuna_search_translates_5xx_server_error() -> None:
    raw_payload_sentinel = "500_SERVER_ERROR"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.UNAVAILABLE
    assert str(error) == "A Adzuna está temporariamente indisponível."
    assert error.action == "Tente novamente mais tarde; nenhuma repetição automática foi feita."
    assert error.retryable is True
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_adzuna_search_rejects_invalid_json_as_contract_error() -> None:
    raw_payload_sentinel = "NOT_JSON"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=raw_payload_sentinel)

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.CONTRACT
    assert str(error) == "A resposta da Adzuna não corresponde ao formato esperado."
    assert error.retryable is False
    _assert_failure_is_sanitized(error, raw_payload_sentinel)


def test_adzuna_search_rejects_missing_or_invalid_results_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": "invalid_type"})

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.CONTRACT


def test_adzuna_search_rejects_incompatible_job_item() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "123",
                        # title is missing
                        "redirect_url": "https://example.invalid/123",
                    }
                ]
            },
        )

    error = _capture_search_failure(handler)
    assert error.kind is JobSourceFailureKind.CONTRACT


def _capture_search_failure(
    handler: Callable[[httpx.Request], httpx.Response],
) -> JobSourceError:
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        source = AdzunaJobSource(app_id=APP_ID, app_key=APP_KEY, client=client)
        with pytest.raises(JobSourceError) as captured:
            source.search(JobSourceQuery(keywords="Python", location="Brasil", limit=1))

    return captured.value


def _assert_failure_is_sanitized(error: JobSourceError, unsafe_marker: str) -> None:
    safe_surface = f"{error!r} {error.action}"
    assert APP_ID not in safe_surface
    assert APP_KEY not in safe_surface
    assert unsafe_marker not in safe_surface
    assert error.__context__ is None
