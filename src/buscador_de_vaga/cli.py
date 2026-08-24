"""CLI local para descobrir e apresentar oportunidades."""

import argparse
import json
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
from buscador_de_vaga.resume import (
    CandidateProfileDraft,
    DeterministicResumeParser,
    EmptyDocumentError,
    ResumeReadError,
    UnreadablePdfError,
    UnsupportedFileFormatError,
    read_resume,
)
from buscador_de_vaga.sources.jooble import JoobleJobSource
from buscador_de_vaga.sources.synthetic import SyntheticJobSource, SyntheticSourceError


def main(
    argv: Sequence[str] | None = None,
    *,
    http_client: httpx.Client | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Executa a CLI e devolve um código adequado para o processo."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] == "importar-curriculo":
        return _handle_importar_curriculo(args_list[1:])

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


def _build_importar_curriculo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buscar-vagas importar-curriculo",
        description="Importa, analisa e consolida um currículo em um CandidateProfile JSON.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Caminho do arquivo de currículo (.pdf ou .docx).",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Exibe no terminal a revisão estruturada (CandidateProfileDraft) sem salvar arquivos.",
    )
    parser.add_argument(
        "--output",
        help="Caminho do arquivo JSON de saída para salvar o CandidateProfile gerado.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve o arquivo de saída (--output) caso ele já exista.",
    )
    return parser


def _handle_importar_curriculo(args: list[str]) -> int:
    parser = _build_importar_curriculo_parser()
    try:
        arguments = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    if not arguments.review and not arguments.output:
        print("Erro: Deve informar --output <caminho> ou --review.", file=sys.stderr)
        print(
            "Ação: informe --output para salvar o perfil ou --review para inspecionar no terminal.",
            file=sys.stderr,
        )
        return 2

    output_path: Path | None = Path(arguments.output) if arguments.output else None
    if output_path is not None and output_path.exists() and not arguments.force:
        print(f"Erro: O arquivo de saída '{output_path}' já existe.", file=sys.stderr)
        print(
            "Ação: especifique outro caminho ou use --force para sobrescrever.",
            file=sys.stderr,
        )
        return 2

    file_path = Path(arguments.file)
    if not file_path.is_file():
        print(f"Erro: Arquivo não encontrado: {file_path}", file=sys.stderr)
        print(
            "Ação: verifique se o caminho especificado para --file está correto.",
            file=sys.stderr,
        )
        return 2

    try:
        raw_resume = read_resume(file_path)
        parser_instance = DeterministicResumeParser()
        draft = parser_instance.parse(raw_resume)
    except UnreadablePdfError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: selecione um PDF com camada de texto exportada ou converta o "
            "documento para texto selecionável (OCR ainda não suportado).",
            file=sys.stderr,
        )
        return 2
    except UnsupportedFileFormatError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: forneça um arquivo no formato PDF (.pdf) ou Word (.docx).",
            file=sys.stderr,
        )
        return 2
    except EmptyDocumentError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: verifique se o arquivo do currículo contém texto e "
            "não está zerado ou em branco.",
            file=sys.stderr,
        )
        return 2
    except ResumeReadError as error:
        print(f"Erro: {error}", file=sys.stderr)
        print(
            "Ação: verifique a integridade do arquivo de currículo e suas permissões de leitura.",
            file=sys.stderr,
        )
        return 2
    except Exception as error:
        print(f"Erro ao processar currículo: {error}", file=sys.stderr)
        print(
            "Ação: verifique o arquivo de entrada e tente novamente.",
            file=sys.stderr,
        )
        return 2

    if arguments.review:
        _present_draft_review(draft)

    if output_path is not None:
        categories_set: set[str] = set()
        for draft_ev in draft.suggested_evidences:
            if draft_ev.suggested_field == "target_categories":
                if isinstance(draft_ev.evidence.subject.value, JobCategory):
                    categories_set.add(draft_ev.evidence.subject.value.value)
                elif isinstance(draft_ev.evidence.subject.value, str):
                    categories_set.add(draft_ev.evidence.subject.value)

        if not categories_set:
            categories_set.add(JobCategory.SOFTWARE_DEVELOPMENT.value)

        ordered_categories = sorted(categories_set)
        profile_dict = {
            "schema_version": 1,
            "id": f"candidate-{file_path.stem}",
            "target_categories": ordered_categories,
        }

        try:
            output_path.write_text(
                json.dumps(profile_dict, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            print(f"Erro ao salvar arquivo de saída: {error}", file=sys.stderr)
            print(
                "Ação: verifique as permissões de escrita no diretório de destino.",
                file=sys.stderr,
            )
            return 2

        print(f"CandidateProfile salvo com sucesso em '{output_path}'.")

    return 0


def _present_draft_review(draft: CandidateProfileDraft) -> None:
    file_name = Path(draft.source_file).name
    print(f"Revisão do CandidateProfileDraft para '{file_name}':")
    print(f"  Resumo do texto: {draft.raw_text_summary}")
    print("  Evidências sugeridas:")
    if draft.suggested_evidences:
        for item in draft.suggested_evidences:
            ev = item.evidence
            prov = f"{ev.provenance.origin} -> {ev.provenance.locator}"
            print(
                f"    - [{item.confidence.upper()}] [{item.suggested_field}] "
                f"{ev.statement} (proveniência: {prov})"
            )
    else:
        print("    - (nenhuma evidência sugerida)")
    print("  Seções não reconhecidas:")
    if draft.unrecognized_sections:
        for sec in draft.unrecognized_sections:
            print(f"    - {sec}")
    else:
        print("    - (nenhuma)")


if __name__ == "__main__":
    raise SystemExit(main())
