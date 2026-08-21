"""Adapter síncrono para a REST API oficial do Jooble."""

from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from buscador_de_vaga.discovery import JobSourceError, JobSourceFailureKind
from buscador_de_vaga.domain import JobPosting, JobSourceQuery

_API_BASE_URL = "https://jooble.org/api"
_RETRY_LATER_ACTION = "Tente novamente mais tarde; nenhuma repetição automática foi feita."


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JoobleJobSource:
    """Consulta uma página do Jooble e traduz seu schema para o domínio."""

    name = "jooble-br"

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.Client,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._clock = clock

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        """Consulta somente a primeira página da busca."""
        response = self._request(query)
        if response.status_code == 403:
            raise JobSourceError(
                "A credencial do Jooble foi rejeitada.",
                source_name=self.name,
                kind=JobSourceFailureKind.AUTHENTICATION,
                action="Solicite ou configure uma chave brasileira válida do Jooble.",
                retryable=False,
            )
        if response.status_code == 429:
            raise JobSourceError(
                "O Jooble limitou a busca.",
                source_name=self.name,
                kind=JobSourceFailureKind.RATE_LIMIT,
                action="Verifique a quota da chave e aguarde antes de tentar novamente.",
                retryable=True,
            )
        if response.status_code >= 500:
            raise _unavailable_error("O Jooble está temporariamente indisponível.")
        if response.status_code != 200:
            raise _contract_error()

        postings = _try_decode_response(response, collected_at=self._clock())
        if postings is None:
            raise _contract_error()
        return postings

    def _request(self, query: JobSourceQuery) -> httpx.Response:
        try:
            return self._client.post(
                f"{_API_BASE_URL}/{quote(self._api_key, safe='')}",
                headers={"Accept": "application/json"},
                follow_redirects=False,
                json={
                    "keywords": query.keywords,
                    "location": query.location,
                    "page": 1,
                    "ResultOnPage": query.limit,
                },
            )
        except httpx.TimeoutException:
            failure = JobSourceError(
                "O Jooble não respondeu dentro do tempo limite.",
                source_name=self.name,
                kind=JobSourceFailureKind.TIMEOUT,
                action=_RETRY_LATER_ACTION,
                retryable=True,
            )
        except httpx.RequestError:
            failure = _unavailable_error("Não foi possível conectar ao Jooble.")
        raise failure


def _try_decode_response(
    response: httpx.Response,
    *,
    collected_at: datetime,
) -> tuple[JobPosting, ...] | None:
    try:
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise ValueError("a resposta do Jooble deve ser um objeto JSON")
        total_count: object = payload.get("totalCount")
        if not isinstance(total_count, int) or isinstance(total_count, bool):
            raise ValueError("totalCount da resposta do Jooble deve ser um inteiro")
        jobs: object = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("jobs da resposta do Jooble deve ser uma lista JSON")

        return tuple(_decode_posting(job, collected_at=collected_at) for job in jobs)
    except (TypeError, ValueError):
        return None


def _contract_error() -> JobSourceError:
    return JobSourceError(
        "A resposta do Jooble não corresponde ao formato esperado.",
        source_name=JoobleJobSource.name,
        kind=JobSourceFailureKind.CONTRACT,
        action=(
            "Verifique se a integração está atualizada e reporte uma possível mudança no contrato."
        ),
        retryable=False,
    )


def _unavailable_error(message: str) -> JobSourceError:
    return JobSourceError(
        message,
        source_name=JoobleJobSource.name,
        kind=JobSourceFailureKind.UNAVAILABLE,
        action=_RETRY_LATER_ACTION,
        retryable=True,
    )


def _decode_posting(value: object, *, collected_at: datetime) -> JobPosting:
    if not isinstance(value, dict):
        raise ValueError("cada vaga do Jooble deve ser um objeto JSON")

    external_id = value.get("id")
    if not isinstance(external_id, int) or isinstance(external_id, bool):
        raise ValueError("id da vaga do Jooble deve ser um inteiro")

    return JobPosting(
        source_name=JoobleJobSource.name,
        external_id=str(external_id),
        title=_required_text(value.get("title")),
        company=_optional_text(value.get("company")),
        location=_optional_text(value.get("location")),
        source_url=_required_text(value.get("link")),
        collected_at=collected_at,
        summary=_optional_text(value.get("snippet")),
        source_updated_at=_optional_datetime(value.get("updated")),
    )


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("campo obrigatório da vaga do Jooble deve ser texto não vazio")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text(value)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = _required_text(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("updated da vaga do Jooble deve estar em formato ISO 8601") from error
