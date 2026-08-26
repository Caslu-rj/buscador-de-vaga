"""Agregador de múltiplos JobSources."""

from collections.abc import Iterable

from buscador_de_vaga.discovery import JobSource
from buscador_de_vaga.domain import JobPosting, JobSourceQuery


class MultiSourceJobSource:
    """Combina múltiplos JobSources consultando-os sequencialmente."""

    def __init__(self, sources: Iterable[JobSource]) -> None:
        self._sources: tuple[JobSource, ...] = tuple(sources)
        if not self._sources:
            raise ValueError("MultiSourceJobSource requer pelo menos um JobSource")

    @property
    def name(self) -> str:
        """Identificador legível e estável da fonte agregadora."""
        return "multi-source"

    def search(self, query: JobSourceQuery) -> tuple[JobPosting, ...]:
        """Consulta cada fonte sequencialmente e combina as publicações retornadas."""
        all_postings: list[JobPosting] = []
        for source in self._sources:
            postings = source.search(query)
            all_postings.extend(postings)
        return tuple(all_postings)
