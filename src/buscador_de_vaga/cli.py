"""CLI do primeiro tracer bullet de descoberta."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from buscador_de_vaga.discovery import InvalidDiscoveryRequest, OpportunityDiscovery
from buscador_de_vaga.domain import JobCategory, SearchCriteria
from buscador_de_vaga.profile import CandidateProfileError, load_candidate_profile
from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError


def main(argv: Sequence[str] | None = None) -> int:
    """Executa a CLI e devolve um código adequado para o processo."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)

    try:
        profile = load_candidate_profile(Path(arguments.profile))
        source = SyntheticJobSource.from_file(Path(arguments.postings_file))
    except CandidateProfileError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: verifique o caminho e o formato do CandidateProfile.",
            file=sys.stderr,
        )
        return 2
    except SyntheticSourceError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: verifique o caminho e o formato da fixture de JobPostings.",
            file=sys.stderr,
        )
        return 2

    criteria = SearchCriteria(
        category=JobCategory(arguments.category),
        location=arguments.location,
        limit=arguments.limit,
    )
    try:
        result = OpportunityDiscovery(source=source).discover(profile, criteria)
    except InvalidDiscoveryRequest as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: escolha uma JobCategory declarada no perfil.",
            file=sys.stderr,
        )
        return 2
    except SyntheticSourceError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: use uma fixture correspondente aos argumentos da busca.",
            file=sys.stderr,
        )
        return 2

    count = len(result.shortlist.items)
    if count == 0:
        print("Nenhuma oportunidade encontrada.")
        return 0

    noun = "oportunidade" if count == 1 else "oportunidades"
    adjective = "encontrada" if count == 1 else "encontradas"
    print(f"{count} {noun} {adjective}.")
    for position, opportunity in enumerate(result.shortlist.items, start=1):
        print(f"{position}. {_safe_terminal_text(opportunity.title)}")
        if opportunity.company is not None:
            print(f"   Empresa: {_safe_terminal_text(opportunity.company)}")
        if opportunity.location is not None:
            print(f"   Local: {_safe_terminal_text(opportunity.location)}")
        print(f"   URL: {_safe_terminal_text(opportunity.source_url)}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buscar-vagas",
        description="Descobre oportunidades de tecnologia a partir de um CandidateProfile local.",
    )
    parser.add_argument("--profile", required=True, help="Caminho do CandidateProfile JSON.")
    parser.add_argument(
        "--category",
        required=True,
        choices=tuple(category.value for category in JobCategory),
        help="JobCategory usada nesta execução.",
    )
    parser.add_argument("--location", required=True, help="Localização da busca.")
    parser.add_argument(
        "--limit",
        type=_positive_integer,
        default=10,
        help="Número máximo de publicações sintéticas.",
    )
    parser.add_argument(
        "--postings-file",
        required=True,
        help="Arquivo JSON de JobPostings sintéticos para o tracer bullet.",
    )
    return parser


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("deve ser um número inteiro") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("deve ser maior que zero")
    return parsed


def _safe_terminal_text(value: str) -> str:
    return "".join(character if character.isprintable() else " " for character in value)


if __name__ == "__main__":
    raise SystemExit(main())
