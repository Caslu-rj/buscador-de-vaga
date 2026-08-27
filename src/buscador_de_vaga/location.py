"""Normalização determinística de localizações brasileiras."""

import re
from dataclasses import dataclass
from unicodedata import combining
from unicodedata import normalize as normalize_unicode

_BRAZILIAN_STATES: tuple[tuple[str, str], ...] = (
    ("acre", "AC"),
    ("alagoas", "AL"),
    ("amapa", "AP"),
    ("amazonas", "AM"),
    ("bahia", "BA"),
    ("ceara", "CE"),
    ("distrito federal", "DF"),
    ("espirito santo", "ES"),
    ("goias", "GO"),
    ("maranhao", "MA"),
    ("mato grosso", "MT"),
    ("mato grosso do sul", "MS"),
    ("minas gerais", "MG"),
    ("para", "PA"),
    ("paraiba", "PB"),
    ("parana", "PR"),
    ("pernambuco", "PE"),
    ("piaui", "PI"),
    ("rio de janeiro", "RJ"),
    ("rio grande do norte", "RN"),
    ("rio grande do sul", "RS"),
    ("rondonia", "RO"),
    ("roraima", "RR"),
    ("santa catarina", "SC"),
    ("sao paulo", "SP"),
    ("sergipe", "SE"),
    ("tocantins", "TO"),
)
_STATE_BY_ALIAS = {
    alias: abbreviation
    for state_name, abbreviation in _BRAZILIAN_STATES
    for alias in (state_name, abbreviation.casefold())
}


@dataclass(frozen=True, slots=True)
class NormalizedLocation:
    """Cidade canônica acompanhada de uma UF explicitamente informada."""

    city: str
    state: str | None = None

    @property
    def canonical_value(self) -> str:
        """Representação textual estável para uso interno no matching."""
        if self.state is None:
            return self.city
        return f"{self.city}, {self.state.casefold()}"


def normalize_location(value: str) -> NormalizedLocation:
    """Normaliza uma localização sem inferir dados geográficos ausentes."""
    comparison_text = _comparison_text(value)
    explicit_state_parts = _explicit_state_parts(comparison_text)
    if explicit_state_parts is not None:
        city_text, state_text = explicit_state_parts
        state = _STATE_BY_ALIAS.get(_normalize_state_alias(state_text))
        if state is not None:
            return NormalizedLocation(
                city=_normalize_component(city_text),
                state=state,
            )
    return NormalizedLocation(city=_normalize_component(comparison_text))


def locations_equivalent(left: str, right: str) -> bool:
    """Compara cidades e rejeita UFs explicitamente conflitantes."""
    normalized_left = normalize_location(left)
    normalized_right = normalize_location(right)
    if not normalized_left.city or normalized_left.city != normalized_right.city:
        return False
    return not (
        normalized_left.state is not None
        and normalized_right.state is not None
        and normalized_left.state != normalized_right.state
    )


def _comparison_text(value: str) -> str:
    decomposed = normalize_unicode("NFKD", value)
    without_accents = "".join(character for character in decomposed if not combining(character))
    return " ".join(without_accents.casefold().split())


def _normalize_component(value: str) -> str:
    without_punctuation = re.sub(r"[^\w\s]|_", " ", value)
    return " ".join(without_punctuation.split())


def _explicit_state_parts(value: str) -> tuple[str, str] | None:
    city_text, separator, state_text = value.rpartition(",")
    if separator:
        return city_text, state_text
    hyphenated = re.fullmatch(r"(.+?)\s+-\s+(.+)", value)
    if hyphenated is not None:
        return hyphenated.group(1), hyphenated.group(2)
    return None


def _normalize_state_alias(value: str) -> str:
    normalized = _normalize_component(value)
    for prefix in ("estado do ", "estado de ", "estado da "):
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix)
    return normalized
