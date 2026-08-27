import pytest

from buscador_de_vaga.location import locations_equivalent, normalize_location


@pytest.mark.parametrize(
    ("state_name", "abbreviation"),
    (
        ("Acre", "AC"),
        ("Alagoas", "AL"),
        ("Amapá", "AP"),
        ("Amazonas", "AM"),
        ("Bahia", "BA"),
        ("Ceará", "CE"),
        ("Distrito Federal", "DF"),
        ("Espírito Santo", "ES"),
        ("Goiás", "GO"),
        ("Maranhão", "MA"),
        ("Mato Grosso", "MT"),
        ("Mato Grosso do Sul", "MS"),
        ("Minas Gerais", "MG"),
        ("Pará", "PA"),
        ("Paraíba", "PB"),
        ("Paraná", "PR"),
        ("Pernambuco", "PE"),
        ("Piauí", "PI"),
        ("Rio de Janeiro", "RJ"),
        ("Rio Grande do Norte", "RN"),
        ("Rio Grande do Sul", "RS"),
        ("Rondônia", "RO"),
        ("Roraima", "RR"),
        ("Santa Catarina", "SC"),
        ("São Paulo", "SP"),
        ("Sergipe", "SE"),
        ("Tocantins", "TO"),
    ),
)
def test_brazilian_state_names_and_abbreviations_have_the_same_canonical_state(
    state_name: str,
    abbreviation: str,
) -> None:
    assert (
        normalize_location(f"Cidade, {state_name}").state,
        normalize_location(f"Cidade, {abbreviation}").state,
    ) == (abbreviation, abbreviation)


def test_rio_de_janeiro_without_state_is_equivalent_to_rj_abbreviation() -> None:
    assert locations_equivalent("Rio de Janeiro", "Rio de Janeiro, RJ")


def test_rio_de_janeiro_is_equivalent_to_full_state_name() -> None:
    assert locations_equivalent(
        "Rio de Janeiro",
        "Rio de Janeiro, Estado do Rio de Janeiro",
    )


def test_comma_and_structural_hyphen_are_equivalent_state_separators() -> None:
    assert locations_equivalent("Rio de Janeiro, RJ", "Rio de Janeiro - RJ")


def test_sao_paulo_without_state_is_equivalent_to_sp_abbreviation() -> None:
    assert locations_equivalent("São Paulo", "São Paulo, SP")


def test_sao_paulo_is_equivalent_to_full_state_name() -> None:
    assert locations_equivalent("São Paulo", "São Paulo, Estado de São Paulo")


def test_case_does_not_change_location_equivalence() -> None:
    assert locations_equivalent("RIO DE JANEIRO", "rio de janeiro, rj")


def test_accents_do_not_change_location_equivalence() -> None:
    assert locations_equivalent("SAO PAULO", "São Paulo, SP")


def test_extra_spaces_do_not_change_location_equivalence() -> None:
    assert locations_equivalent("  Rio   de Janeiro ", "Rio de Janeiro,   RJ")


def test_rio_de_janeiro_is_not_equivalent_to_niteroi() -> None:
    assert not locations_equivalent("Rio de Janeiro", "Niterói")


def test_sao_paulo_is_not_equivalent_to_campinas() -> None:
    assert not locations_equivalent("São Paulo", "Campinas")


def test_explicitly_conflicting_states_are_not_equivalent() -> None:
    assert not locations_equivalent("Rio de Janeiro, RJ", "Rio de Janeiro, SP")


def test_repeated_normalization_calls_are_deterministic() -> None:
    first = normalize_location("Rio de Janeiro, Estado do Rio de Janeiro")
    second = normalize_location("Rio de Janeiro, Estado do Rio de Janeiro")

    assert first == second
