"""Adapters de JobSource disponíveis para a aplicação."""

from buscador_de_vaga.sources.jooble import JoobleJobSource
from buscador_de_vaga.sources.multi import MultiSourceJobSource
from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError

__all__ = [
    "JoobleJobSource",
    "MultiSourceJobSource",
    "SyntheticJobSource",
    "SyntheticSourceError",
]
