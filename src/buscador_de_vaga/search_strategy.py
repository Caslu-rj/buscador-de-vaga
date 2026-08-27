"""Estratégia determinística de consultas por estágio da carreira."""

from typing import Final

from buscador_de_vaga.domain import JobCategory, JobSourceQuery

_CATEGORY_KEYWORDS: Final[dict[JobCategory, tuple[str, ...]]] = {
    JobCategory.SOFTWARE_DEVELOPMENT: (
        "estágio desenvolvimento",
        "desenvolvedor python júnior",
        "desenvolvedor de software",
    ),
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: (
        "estágio suporte TI",
        "suporte TI júnior",
        "suporte de TI infraestrutura",
    ),
    JobCategory.QUALITY_ASSURANCE: (
        "estágio QA",
        "QA júnior",
        "qualidade de software QA",
    ),
    JobCategory.DATA: (
        "estágio dados",
        "analista de dados júnior",
        "analista de dados",
    ),
    JobCategory.SYSTEMS: (
        "estágio sistemas",
        "analista de sistemas júnior",
        "analista de sistemas",
    ),
}


class CareerSearchStrategy:
    """Produz consultas ordenadas que priorizam oportunidades de entrada."""

    def queries_for(
        self,
        *,
        category: JobCategory,
        location: str,
        limit: int,
    ) -> tuple[JobSourceQuery, ...]:
        """Cria consultas independentes de fornecedor para uma JobCategory."""
        return tuple(
            JobSourceQuery(keywords=keywords, location=location, limit=limit)
            for keywords in _CATEGORY_KEYWORDS[category]
        )
