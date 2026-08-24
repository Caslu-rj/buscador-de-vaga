"""CLI local para descobrir e apresentar oportunidades."""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import httpx

from buscador_de_vaga.discovery import (
    InvalidDiscoveryRequest,
    JobSource,
    JobSourceError,
    JobSourceFailureKind,
    OpportunityDiscovery,
)
from buscador_de_vaga.domain import (
    CandidateProfile,
    EligibilityStatus,
    JobCategory,
    SearchCriteria,
)
from buscador_de_vaga.profile import CandidateProfileError, load_candidate_profile
from buscador_de_vaga.sources.jooble import JoobleJobSource
from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError


def main(
    argv: Sequence[str] | None = None,
    *,
    http_client: httpx.Client | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Executa a CLI e devolve um código adequado para o processo."""
    parser = _build_parser()
    arguments = parser.parse_args(argv)

    try:
        profile = load_candidate_profile(Path(arguments.profile))
    except CandidateProfileError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: verifique o caminho e o formato do CandidateProfile.",
            file=sys.stderr,
        )
        return 2

    criteria = SearchCriteria(
        category=JobCategory(arguments.category),
        location=arguments.location,
        limit=arguments.limit,
    )

    if arguments.postings_file is not None:
        try:
            source = SyntheticJobSource.from_file(Path(arguments.postings_file))
        except SyntheticSourceError as error:
            print(f"Erro: {error}", file=sys.stderr)
            print(
                "Ação: verifique o caminho e o formato da fixture de JobPostings.",
                file=sys.stderr,
            )
            return 2
        return _discover_and_present(profile=profile, criteria=criteria, source=source)

    try:
        api_key = _required_jooble_api_key(os.environ if environ is None else environ)
    except JobSourceError as error:
        return _report_source_error(error)

    if http_client is not None:
        return _discover_and_present(
            profile=profile,
            criteria=criteria,
            source=JoobleJobSource(api_key=api_key, client=http_client),
        )

    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        return _discover_and_present(
            profile=profile,
            criteria=criteria,
            source=JoobleJobSource(api_key=api_key, client=client),
        )


def _discover_and_present(
    *,
    profile: CandidateProfile,
    criteria: SearchCriteria,
    source: JobSource,
) -> int:
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
    except JobSourceError as error:
        return _report_source_error(error)

    count = len(result.shortlist.items)
    if count == 0:
        print("Nenhuma oportunidade encontrada.")
        return 0

    noun = "oportunidade" if count == 1 else "oportunidades"
    adjective = "encontrada" if count == 1 else "encontradas"
    print(f"{count} {noun} {adjective}.")
    assessments_by_id = {
        assessment.opportunity_id: assessment for assessment in result.match_assessments
    }
    for position, opportunity in enumerate(result.shortlist.items, start=1):
        assessment = assessments_by_id[opportunity.id]
        print(f"{position}. {_safe_terminal_text(opportunity.title)}")
        if opportunity.company is not None:
            print(f"   Empresa: {_safe_terminal_text(opportunity.company)}")
        if opportunity.location is not None:
            print(f"   Local: {_safe_terminal_text(opportunity.location)}")
        print(f"   URL: {_safe_terminal_text(opportunity.source_url)}")
        print(f"   Elegibilidade: {_eligibility_label(assessment.eligibility_status)}")
        print(
            f"   FitScore: {assessment.fit_score.value}/100 "
            f"(cobertura de evidência: {assessment.fit_score.evidence_coverage}%)"
        )
        print("   Breakdown:")
        for item in assessment.fit_score.breakdown:
            print(
                f"     - {item.dimension.value}: {item.awarded_points}/{item.weight} pts "
                f"(cobertura: {item.covered_weight}/{item.weight})"
            )
        print("   Pontos fortes:")
        if assessment.strengths:
            for strength in assessment.strengths:
                print(f"     - {_safe_terminal_text(strength.requirement.statement)}")
        else:
            print("     - (nenhum)")
        print("   Skill Gaps:")
        if assessment.skill_gaps:
            for gap in assessment.skill_gaps:
                print(f"     - {_safe_terminal_text(gap.requirement.statement)}")
        else:
            print("     - (nenhum)")
        print("   Requisitos não informados:")
        if assessment.unknown_requirements:
            for unknown in assessment.unknown_requirements:
                print(f"     - {_safe_terminal_text(unknown.requirement.statement)}")
        else:
            print("     - (nenhum)")
        print("   Possíveis impeditivos:")
        if assessment.possible_blockers:
            for blocker in assessment.possible_blockers:
                print(f"     - {_safe_terminal_text(blocker.assessment.requirement.statement)}")
        else:
            print("     - (nenhum)")

    return 0


def _eligibility_label(status: EligibilityStatus) -> str:
    if status is EligibilityStatus.ELIGIBLE:
        return "Elegível"
    if status is EligibilityStatus.UNCERTAIN:
        return "Incerto"
    if status is EligibilityStatus.INELIGIBLE:
        return "Inelegível"
    return status.value


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
        help="Número máximo de publicações retornadas na primeira página.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--postings-file",
        help="Arquivo JSON de JobPostings sintéticos para o tracer bullet.",
    )
    source_group.add_argument(
        "--jooble",
        action="store_true",
        help="Consulta live explícita ao Jooble usando JOOBLE_API_KEY.",
    )
    return parser


def _required_jooble_api_key(environ: Mapping[str, str]) -> str:
    api_key = environ.get("JOOBLE_API_KEY")
    if api_key is None or not api_key.strip():
        raise JobSourceError(
            "JOOBLE_API_KEY não está configurada.",
            source_name=JoobleJobSource.name,
            kind=JobSourceFailureKind.CONFIGURATION,
            action="defina JOOBLE_API_KEY no ambiente antes da busca live.",
            retryable=False,
        )
    return api_key.strip()


def _report_source_error(error: JobSourceError) -> int:
    print(f"Erro: {error}", file=sys.stderr)
    print(f"Ação: {error.action}", file=sys.stderr)
    if error.kind is JobSourceFailureKind.CONFIGURATION:
        return 2
    return 1


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
