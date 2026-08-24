"""Parser determinístico para extração de evidências e geração de CandidateProfileDraft."""

import re
from pathlib import Path
from typing import Protocol

from buscador_de_vaga.domain import (
    EntryProgram,
    Evidence,
    EvidenceAssertion,
    JobCategory,
    Provenance,
    RequirementKind,
    RequirementSubject,
    Seniority,
)
from buscador_de_vaga.resume.models import (
    CandidateProfileDraft,
    DraftEvidence,
    RawResumeText,
    ResumeSection,
)

# Mapeamento de títulos de seções conhecidas (PT e EN) para chaves canônicas
_SECTION_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "experiencia_profissional": (
        "experiencia profissional",
        "experiência profissional",
        "experiencia",
        "experiência",
        "experiências",
        "experiencias",
        "historico profissional",
        "histórico profissional",
        "experiência de trabalho",
        "experiencia de trabalho",
        "work experience",
        "professional experience",
        "experience",
        "employment history",
        "work history",
    ),
    "educacao": (
        "formacao academica",
        "formação acadêmica",
        "formacao",
        "formação",
        "educacao",
        "educação",
        "escolaridade",
        "estudos",
        "education",
        "academic background",
        "academic qualification",
        "academic education",
    ),
    "habilidades": (
        "habilidades",
        "competencias",
        "competências",
        "habilidades tecnicas",
        "habilidades técnicas",
        "conhecimentos tecnicos",
        "conhecimentos técnicos",
        "tecnologias",
        "conhecimentos",
        "skills",
        "technical skills",
        "competencies",
        "core competencies",
        "tech stack",
    ),
    "projetos": (
        "projetos",
        "projetos pessoais",
        "projetos relevantes",
        "projetos academicos",
        "projetos acadêmicos",
        "projects",
        "personal projects",
        "relevant projects",
        "academic projects",
    ),
    "cursos": (
        "cursos",
        "cursos extracurriculares",
        "treinamentos",
        "cursos e treinamentos",
        "formacao complementar",
        "formação complementar",
        "courses",
        "extracurricular courses",
        "training",
        "trainings",
    ),
    "certificacoes": (
        "certificacoes",
        "certificações",
        "certificados",
        "certifications",
        "certificates",
    ),
    "idiomas": (
        "idiomas",
        "linguas",
        "línguas",
        "languages",
    ),
}

# Termos taxonômicos de habilidades e seus padrões regex
_SKILL_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": (r"\bpython\b",),
    "java": (r"\bjava\b",),
    "javascript": (r"\bjavascript\b", r"\bjs\b"),
    "typescript": (r"\btypescript\b", r"\bts\b"),
    "sql": (r"\bsql\b",),
    "git": (r"\bgit\b",),
    "linux": (r"\blinux\b",),
    "docker": (r"\bdocker\b",),
    "aws": (r"\baws\b", r"\bamazon web services\b"),
    "azure": (r"\bazure\b", r"\bmicrosoft azure\b"),
    "gcp": (r"\bgcp\b", r"\bgoogle cloud platform\b", r"\bgoogle cloud\b"),
    "react": (r"\breact\b", r"\breactjs\b", r"\breact\.js\b"),
    "flask": (r"\bflask\b",),
    "django": (r"\bdjango\b",),
    "fastapi": (r"\bfastapi\b",),
}

# Padrões para programas de entrada
_ENTRY_PROGRAM_PATTERNS: dict[EntryProgram, tuple[str, ...]] = {
    EntryProgram.INTERNSHIP: (
        r"\bestágio\b",
        r"\bestagiar\b",
        r"\bestagiári[oa]\b",
        r"\binternship\b",
        r"\bintern\b",
    ),
    EntryProgram.APPRENTICESHIP: (
        r"\bjovem aprendiz\b",
        r"\baprendiz\b",
        r"\bapprenticeship\b",
    ),
    EntryProgram.TRAINEE: (r"\btrainee\b",),
}

# Padrões para senioridade
_SENIORITY_PATTERNS: dict[Seniority, tuple[str, ...]] = {
    Seniority.JUNIOR: (r"\bjúnior\b", r"\bjunior\b", r"\bjr\b"),
    Seniority.MID_LEVEL: (r"\bpleno\b", r"\bplenô\b", r"\bmid-level\b", r"\bmid level\b"),
    Seniority.SENIOR: (r"\bsênior\b", r"\bsenior\b", r"\bsr\b"),
}

# Padrões para categorias profissionais
_CATEGORY_PATTERNS: dict[JobCategory, tuple[str, ...]] = {
    JobCategory.SOFTWARE_DEVELOPMENT: (
        r"\bdesenvolv(?:imento|edor|edora)\b",
        r"\bsoftware (?:developer|engineer)\b",
        r"\bprogramad(?:or|ora)\b",
        r"\bbackend\b",
        r"\bfrontend\b",
        r"\bfull\s*stack\b",
    ),
    JobCategory.IT_SUPPORT_INFRASTRUCTURE: (
        r"\banalista de suporte\b",
        r"\bsuporte(?: de ti)?\b",
        r"\bhelpdesk\b",
        r"\bservice desk\b",
        r"\binfraestrutura\b",
        r"\bdevops\b",
    ),
    JobCategory.QUALITY_ASSURANCE: (
        r"\bqa\b",
        r"\bquality assurance\b",
        r"\banalista de qa\b",
        r"\banalista de qualidade\b",
        r"\bsoftware tester\b",
        r"\btester\b",
    ),
    JobCategory.DATA: (
        r"\banalista de dados\b",
        r"\bcientista de dados\b",
        r"\bdata (?:analyst|scientist|engineer)\b",
        r"\bengenheiro de dados\b",
    ),
}

# Padrões para idiomas com níveis
_LANGUAGE_PATTERNS: tuple[str, ...] = (
    r"\b(?:inglês|english)\s+(?:básico|basic|intermediário|intermediate|avançado|advanced|fluente|fluent|nativo|native|b1|b2|c1|c2|a1|a2)\b",
    r"\b(?:espanhol|spanish)\s+(?:básico|basic|intermediário|intermediate|avançado|advanced|fluente|fluent|nativo|native|b1|b2|c1|c2|a1|a2)\b",
    r"\b(?:português|portuguese)\s+(?:nativo|native|fluente|fluent)\b",
)

CONFIDENCE_PRIORITY = {"high": 3, "medium": 2, "low": 1}


class ResumeParser(Protocol):
    """Interface (Protocol) para parsers de currículo."""

    def parse(self, raw_text: RawResumeText) -> CandidateProfileDraft:
        ...


class DeterministicResumeParser:
    """Parser determinístico que segmenta currículos e extrai evidências de forma 100% offline."""

    def parse(self, raw_text: RawResumeText) -> CandidateProfileDraft:
        sections, unrecognized = self._segment_sections(raw_text.text)
        file_name = Path(raw_text.source_file).name
        origin = f"resume:{file_name}"

        raw_evidences: list[DraftEvidence] = []

        for sec in sections:
            for line_no, line_text in sec.lines:
                # 1. Extração de Skills
                for skill_name, patterns in _SKILL_PATTERNS.items():
                    if any(re.search(pat, line_text, re.IGNORECASE) for pat in patterns):
                        confidence = self._get_skill_confidence(sec.name)
                        ev = Evidence(
                            id=f"draft-skill-{skill_name}-{sec.name}-{line_no}",
                            subject=RequirementSubject.skill(skill_name),
                            statement=f"Tecnologia identificada: {skill_name.capitalize()}",
                            assertion=EvidenceAssertion.SUPPORTS,
                            provenance=Provenance(
                                origin=origin,
                                locator=f"section:{sec.name}#line:{line_no}",
                            ),
                        )
                        raw_evidences.append(
                            DraftEvidence(
                                evidence=ev,
                                confidence=confidence,
                                suggested_field="skills",
                            )
                        )

                # 2. Extração de Programas de Entrada (Estágio, Jovem Aprendiz, Trainee)
                for entry_program, patterns in _ENTRY_PROGRAM_PATTERNS.items():
                    if any(re.search(pat, line_text, re.IGNORECASE) for pat in patterns):
                        is_main_sec = sec.name in ("experiencia_profissional", "geral")
                        confidence = "high" if is_main_sec else "medium"
                        ev = Evidence(
                            id=f"draft-entry-{entry_program.value}-{sec.name}-{line_no}",
                            subject=RequirementSubject.entry_program(entry_program),
                            statement=f"Programa de entrada identificado: {entry_program.value}",
                            assertion=EvidenceAssertion.SUPPORTS,
                            provenance=Provenance(
                                origin=origin,
                                locator=f"section:{sec.name}#line:{line_no}",
                            ),
                        )
                        raw_evidences.append(
                            DraftEvidence(
                                evidence=ev,
                                confidence=confidence,
                                suggested_field="entry_program",
                            )
                        )

                # 3. Extração de Senioridade (Júnior, Pleno, Sênior)
                for seniority, patterns in _SENIORITY_PATTERNS.items():
                    if any(re.search(pat, line_text, re.IGNORECASE) for pat in patterns):
                        is_main_sec = sec.name in ("experiencia_profissional", "geral")
                        confidence = "high" if is_main_sec else "medium"
                        ev = Evidence(
                            id=f"draft-seniority-{seniority.value}-{sec.name}-{line_no}",
                            subject=RequirementSubject.seniority(seniority),
                            statement=f"Senioridade identificada: {seniority.value}",
                            assertion=EvidenceAssertion.SUPPORTS,
                            provenance=Provenance(
                                origin=origin,
                                locator=f"section:{sec.name}#line:{line_no}",
                            ),
                        )
                        raw_evidences.append(
                            DraftEvidence(
                                evidence=ev,
                                confidence=confidence,
                                suggested_field="seniority",
                            )
                        )

                # 4. Extração de Categorias Profissionais
                for category, patterns in _CATEGORY_PATTERNS.items():
                    if any(re.search(pat, line_text, re.IGNORECASE) for pat in patterns):
                        is_main_sec = sec.name in ("experiencia_profissional", "geral")
                        confidence = "high" if is_main_sec else "medium"
                        ev = Evidence(
                            id=f"draft-category-{category.value}-{sec.name}-{line_no}",
                            subject=RequirementSubject.job_category(category),
                            statement=f"Categoria de trabalho identificada: {category.value}",
                            assertion=EvidenceAssertion.SUPPORTS,
                            provenance=Provenance(
                                origin=origin,
                                locator=f"section:{sec.name}#line:{line_no}",
                            ),
                        )
                        raw_evidences.append(
                            DraftEvidence(
                                evidence=ev,
                                confidence=confidence,
                                suggested_field="target_categories",
                            )
                        )

                # 5. Extração de Idiomas
                for lang_pat in _LANGUAGE_PATTERNS:
                    match = re.search(lang_pat, line_text, re.IGNORECASE)
                    if match:
                        matched_text = match.group(0)
                        confidence = "high" if sec.name == "idiomas" else "medium"
                        ev = Evidence(
                            id=f"draft-lang-{line_no}",
                            subject=RequirementSubject.skill(matched_text.lower()),
                            statement=f"Idioma identificado: {matched_text}",
                            assertion=EvidenceAssertion.SUPPORTS,
                            provenance=Provenance(
                                origin=origin,
                                locator=f"section:{sec.name}#line:{line_no}",
                            ),
                        )
                        raw_evidences.append(
                            DraftEvidence(
                                evidence=ev,
                                confidence=confidence,
                                suggested_field="languages",
                            )
                        )

        deduplicated = self._deduplicate_evidences(raw_evidences)
        summary = raw_text.text[:100].strip().replace("\n", " ")

        return CandidateProfileDraft(
            source_file=raw_text.source_file,
            raw_text_summary=summary,
            suggested_evidences=tuple(deduplicated),
            unrecognized_sections=tuple(unrecognized),
        )

    def _segment_sections(self, text: str) -> tuple[list[ResumeSection], list[str]]:
        lines = text.splitlines()
        sections: dict[str, list[tuple[int, str]]] = {}
        unrecognized: list[str] = []
        current_section = "geral"

        for line_idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            header_candidate = self._detect_header(line)
            if header_candidate:
                matched_canonical = self._match_section_header(header_candidate)
                if matched_canonical:
                    current_section = matched_canonical
                else:
                    unrecognized.append(header_candidate)
                    current_section = "unrecognized"
                continue

            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append((line_idx, line))

        result_sections = [
            ResumeSection(
                name=sec_name,
                content="\n".join(txt for _, txt in lines_list),
                lines=tuple(lines_list),
            )
            for sec_name, lines_list in sections.items()
        ]
        return result_sections, unrecognized

    def _detect_header(self, line: str) -> str | None:
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line.endswith(":") and len(line) <= 50:
            return line.rstrip(":").strip()

        clean_line = line.strip("*_#-:")
        normalized = clean_line.lower()
        for aliases in _SECTION_HEADER_ALIASES.values():
            if normalized in aliases:
                return clean_line
        return None

    def _match_section_header(self, title: str) -> str | None:
        normalized = title.lower().strip()
        for canonical, aliases in _SECTION_HEADER_ALIASES.items():
            if normalized in aliases:
                return canonical
        return None

    def _get_skill_confidence(self, section_name: str) -> str:
        if section_name == "habilidades":
            return "high"
        elif section_name in ("experiencia_profissional", "projetos", "cursos", "certificacoes"):
            return "medium"
        return "low"

    def _deduplicate_evidences(self, evidences: list[DraftEvidence]) -> list[DraftEvidence]:
        # Agrupa por (kind, resolved_value, section_name) preservando a de maior confiança
        grouped: dict[tuple[RequirementKind, str, str], DraftEvidence] = {}
        for draft_ev in evidences:
            sub = draft_ev.evidence.subject
            sec_name = draft_ev.evidence.provenance.locator.split("#")[0].replace("section:", "")
            key = (sub.kind, sub.resolved_value, sec_name)

            if key not in grouped:
                grouped[key] = draft_ev
            else:
                existing_priority = CONFIDENCE_PRIORITY.get(grouped[key].confidence, 0)
                new_priority = CONFIDENCE_PRIORITY.get(draft_ev.confidence, 0)
                if new_priority > existing_priority:
                    grouped[key] = draft_ev

        return list(grouped.values())
