"""Adapters de JobSource disponíveis para a aplicação."""

from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError

__all__ = ["SyntheticJobSource", "SyntheticSourceError"]
