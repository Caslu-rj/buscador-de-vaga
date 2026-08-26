"""Adapter síncrono para a REST API oficial da Adzuna."""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from buscador_de_vaga.discovery import JobSourceError, JobSourceFailureKind
from buscador_de_vaga.domain import JobPosting, JobSourceQuery

_API_BASE_URL = "https://api.adzuna.com/v1/api/jobs/br/search/1"
_RETRY_LATER_ACTION = "Tente novamente mais tarde; nenhuma repetição automática foi feita."


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AdzunaJobSource:
    """Consulta a REST API da Adzuna para o mercado brasileiro."""

    name = "adzuna-br"

    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        client: httpx.Client,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not app_id or not app_id.strip() or not app_key or not app_key.strip():
            raise JobSourceError(
                "As credenciais da Adzuna não foram configuradas.",
                source_name=self.name,
                kind=JobSourceFailureKind.CONFIGURATION,
                action="Configure app_id e app_key válidos para a Adzuna.",
                retryable=False,
            )
        self._app_id = app_id
        self._app_key = app_key
        self._client = client
        self._clock = clock

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        """Consulta a primeira página de busca da Adzuna."""
        response = self._request(query)
        if response.status_code in (401, 403):
            raise JobSourceError(
                "As credenciais da Adzuna foram rejeitadas.",
                source_name=self.name,
                kind=JobSourceFailureKind.AUTHENTICATION,
                action="Solicite ou configure app_id e app_key válidos da Adzuna.",
                retryable=False,
            )
        if response.status_code == 429:
            raise JobSourceError(
                "A Adzuna limitou a busca.",
                source_name=self.name,
                kind=JobSourceFailureKind.RATE_LIMIT,
                action="Verifique a quota da conta e aguarde antes de tentar novamente.",
                retryable=True,
            )
        if response.status_code >= 500:
            raise _unavailable_error("A Adzuna está temporariamente indisponível.")
        if response.status_code != 200:
            raise _contract_error()

        postings = _try_decode_response(response, collected_at=self._clock())
        if postings is None:
            raise _contract_error()
        return postings

    def _request(self, query: JobSourceQuery) -> httpx.Response:
        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query.keywords,
            "results_per_page": query.limit,
        }
        if query.location and query.location.strip():
            params["where"] = query.location.strip()

        try:
            return self._client.get(
                _API_BASE_URL,
                params=params,
                headers={"Accept": "application/json"},
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            failure = JobSourceError(
                "A Adzuna não respondeu dentro do tempo limite.",
                source_name=self.name,
                kind=JobSourceFailureKind.TIMEOUT,
                action=_RETRY_LATER_ACTION,
                retryable=True,
            )
        except httpx.RequestError:
            failure = _unavailable_error("Não foi possível conectar à Adzuna.")
        raise failure


def _try_decode_response(
    response: httpx.Response,
    *,
    collected_at: datetime,
) -> tuple[JobPosting, ...] | None:
    try:
        payload: object = response.json()
        if not isinstance(payload, dict):
            raise ValueError("a resposta da Adzuna deve ser um objeto JSON")
        results: object = payload.get("results")
        if not isinstance(results, list):
            raise ValueError("results da resposta da Adzuna deve ser uma lista JSON")

        return tuple(_decode_posting(job, collected_at=collected_at) for job in results)
    except (TypeError, ValueError):
        return None


def _contract_error() -> JobSourceError:
    return JobSourceError(
        "A resposta da Adzuna não corresponde ao formato esperado.",
        source_name=AdzunaJobSource.name,
        kind=JobSourceFailureKind.CONTRACT,
        action=(
            "Verifique se a integração está atualizada e reporte uma possível mudança no contrato."
        ),
        retryable=False,
    )


def _unavailable_error(message: str) -> JobSourceError:
    return JobSourceError(
        message,
        source_name=AdzunaJobSource.name,
        kind=JobSourceFailureKind.UNAVAILABLE,
        action=_RETRY_LATER_ACTION,
        retryable=True,
    )


def _decode_posting(value: object, *, collected_at: datetime) -> JobPosting:
    if not isinstance(value, dict):
        raise ValueError("cada vaga da Adzuna deve ser um objeto JSON")

    raw_id = value.get("id")
    if raw_id is None:
        raise ValueError("id da vaga da Adzuna é obrigatório")
    if not isinstance(raw_id, (str, int)) or isinstance(raw_id, bool):
        raise ValueError("id da vaga da Adzuna deve ser texto ou inteiro")
    external_id = str(raw_id)
    if not external_id.strip():
        raise ValueError("id da vaga da Adzuna não pode ser vazio")

    title = _required_text(value.get("title"))
    company = _parse_company(value.get("company"))
    location = _parse_location(value.get("location"))
    source_url = _required_text(value.get("redirect_url"))
    summary = _optional_text(value.get("description"))
    source_updated_at = _optional_datetime(value.get("created"))

    return JobPosting(
        source_name=AdzunaJobSource.name,
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        source_url=source_url,
        collected_at=collected_at,
        summary=summary,
        source_updated_at=source_updated_at,
    )


def _parse_company(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("company da Adzuna deve ser objeto JSON")
    return _optional_text(value.get("display_name"))


def _parse_location(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("location da Adzuna deve ser objeto JSON")
    return _optional_text(value.get("display_name"))


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("campo obrigatório da vaga da Adzuna deve ser texto não vazio")
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
        raise ValueError("created da vaga da Adzuna deve estar em formato ISO 8601") from error
