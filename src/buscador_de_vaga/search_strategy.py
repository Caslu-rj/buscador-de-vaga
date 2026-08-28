"""Estratégia determinística de consultas por estágio da carreira."""

from typing import Final

from buscador_de_vaga.candidate_positioning import (
    MAX_AUTOMATIC_QUERIES,
    CandidateCareerLevel,
    CandidateProfileAssessment,
)
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

_AUTOMATIC_LEVEL_KEYWORDS: Final[
    dict[JobCategory, dict[CandidateCareerLevel, str]]
] = {
    JobCategory.SOFTWARE_DEVELOPMENT: {
        CandidateCareerLevel.INTERNSHIP: "estágio desenvolvimento",
        CandidateCareerLevel.JUNIOR: "desenvolvedor júnior",
        CandidateCareerLevel.MID_LEVEL: "desenvolvedor pleno",
        CandidateCareerLevel.SENIOR: "desenvolvedor sênior",
    },
    JobCategory.DATA: {
        CandidateCareerLevel.INTERNSHIP: "estágio dados",
        CandidateCareerLevel.JUNIOR: "analista de dados júnior",
        CandidateCareerLevel.MID_LEVEL: "analista de dados pleno",
        CandidateCareerLevel.SENIOR: "analista de dados sênior",
    },
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: {
        CandidateCareerLevel.INTERNSHIP: "estágio suporte TI",
        CandidateCareerLevel.JUNIOR: "suporte TI júnior",
        CandidateCareerLevel.MID_LEVEL: "suporte TI pleno",
        CandidateCareerLevel.SENIOR: "suporte TI sênior",
    },
    JobCategory.SYSTEMS: {
        CandidateCareerLevel.INTERNSHIP: "estágio sistemas",
        CandidateCareerLevel.JUNIOR: "analista de sistemas júnior",
        CandidateCareerLevel.MID_LEVEL: "analista de sistemas pleno",
        CandidateCareerLevel.SENIOR: "analista de sistemas sênior",
    },
    JobCategory.QUALITY_ASSURANCE: {
        CandidateCareerLevel.INTERNSHIP: "estágio QA",
        CandidateCareerLevel.JUNIOR: "QA júnior",
        CandidateCareerLevel.MID_LEVEL: "QA pleno",
        CandidateCareerLevel.SENIOR: "QA sênior",
    },
}

_GENERIC_CATEGORY_KEYWORDS: Final[dict[JobCategory, str]] = {
    JobCategory.SOFTWARE_DEVELOPMENT: "desenvolvedor de software",
    JobCategory.DATA: "analista de dados",
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: "suporte de TI infraestrutura",
    JobCategory.SYSTEMS: "analista de sistemas",
    JobCategory.QUALITY_ASSURANCE: "qualidade de software QA",
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


class AutomaticCareerSearchStrategy:
    """Produz consultas automáticas deduplicadas e limitadas para o plano de busca."""

    def build_queries(
        self,
        *,
        assessment: CandidateProfileAssessment,
        location: str,
        limit: int,
        max_queries: int = MAX_AUTOMATIC_QUERIES,
    ) -> tuple[JobSourceQuery, ...]:
        """Gera consultas para as categorias selecionadas respeitando o limite máximo."""
        queries: list[JobSourceQuery] = []
        seen_queries: set[tuple[str, str, int]] = set()
        if max_queries < 1:
            return ()

        def append_query(keywords: str) -> bool:
            key = (keywords, location, limit)
            if key not in seen_queries:
                seen_queries.add(key)
                queries.append(
                    JobSourceQuery(keywords=keywords, location=location, limit=limit)
                )
            return len(queries) >= max_queries

        for category in assessment.selected_categories:
            cat_assessment = assessment.get_assessment(category)
            if cat_assessment is None:
                continue

            for level in cat_assessment.recommended_levels:
                keywords = _AUTOMATIC_LEVEL_KEYWORDS.get(category, {}).get(level)
                if keywords is not None and append_query(keywords):
                    return tuple(queries)

        for category in assessment.selected_categories:
            generic_keywords = _GENERIC_CATEGORY_KEYWORDS.get(category)
            if generic_keywords is not None and append_query(generic_keywords):
                return tuple(queries)

        return tuple(queries)
