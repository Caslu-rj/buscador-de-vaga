# 0004: Extração Local e Determinística de Currículo (PDF/DOCX)

## Status
Aceito

## Contexto
Para acelerar o preenchimento do `CandidateProfile`, a aplicação precisa importar currículos em formatos populares (`.pdf` e `.docx`). Como o projeto adota rigorosamente o princípio *local-first* e *privacy-by-design*, nenhuma informação contida no currículo do usuário pode ser transmitida para APIs ou serviços externos de terceiros (como OpenAI ou serviços de OCR na nuvem).

Além disso, a aplicação prioriza baixo consumo de recursos e instalação simplificada sem dependências nativas C/C++ pesadas.

## Decisão
Decidimos que a extração de currículos será 100% local e baseada nas bibliotecas Python puras `pypdf` (para PDF) e `python-docx` (para DOCX), aliada a um pipeline de parsing determinístico por regras e taxonomia de domínio.

Principais diretrizes:
1. **`ResumeReader` desacoplado:** A leitura técnica de arquivos PDF (`pypdf`) e DOCX (`python-docx`) é isolada da lógica de extração semântica.
2. **Detecção de PDFs Escaneados:** Caso o `ResumeReader` detecte que o PDF possui páginas mas nenhuma camada de texto extraível, deve lançar a exceção customizada `UnreadablePdfError`, informando ao usuário que OCR ainda não é suportado neste marco.
3. **Parsing Determinístico:** O `ResumeParser` utilizará expressões regulares para segmentação de seções (Experiência, Educação, Habilidades, Idiomas, etc.) e mapeamento de `Evidence` com base nos dicionários taxonômicos do repositório (`JobCategory`, `Skill`, `Seniority`, `EntryProgram`, `Idiomas`).
4. **Rastreabilidade com `Provenance`:** Cada evidência extraída incluirá o local de origem no documento (ex: `resume:curriculo.pdf#section:skills`).

## Consequências
- **Positivas:**
  - Garantia absoluta de privacidade (dados não saem da máquina do usuário).
  - Execução offline rápida sem custo por requisição.
  - Dependências extremamente leves (~3 MB total, sem dependências C).
  - Rastreabilidade ponta a ponta através do objeto `Provenance`.
- **Negativas / Limitações:**
  - PDFs escaneados (sem camada de texto) não serão processados no Marco 2.
  - Layouts não convencionais ou tabelas complexas em PDF podem ter extração imperfeita, exigindo revisão do candidato.
