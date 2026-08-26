"""Adapters de JobSource disponíveis para a aplicação."""

from buscador_de_vaga.sources.adzuna import AdzunaJobSource
from buscador_de_vaga.sources.jooble import JoobleJobSource
from buscador_de_vaga.sources.multi import MultiSourceJobSource
from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError

__all__ = [
    "AdzunaJobSource",
    "JoobleJobSource",
    "MultiSourceJobSource",
    "SyntheticJobSource",
    "SyntheticSourceError",
]
