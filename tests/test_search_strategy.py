from buscador_de_vaga.domain import JobCategory
from buscador_de_vaga.search_strategy import CareerSearchStrategy


def test_software_development_generates_entry_level_queries_in_order() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "estágio desenvolvimento",
        "desenvolvedor python júnior",
        "desenvolvedor de software",
    )


def test_it_support_infrastructure_has_its_own_ordered_queries() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.IT_SUPPORT_INFRASTRUCTURE,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "estágio suporte TI",
        "suporte TI júnior",
        "suporte de TI infraestrutura",
    )


def test_quality_assurance_has_its_own_ordered_queries() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.QUALITY_ASSURANCE,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "estágio QA",
        "QA júnior",
        "qualidade de software QA",
    )


def test_data_has_its_own_ordered_queries() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.DATA,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "estágio dados",
        "analista de dados júnior",
        "analista de dados",
    )


def test_systems_has_its_own_ordered_queries() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.SYSTEMS,
        location="Brasil",
        limit=10,
    )

    assert tuple(query.keywords for query in queries) == (
        "estágio sistemas",
        "analista de sistemas júnior",
        "analista de sistemas",
    )


def test_internship_queries_come_before_junior_queries() -> None:
    keywords = tuple(
        query.keywords
        for query in CareerSearchStrategy().queries_for(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Brasil",
            limit=10,
        )
    )

    assert keywords.index("estágio desenvolvimento") < keywords.index(
        "desenvolvedor python júnior"
    )


def test_junior_queries_come_before_the_generic_query() -> None:
    keywords = tuple(
        query.keywords
        for query in CareerSearchStrategy().queries_for(
            category=JobCategory.SOFTWARE_DEVELOPMENT,
            location="Brasil",
            limit=10,
        )
    )

    assert keywords.index("desenvolvedor python júnior") < keywords.index(
        "desenvolvedor de software"
    )


def test_location_is_preserved_in_every_query() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Rio de Janeiro, RJ",
        limit=10,
    )

    assert tuple(query.location for query in queries) == ("Rio de Janeiro, RJ",) * 3


def test_limit_is_preserved_in_every_query() -> None:
    queries = CareerSearchStrategy().queries_for(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=7,
    )

    assert tuple(query.limit for query in queries) == (7,) * 3


def test_repeated_calls_produce_identical_queries() -> None:
    strategy = CareerSearchStrategy()

    first = strategy.queries_for(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )
    second = strategy.queries_for(
        category=JobCategory.SOFTWARE_DEVELOPMENT,
        location="Brasil",
        limit=10,
    )

    assert first == second
