# Segundo marco: importação e análise de currículo (PDF/DOCX)

## Problem Statement

Candidatos ao mercado de tecnologia frequentemente possuem seus históricos profissionais, projetos, tecnologias conhecidas e formações armazenados em arquivos de currículo (PDF ou DOCX). O preenchimento manual do `CandidateProfile` em formato JSON é moroso, suscetível a erros de digitação e intimidador para iniciantes.

Ao mesmo tempo, enviar esses arquivos para serviços externos de terceiros ou IAs na nuvem viola o princípio da privacidade do candidato (*local-first* e *privacy-by-design*). Além disso, dependências pesadas de visão computacional ou OCR inviabilizam a execução rápida e leve no ambiente local.

## Solution

Entregar no `buscador-de-vaga` a funcionalidade de importação e extração determinística de currículos em formato PDF e DOCX. 

Através do desacoplamento entre a leitura técnica do documento (`ResumeReader`) e a interpretação semântica das evidências (`ResumeParser`), a aplicação lerá o texto bruto dos arquivos usando `pypdf` e `python-docx`, aplicará regras determinísticas com base na taxonomia de domínio para identificar competências, cargos passados, nível de experiência e idiomas, e gerará um `CandidateProfileDraft` com rastreabilidade explícita (`Provenance`). O candidato poderá revisar e confirmar este rascunho via CLI antes de integrá-lo ao `CandidateProfile` oficial.

PDFs escaneados sem camada de texto serão identificados e rejeitados com uma mensagem acionável de erro (`UnreadablePdfError`), informando a ausência de OCR neste marco.

## User Stories

1. Como Candidate, quero importar meu currículo em formato `.pdf` ou `.docx`, para preencher meu perfil profissional sem digitar dados manualmente em um arquivo JSON.
2. Como Candidate, quero que todo o processamento de parsing do meu currículo seja executado 100% offline no meu computador, garantindo que meus dados pessoais nunca saiam da minha máquina.
3. Como Candidate, quero receber um erro acionável (`UnreadablePdfError`) caso forneça um PDF escaneado (imagem sem texto extraível), sabendo que o suporte a OCR não é oferecido no Marco 2.
4. Como Candidate, quero receber um erro claro (`UnsupportedFileFormatError`) caso forneça um formato de arquivo não suportado (ex: `.txt`, `.png`, `.doc`).
5. Como Candidate, quero que a extração identifique seções de Experiência, Formação, Habilidades, Idiomas e Projetos, para categorizar minhas informações.
6. Como Candidate, quero que cada `Evidence` extraída possua `Provenance` indicando de qual seção/linha do currículo a informação foi obtida, para poder auditar o resultado.
7. Como Candidate, quero visualizar um rascunho (`CandidateProfileDraft`) com todas as evidências sugeridas antes da consolidação final, permitindo aceitar, editar ou rejeitar itens.
8. Como Candidate, quero poder consolidar o rascunho revisado no arquivo `candidate-profile.json` ativo, para que ele seja usado imediatamente na busca e no `MatchAssessment`.
9. Como Maintainer, quero que a leitura técnica dos arquivos (`ResumeReader`) seja completamente separada da lógica de segmentação e extração (`ResumeParser`), para permitir novos leitores sem afetar o parser.
10. Como Maintainer, quero testes unitários com fixtures sintéticas em PDF e DOCX (em diretório de testes ou memória), sem depender de arquivos ou dados reais do usuário.

## Implementation Decisions

- **Modular Monolith Local-First:** Toda a solução será implementada no pacote `src/buscador_de_vaga/resume/` em Python 3.12+.
- **Bibliotecas Selecionadas:**
  - `pypdf` (>=5.0.0, <6) para extração de texto de PDFs.
  - `python-docx` (>=1.1.0, <2) para extração de texto de arquivos `.docx`.
- **Exceções Tipadas (`src/buscador_de_vaga/resume/exceptions.py`):**
  - `UnreadablePdfError`: Disparado quando o PDF tem páginas, mas `pypdf` não consegue extrair texto significativo (sinalizando PDF escaneado).
  - `UnsupportedFileFormatError`: Disparado quando a extensão não é `.pdf` nem `.docx`.
  - `EmptyDocumentError`: Disparado quando o arquivo está com 0 bytes.
- **Seam de Leitura (`ResumeReader`):**
  - `PdfResumeReader`: Abre o PDF com `pypdf`, itera pelas páginas e concatena o texto. Se a contagem final for inferior a 30 caracteres em documentos com páginas, lança `UnreadablePdfError`.
  - `DocxResumeReader`: Abre o DOCX com `python-docx`, itera sobre parágrafos e células de tabelas extraindo texto.
- **Seam de Extração (`ResumeParser`):**
  - `DeterministicResumeParser`: Segmenta o texto bruto por expressões regulares representando seções tradicionais de currículos (PT-BR e EN).
  - Utiliza os dicionários taxonômicos do repositório (`JobCategory`, `Skill`, `Seniority`, `EntryProgram`, `WorkplaceMode`, `Idiomas`) para localizar ocorrências nas seções.
  - Mapeia cada ocorrência em uma `Evidence` vinculada à sua `Provenance`.
- **Rascunho e Revisão (`CandidateProfileDraft`):**
  - O resultado do `ResumeParser` é um `CandidateProfileDraft`.
  - O rascunho pode ser exportado para JSON ou revisado via subcomando CLI `buscar-vagas importar-curriculo --file <caminho> --review`.
  - Após a confirmação, o `CandidateProfileDraft` substitui ou atualiza o `CandidateProfile` local (`candidate-profile.json`).
- **Segurança e Versionamento:**
  - O arquivo `.gitignore` bloqueia diretórios `/resumes/`, arquivos `*.pdf` e `*.docx`.

## Testing Decisions

- **Suíte 100% Offline e Sintética:** Testes criarão arquivos PDF/DOCX sintéticos e efêmeros via fixtures do `pytest` (`tmp_path`) com conteúdos controlados.
- **Testes de Unidade do `ResumeReader`:**
  - Validação de extração de texto em PDF sintético.
  - Teste da exceção `UnreadablePdfError` com um PDF sintético de imagem (sem texto).
  - Validação de extração de texto e tabelas em DOCX sintético.
  - Rejeição de formatos não suportados (`UnsupportedFileFormatError`).
- **Testes de Unidade do `ResumeParser`:**
  - Verificação de segmentação correta de seções (Experiência, Habilidades, Educação).
  - Verificação da extração de habilidades (ex: Python, SQL, Docker) e vinculo de `Provenance`.
  - Verificação do cálculo de grau de confiança (`high`, `medium`, `low`).
- **Testes de Integração da CLI:**
  - Subcomando CLI de importação recebendo `--file` e `--output`.
  - Exibição adequada das mensagens de erro acionáveis (`UnreadablePdfError`).

## Out of Scope

- OCR (Reconhecimento Óptico de Caracteres) para PDFs escaneados ou imagens.
- Uso de LLMs ou APIs pagas/nuvem para parsing.
- Geração automática de currículos em PDF/DOCX (exportação de novos currículos).
- Extração de fotos ou elementos gráficos do currículo.
- Tradução automática de idiomas.

## Further Notes

- As dependências `pypdf` e `python-docx` devem ser adicionadas a `pyproject.toml` na seção de dependências do projeto.
- O parsing determinístico garantirá reprodutibilidade total nos testes e execução instantânea sem custo financeiro nem latência de rede.
