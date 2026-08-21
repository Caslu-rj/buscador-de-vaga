# Pesquisa de referência: `MadsLorentzen/ai-job-search`

## Escopo e rastreabilidade

Esta análise usa como referência o tag [`v1.6.0`](https://github.com/MadsLorentzen/ai-job-search/releases/tag/v1.6.0), no commit [`ab91c60cc47147d9416f0af758fb5e2d109956ce`](https://github.com/MadsLorentzen/ai-job-search/tree/ab91c60cc47147d9416f0af758fb5e2d109956ce), de 19 de agosto de 2026. Todos os fatos sobre o projeto original abaixo vêm do código, da documentação, do histórico ou da licença do próprio repositório. Os links para arquivos estão fixados nesse commit para que a evidência não mude com `master`.

As decisões propostas para o `buscador-de-vaga` são recomendações de engenharia, não afirmações sobre a situação atual dos portais brasileiros. A viabilidade de Gupy, Indeed, Vagas.com, CIEE, Nube, Programathor e Remotar precisa ser pesquisada individualmente antes de qualquer adapter, com verificação atual de API/feed/páginas públicas, `robots.txt`, termos, autenticação, limites e estabilidade. O próprio original exige essa investigação antes de gerar um portal skill ([`add-portal.md`, linhas 32–46](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L32-L46)).

## Conclusão executiva

O `ai-job-search` é uma excelente referência de **fluxo de produto e guardrails**, mas não deve ser tratado como a arquitetura de uma aplicação tradicional. A implementação principal são especificações Markdown executadas pelo Claude Code; o próprio mantenedor afirma que “the markdown specs ARE the implementation”. Ao redor delas há CLIs TypeScript/Bun por portal, pequenos utilitários Python, templates de documentos e persistência local em JSON, CSV e arquivos Markdown/LaTeX ([`CONTRIBUTING.md`, linhas 16–28](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CONTRIBUTING.md#L16-L28); [`README.md`, linhas 164–230](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L164-L230)).

Para a implementação brasileira, a melhor leitura é:

- **Manter** o ciclo `setup → search/scrape → normalize → deduplicate → rank → shortlist → apply → outcome → interview → upskill`, a explicabilidade, a confirmação humana, a preservação de evidências e a regra de nunca inventar experiência.
- **Adaptar** onboarding, critérios de fit, vocabulário de cargos, localização, remuneração, modalidade, escolaridade, disponibilidade e materiais de candidatura para pessoas entrando no mercado brasileiro de tecnologia.
- **Substituir** regras de negócio espalhadas em prompts, estado em JSON/CSV e CLIs TypeScript isoladas por um core Python tipado, um modelo normalizado, ports/adapters explícitos e SQLite.
- **Não usar** os quatro adapters dinamarqueses nem tornar Claude Code, `.agents/`, `.claude/`, `AGENTS.md` ou `CLAUDE.md` dependências do produto público.
- **Estudar posteriormente** automação de LinkedIn, geração de CV/carta, tracking avançado, entrevistas, upskill, dashboard e integrações de e-mail/Notion. Elas têm valor, mas não pertencem ao primeiro tracer bullet.

O primeiro marco deve terminar em uma CLI funcional e testada que executa `CandidateProfile → uma fonte real autorizada → Job normalizado → deduplicação → MatchAssessment explicável → shortlist`, sem exigir LLM para produzir um resultado correto.

## 1. Arquitetura observada no original

O README define um workflow centrado em Claude Code: `/setup` preenche o perfil, `/scrape` procura vagas e `/apply` avalia, redige, revisa e compila a candidatura ([`README.md`, linhas 40–60](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L40-L60)). A arquitetura efetiva pode ser resumida assim:

```text
documentos do candidato
        │
        ▼
     /setup ───────────────► perfil em Markdown + queries
                                  │
portais ─► CLIs Bun/TS ─► /scrape ├─► seen_jobs.json
                                  │        │
                                  │        ▼
                                  │      /rank ─► score/gaps/shortlist
                                  │
                                  └─────► /apply ─► CV + carta + PDFs
                                                   │
                                                   ├─► tracker CSV
                                                   └─► arquivo da candidatura
                                                            │
                                               ┌────────────┼───────────┐
                                               ▼            ▼           ▼
                                           /outcome    /interview    /upskill
                                               │
                                               └────► calibração no /setup
```

Essa composição é confirmada pelo inventário oficial de diretórios e comandos ([`README.md`, linhas 164–230](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L164-L230)) e pela descrição do lifecycle como feature-complete ([`CONTRIBUTING.md`, linhas 24–28](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CONTRIBUTING.md#L24-L28)).

### Responsabilidades por diretório

| Área original | Responsabilidade observada | Direção para o projeto brasileiro |
|---|---|---|
| `CLAUDE.md` | Perfil agregado do candidato e regras globais de workflow/verificação ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CLAUDE.md#L6-L14)) | **Substituir** por `CandidateProfile` persistido; não usar arquivo de agente como banco de dados. |
| `.claude/commands/` | Casos de uso descritos passo a passo: setup, rank, apply, outcome, interview etc. ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L169-L182)) | **Adaptar** os fluxos como application services Python, mantendo prompts apenas em adapters de IA opcionais. |
| `.claude/skills/job-application-assistant/` | Perfil, comportamento, escrita, avaliação, templates e entrevista ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L183-L194)) | **Adaptar** a metodologia; mover fatos e regras estruturáveis para tipos e políticas versionadas. |
| `.claude/skills/job-scraper/` | Orquestra portal skills, dedupe, estado e apresentação ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L15-L20)) | **Substituir** por `SearchService`, repositories e adapters. |
| `.agents/skills/*-search/` | Integrações autônomas de portais com `SKILL.md`, CLI, parser e testes ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L299-L320)) | **Adaptar** o isolamento e o contrato; implementar módulos Python normais versionados, não Agent Skills locais. |
| `cv/`, `cover_letters/`, `templates/` | Templates e artefatos de candidatura, inicialmente LaTeX ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L203-L210)) | **Estudar posteriormente** atrás de um renderer/template port. |
| `documents/` | Fontes do perfil e arquivo imutável por candidatura ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/documents/README.md#L7-L24)) | **Adaptar** a ideia de provenance e snapshot; armazenar dados privados fora do versionamento. |
| `job_scraper/seen_jobs.json` e `job_search_tracker.csv` | Estado de vagas vistas/rankeadas e pipeline de candidaturas ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L129-L156)) | **Substituir** por SQLite e repositories. |
| `tools/`, `tests/`, `.github/workflows/ci.yml` | Validadores, testes Python, typecheck/test dos CLIs e smoke tests ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.github/workflows/ci.yml#L37-L72)) | **Manter** a disciplina de testes/guardrails, adaptada à stack Python. |

### Decisão arquitetural derivada

O original tem seams úteis entre orquestração, perfil, portal e artefato, mas esses seams são convenções de arquivos. A implementação brasileira deve torná-los interfaces do software:

```text
CLI/UI
  └─ Application Services
       ├─ Candidate Profile
       ├─ Job Search
       ├─ Normalization + Deduplication
       ├─ Matching + Ranking
       └─ Applications (fase posterior)
            │
            ├─ Domain Core (sem HTTP, SQLite ou LLM)
            ├─ Ports (JobSource, Repository, LLMProvider, DocumentRenderer)
            └─ Adapters (portais, SQLite, modelos, exportadores)
```

## 2. Setup e perfil do candidato

### Como funciona no original

`/setup` oferece três entradas convergentes: diretório de documentos, importação de um CV único ou entrevista guiada. O modo de documentos é read-before-write, cruza fontes e procura ser idempotente ([`setup.md`, linhas 32–74](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md#L32-L74)). Ele lê CV, export do LinkedIn, diplomas, referências e candidaturas anteriores; compara datas, cargos, educação e nomes de empregadores antes de propor mudanças ([`setup.md`, linhas 96–168](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md#L96-L168)).

O perfil resultante cobre identidade, localização, idiomas, educação, experiência, projetos, skills, publicações, prêmios e referências ([`01-candidate-profile.md`, linhas 10–73](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/01-candidate-profile.md#L10-L73)). A entrevista também pergunta objetivos, preferências, deal-breakers, salário, deslocamento, cargos, skills pesquisáveis, empresas e portais ([`setup.md`, linhas 261–344](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md#L261-L344)).

Há uma fragilidade importante: `/setup` personaliza arquivos rastreados pelo Git. O comando tenta detectar fork público e avisar antes da escrita, e volta a alertar no final ([`setup.md`, linhas 13–30](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md#L13-L30); [`setup.md`, linhas 392–415](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md#L392-L415)).

### Implementação brasileira

Classificação: **adaptar** o onboarding; **substituir** sua persistência.

Manter:

- múltiplas formas de entrada;
- importação com provenance por fato;
- detecção explícita de conflito entre fontes;
- preview e confirmação antes de gravar inferências;
- reexecução idempotente;
- fatos confirmados como única base para CV, fit e entrevista.

Adaptar o perfil para incluir, sem misturar dimensões diferentes:

- cidade, UF, país e raio/tempo aceitável de deslocamento;
- preferência por remoto, híbrido e presencial;
- disponibilidade de horário e data de início;
- vínculo/contrato aceito (`CLT`, `PJ`, temporário etc.);
- tipo de programa (`internship/estágio`, `trainee`, `apprenticeship/jovem aprendiz`, regular), separado do vínculo;
- instituição, curso, semestre atual e previsão de conclusão;
- elegibilidade acadêmica para estágio;
- faixa de remuneração ou bolsa, sempre com moeda e período (`BRL`, mensal/hora/ano);
- tecnologias, projetos, cursos, certificações, idiomas e nível de evidência;
- categorias de interesse e aliases/sinônimos, em vez de uma lista de títulos literais.

Substituir os vários Markdown personalizados por um `CandidateProfile` estruturado e registros de provenance, deixando exportações legíveis como views. Dados pessoais devem residir em um diretório de dados local ignorado ou fora do checkout e no banco SQLite local; nunca em `AGENTS.md`, `CLAUDE.md`, fixtures ou commits.

O perfil comportamental do original é opcional e aceita PI/DISC/Myers-Briggs ou autoavaliação ([`02-behavioral-profile.md`, linhas 5–35](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/02-behavioral-profile.md#L5-L35)). Para o produto brasileiro, isso deve ser **estudado posteriormente** e nunca atuar como gate automático: evidência textual sobre preferências de trabalho é mais auditável do que tipologias psicológicas inferidas.

## 3. Busca, portal skills, adapters e CLIs

### Orquestração original

`/scrape` carrega `seen_jobs.json`, o tracker CSV e as queries; descobre todo `SKILL.md` sob `.agents/skills/*`, respeita `enabled: false`, executa CLIs em paralelo, usa o formato JSON e continua quando uma integração falha ([`job-scraper/SKILL.md`, linhas 39–86](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L39-L86)). Para detalhes, usa o comando `detail`; WebSearch/WebFetch é fallback quando não há CLI ou ela falha ([`job-scraper/SKILL.md`, linhas 88–107](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L88-L107)).

O portal contract gerado por `/add-portal` exige:

- `search` e `detail`;
- flags comuns, inclusive JSON/table/plain;
- envelope `{meta, results}`;
- pelo menos `id`, `title`, `company`, `location`, `date`, `url`;
- erros JSON em `stderr` com exit code 1;
- backoff para 429/5xx;
- `null` para ausências;
- credenciais apenas em variável de ambiente;
- testes e live smoke test local antes do registro ([`add-portal.md`, linhas 74–118](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L74-L118)).

Um teste de contrato percorre todos os portal CLIs e falha se algum deixar de emitir os cinco campos que `/scrape` consome. Ele foi criado porque Jobnet e Jobdanmark já haviam emitido shapes incompatíveis ([`test_scrape_contract.py`, linhas 1–20 e 53–74](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/tests/test_scrape_contract.py#L1-L74)). Esse é um dos padrões mais valiosos para reaproveitar.

O sistema ainda possui health checks bounded: detecta campos vazios/garbled, compara yield anterior, faz um sentinel probe limitado e trata rate-limit como inconclusivo, não como parser quebrado ([`job-scraper/SKILL.md`, linhas 184–213](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L184-L213)).

### Portal matrix original → Brasil

| Elemento original | Evidência | Classificação | Decisão brasileira |
|---|---|---|---|
| `jobbank-search` | RSS para busca, JSON-LD para detalhe, filtros de região/formação e risco de bloqueio por Cloudflare ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobbank-search/SKILL.md#L22-L73)) | **Não usar** | Preservar apenas padrões de adapter e parser; nenhum endpoint/código de mercado dinamarquês entra no produto. |
| `jobdanmark-search` | API pública; `search`, `detail`, categories, autocomplete e locations; tipos de trabalho dinamarqueses ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobdanmark-search/SKILL.md#L24-L94)) | **Não usar** | A ideia de discovery de taxonomias é útil, mas códigos, categorias e municípios devem ser substituídos. |
| `jobindex-search` | API pública sem autenticação, query textual e detalhe ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobindex-search/SKILL.md#L20-L63)) | **Não usar** | Somente referência de integração simples `search → detail`. |
| `jobnet-search` | BFF REST do portal governamental dinamarquês, filtros e ESCO discovery ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobnet-search/SKILL.md#L25-L91)) | **Não usar** | A separação de taxonomy lookup e search pode inspirar aliases brasileiros; endpoints/códigos não servem ao Brasil. |
| `linkedin-search` | `jobs-guest`, sem login, mas o próprio skill diz que automação contraria os Terms of Service e limita a uso pessoal de baixo volume ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/linkedin-search/SKILL.md#L18-L33)) | **Estudar posteriormente** | Não escolher como primeiro adapter automatizado. Oferecer inicialmente importação de URL/texto; só automatizar após nova análise jurídica/técnica e com limites claros. |
| `freehire-search` | API pública estruturada e tech-first, com skills/seniority/categoria; serviço best-effort sem SLA ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/freehire-search/SKILL.md#L18-L55)) | **Estudar posteriormente** | Validar cobertura e frescor no Brasil. Pode virar fonte complementar, nunca fonte única. |
| `/add-portal` | Reconnaissance, gate de auth/robots/terms, scaffolding, contrato e teste live ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L32-L118)) | **Adaptar** | Transformar em checklist/template de engenharia e contract tests para `PortalAdapter`, não em gerador agentic necessário em runtime. |
| Auto-discovery por diretório e `enabled` | `/scrape` descobre skills sem registro central ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L59-L75)) | **Adaptar** | Usar registry explícito/configurável de adapters Python; discovery mágico por filesystem não deve esconder dependências. |
| WebSearch como fallback | Resultados podem vir de índice desatualizado, e o original registra provenance `cli/websearch` ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L77-L86)) | **Estudar posteriormente** | Não faz parte do core inicial. Se adicionado, deve ser uma `JobSource` distinta, com baixa confiança e provenance explícito. |

### Fontes brasileiras prioritárias

Gupy, Indeed, Vagas.com, CIEE, Nube, Programathor e Remotar **substituem a camada dinamarquesa**, mas ainda não há evidência suficiente nesta pesquisa para ordenar sua viabilidade técnica. Cada uma deve receber um documento de reconnaissance com:

1. superfície pública permitida e termos;
2. API/feed/JSON-LD/HTML observado;
3. identificador e URL canônicos;
4. paginação, filtros, datas e limites;
5. campos disponíveis e ausentes;
6. tratamento de rate-limit e bloqueios;
7. fixtures sanitizadas e testes offline;
8. live smoke test manual, de baixo volume;
9. decisão `go`, `manual-import-only` ou `no-go`.

O primeiro adapter real deve ser escolhido pelo melhor conjunto **acesso legítimo + estabilidade + identificador confiável + descrição completa + facilidade de teste**, e não pela popularidade do portal. Não se deve implementar CAPTCHA, login, proxy para contornar bloqueio, browser fingerprinting ou qualquer bypass. O original também recusa portais auth-walled e subordina qualquer estratégia de fetch aos termos e ao `robots.txt` ([`add-portal.md`, linhas 39–45](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L39-L45)).

## 4. Normalização e modelo de vaga

### Limite do original

O contrato comum de search do original é deliberadamente estreito: `title`, `company`, `location`, `date` e `url`; o teste aceita um superset ([`test_scrape_contract.py`, linhas 31–74](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/tests/test_scrape_contract.py#L31-L74)). Cada portal mantém campos próprios no detalhe. O LinkedIn, por exemplo, acrescenta `description`, `seniority`, `employmentType`, `jobFunction` e `industries` ([`linkedin helpers.ts`, linhas 50–66](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/linkedin-search/cli/src/helpers.ts#L50-L66)); o freehire possui um wire model mais rico, com `skills`, work mode, regiões, países, cidades e enrichment de seniority/categoria/contrato/salário ([`freehire helpers.ts`, linhas 84–145](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/freehire-search/cli/src/helpers.ts#L84-L145)).

Portanto, é uma inferência direta do código que o original possui **normalização mínima de transporte**, não um modelo de domínio unificado e persistente para vagas.

### Proposta brasileira provisória

Classificação: **substituir** por um modelo explícito. Os nomes finais pertencem ao `domain-modeling`, mas a distinção mais importante é entre a oportunidade e sua ocorrência em uma fonte:

```text
Job                         JobOccurrence
---                         -------------
id                          id
title                       job_id
normalized_title            source_id
company                     external_id
description                 source_url
location                    apply_url
work_mode                   published_at
contract_type               deadline
program_type                collected_at
seniority                   raw_payload_hash
requirements                raw_snapshot_ref
compensation                source_metadata
published_at/deadline
```

Uma vaga encontrada no LinkedIn e na página Gupy da empresa pode ser um único `Job` com duas `JobOccurrence`s. Isso evita perder provenance ao deduplicar e permite escolher depois o link de candidatura mais confiável.

Campos recomendados para refinamento:

- identidade interna, `external_id` por fonte e requisition ID quando houver;
- título original e título/categoria normalizados;
- empresa original e canônica;
- descrição em texto, idioma e hash do conteúdo;
- localização estruturada (`city`, `state`, `country_code`) e texto original;
- `work_mode`: remote/hybrid/onsite/unknown;
- `contract_type`: CLT/PJ/temporary/other/unknown;
- `program_type`: regular/internship/trainee/apprenticeship/unknown;
- senioridade e faixa de experiência;
- requisitos obrigatórios, desejáveis, formação, elegibilidade acadêmica, horário e disponibilidade;
- compensação com mínimo, máximo, moeda, período, natureza salário/bolsa e texto original;
- benefícios;
- publicação, deadline e coleta como instantes distintos;
- lista de todas as fontes, payload/snapshot bruto e versão do normalizador.

Regras importantes:

- `unknown` não é `false`, zero nem “não se aplica”;
- campos derivados sempre guardam provenance e versão da regra/modelo;
- raw payload não entra no domínio e nunca é executado;
- enums internos não devem repetir o vocabulário de um portal;
- datas e dinheiro não devem ser armazenados como texto sem unidade/locale;
- aliases de cargo pertencem a `JobCategory`/taxonomy, não ao parser de cada portal.

## 5. Deduplicação

O original elimina uma entrada quando URL ou `company+title` já aparece em `seen_jobs.json`, ou quando `company+role` já está no tracker ([`job-scraper/SKILL.md`, linhas 109–112](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L109-L112)). Dentro de uma execução, também consolida mass postings com descrição substancialmente igual e variação apenas de local/título ([`job-scraper/SKILL.md`, linhas 113–117](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L113-L117)).

Classificação: **adaptar**, ampliando em camadas conservadoras:

1. mesma fonte + mesmo `external_id` → mesma ocorrência;
2. URL canônica ou requisition ID iguais → provável mesma ocorrência;
3. empresa canônica + título normalizado + local/modalidade + janela temporal → candidato a mesmo `Job`;
4. hash exato da descrição normalizada → forte evidência;
5. similaridade textual/semântica acima de limiar, com restrições de empresa e tempo → candidato a merge;
6. incerteza → manter separado e registrar possível duplicata, evitando falso merge.

O merge deve preservar todas as `JobOccurrence`s e seus campos originais. Variações genuínas por cidade, turno ou requisition ID não podem ser achatadas só porque o texto é parecido. A deduplicação deve ser determinística, versionada e coberta por testes de pares positivos e negativos.

## 6. Fit e ranking

### Modelo original

Antes do score, o original aplica gates de elegibilidade/work rights e idioma ([`04-job-evaluation.md`, linhas 9–47](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md#L9-L47)). Depois avalia:

- Technical Skills;
- Experience Match, pela natureza da função e não pelo título literal;
- Behavioral/Culture Fit;
- Location & Logistics como pass/fail/flag;
- Career Alignment & Motivation;
- salary benchmark opcional ([`04-job-evaluation.md`, linhas 49–144](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md#L49-L144)).

Os pesos são Technical 30%, Experience 25%, Behavioral 15% e Career Alignment 30%; location não é ponderado. Os bands vão de Strong Fit (75+) a Poor Fit (<30) ([`04-job-evaluation.md`, linhas 146–195](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md#L146-L195)).

Há dois níveis úteis de decisão:

- `/scrape` produz sinal rápido high/medium/low ([`job-scraper/SKILL.md`, linhas 119–127](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L119-L127));
- `/rank` faz triagem em lote, com agentes paralelos, pesos, strengths, gaps, vetoes e deadline, mas deixa `/apply` como avaliação autoritativa mais profunda ([`rank.md`, linhas 1–5 e 36–79](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/rank.md#L1-L79)).

### Adaptação brasileira

Classificação: **manter** explicabilidade, gates e dois níveis de avaliação; **substituir** pesos fixos e score produzido diretamente por LLM.

Dimensões candidatas para o primeiro modelo:

- categoria/função e aliases de cargo;
- senioridade e natureza entry-level;
- requisitos obrigatórios;
- skills/tecnologias desejáveis;
- experiência e projetos transferíveis;
- formação, semestre e elegibilidade para estágio;
- localização e modalidade;
- disponibilidade e horário;
- vínculo/programa aceito;
- idioma explicitamente exigido;
- oportunidades de aprendizado/crescimento.

Separar três coisas no resultado:

1. **gates**: impeditivos objetivos e comprováveis;
2. **score dimensions**: contribuições ponderadas com evidência;
3. **flags**: incertezas ou possíveis impeditivos que exigem decisão humana.

O `MatchAssessment` deve guardar a versão da política, score total, breakdown, requisitos atendidos, gaps, blockers/flags e evidências (`profile_fact_id`, `requirement_id`, trecho da vaga). Não esconder gaps e não criar experiência continuam sendo invariantes.

O LLM pode ajudar, por adapter, a extrair requisitos de texto livre, mapear sinônimos ou produzir explicações. O core de scoring deve consumir dados estruturados e funcionar com políticas determinísticas. Assim, trocar fornecedor/modelo ou desligar IA não reescreve o domínio e não torna os testes não determinísticos.

Os pesos originais não devem ser copiados: `Behavioral Fit` é particularmente difícil de sustentar com evidência pública e pode introduzir viés. A primeira versão deve privilegiar critérios observáveis e versionar qualquer mudança de pesos para que scores antigos continuem interpretáveis.

## 7. CV, carta e material de candidatura

O `/apply` original:

1. trata a vaga como input não confiável;
2. avalia fit e pede confirmação antes de redigir;
3. cria CV e carta;
4. envia os drafts inline a um reviewer em contexto novo;
5. audita cada fato contra fontes do perfil;
6. revisa, compila e inspeciona PDFs;
7. verifica a camada de texto para ATS;
8. registra tracker e snapshot da vaga ([`apply.md`, linhas 21–103](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L21-L103); [`apply.md`, linhas 107–203](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L107-L203)).

O fluxo impõe dois pages para o CV e uma para a carta, usa `lualatex`/`xelatex`, inspeciona layout e executa `pdftotext` quando disponível ([`apply.md`, linhas 207–291](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L207-L291)). Ele também trata campos livres de formulário como terceiro artefato opcional ([`apply.md`, linhas 346–352](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L346-L352)).

Classificação: **estudar posteriormente**, preservando desde já as invariantes:

- confirmação humana antes de gerar material;
- factual grounding e provenance de cada claim;
- toda lacuna continua explícita;
- snapshot da descrição que originou o documento;
- revisão separada do draft;
- validação do output final, não apenas do template-fonte;
- nenhuma candidatura ou mensagem enviada automaticamente.

Adaptar para pt-BR, terminologia brasileira e perguntas de formulário. A regra rígida de duas/uma páginas e a dependência de LaTeX devem virar configuração de renderer/template, não regra do domínio. O futuro port `DocumentRenderer` pode suportar HTML/PDF, Typst, LaTeX ou outro toolchain; ATS-check e limites pertencem ao template/política escolhidos.

## 8. Tracking, outcomes e aprendizagem com resultados

O original cria `job_search_tracker.csv` com colunas para data, empresa, setor, cargo, canal, status, contato, fit, notas, documentos, fonte e deadline. Seus status canônicos incluem `drafted`, `applied`, `interview`, `offer`, `hired`, `rejected`, `no_response`, `offer_declined` e `withdrawn` ([`outcome.md`, linhas 28–60](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/outcome.md#L28-L60)). O comando arquiva os documentos efetivamente enviados, a vaga e um `outcome.md`, mantendo histórico append-only e entregando a calibração de volta ao `/setup` ([`outcome.md`, linhas 113–160](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/outcome.md#L113-L160)).

O histórico mostra uma lição arquitetural importante: o tracker CSV e o arquivo `outcome.md` possuíam enums diferentes, e seis comandos repetiam o vocabulário de status com grafias inconsistentes; isso causou bugs no dashboard e Gmail sync até a centralização ([`CHANGELOG.md`, linhas 479–503](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L479-L503)).

Classificação: **adaptar** o lifecycle e o arquivo imutável; **substituir** CSV/Markdown como estado autoritativo.

Modelo sugerido para SQLite:

- `Application`: candidatura a um `Job`, canal, data de submissão e estado atual;
- `ApplicationEvent`: transições e notas datadas append-only;
- `ApplicationArtifact`: CV, carta/respostas e snapshot da vaga com hash;
- `Interview`: etapa, agenda e feedback;
- `Outcome`: resolução final;
- uma única máquina de estados/enum compartilhada por todos os readers/writers.

O feedback pode alimentar calibração, mas somente após confirmação humana e mantendo a amostra visível. Duas rejeições não provam causalidade; são sinal para análise, não autorização para alterar silenciosamente a política de ranking.

Follow-up, Gmail, Notion e dashboard ficam para fases posteriores. Se implementados, devem manter a postura do original: drafts nunca são enviados automaticamente, no máximo dois follow-ups silenciosos e nenhuma claim nova fora do material submetido ([`outcome.md`, linhas 86–109 e 186–195](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/outcome.md#L86-L109)).

## 9. Entrevistas e skill gaps/upskill

### Entrevistas

`/interview` parte de uma candidatura real, lê a vaga e os documentos que o entrevistador recebeu, usa feedback de rounds anteriores, pesquisa a empresa e monta perguntas, bridges honestos para gaps, mapeamento STAR e mock interview ([`interview.md`, linhas 22–85](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/interview.md#L22-L85)).

Classificação: **manter** o conceito e **estudar posteriormente** a implementação. O prep pack futuro deve ser derivado do snapshot da candidatura, nunca do perfil atual se ele divergir do que foi enviado. Respostas STAR precisam referenciar fatos comprovados, e novas lembranças confirmadas devem voltar ao perfil com provenance.

### Skill gaps e upskill

`/upskill` combina tracker e vagas rankeadas com score ≥45, prefere gaps persistidos pelo `/rank`, deduplica por empresa+cargo e pondera gaps pelo inverso do fit; depois adiciona síntese de domínio/soft/tooling/credenciais e cria heatmap/plano de estudo ([`upskill/SKILL.md`, linhas 14–70](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/upskill/SKILL.md#L14-L70); [`upskill/SKILL.md`, linhas 72–115](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/upskill/SKILL.md#L72-L115)).

Classificação: **adaptar** o modelo de `SkillGap` e **estudar posteriormente** recomendações de estudo.

Para o Brasil, gaps devem ser ocorrências ligadas a requisitos reais, com frequência, obrigatoriedade, categoria de vaga, confidence e evidência. Não deixar vagas ruins dominarem o plano só porque `(100 - fit)` é alto; a população deve ser limitada a categorias desejadas e vagas que o candidato realmente consideraria. O primeiro marco apenas expõe gaps por vaga. Heatmap histórico, recursos e trilhas vêm depois.

## 10. Sistema de skills e independência do produto

O original separa `.claude/skills` como orquestração canônica e `.agents/skills` como portal skills portáteis. O `AGENTS.md` raiz é um thin pointer para evitar duplicação ([`AGENTS.md`, linhas 9–19](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/AGENTS.md#L9-L19)). A política upstream mantém Claude Code como runtime de referência e oferece os portal skills portáteis para outros agentes ([`CONTRIBUTING.md`, linhas 53–65](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CONTRIBUTING.md#L53-L65)).

No `buscador-de-vaga`, `.agents/`, `skills-lock.json`, `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md` e `docs/agents/` são locais e não versionados por decisão do projeto. Logo:

- Agent Skills podem orientar **o desenvolvimento**, não implementar o runtime público;
- portal adapters pertencem ao pacote Python versionado;
- regras de domínio pertencem a código/documentação pública (`CONTEXT.md`, ADRs, specs e testes);
- um clone limpo deve instalar e executar sem qualquer arquivo local de agente;
- prompts de LLM, se necessários, são resources do adapter e não substituem invariantes em código.

Classificação do sistema de skills original: **não usar como dependência de produto**; **adaptar como inspiração para modularidade e progressive disclosure**.

## 11. Stack: original versus recomendação brasileira

O original exige Claude Code, Python 3.10+, Bun, uma distribuição LaTeX e opcionalmente `pdftotext` ([`README.md`, linhas 62–68](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L62-L68)). Seus adapters são TypeScript executados por Bun; os dois exemplos globais têm zero runtime dependencies, enquanto os dinamarqueses usam bibliotecas como `@bunli/core`, `zod` e parsers HTML. A CI roda Python 3.12, `unittest`, lint/guard scripts, compilação LaTeX e `bun typecheck/test`, sem requisições live a portais ([`.github/workflows/ci.yml`, linhas 1–24 e 154–195](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.github/workflows/ci.yml#L1-L24)).

| Tema | Original | Recomendação inicial | Classificação |
|---|---|---|---|
| Runtime principal | Claude Code + Markdown | Python 3.12+ como biblioteca/aplicação | **Substituir** |
| Modelos | Markdown, JSON/CSV e interfaces TS locais | tipos Python; entidades de domínio simples e validação Pydantic nas fronteiras | **Substituir** |
| Portais | TypeScript/Bun por skill | adapters Python atrás de ports pequenos | **Substituir** |
| HTTP/parsing | `fetch`, regex/parser por portal | cliente HTTP explícito, timeouts/backoff e parser isolado por adapter | **Adaptar** |
| Persistência | JSON, CSV e pastas | SQLite + repository interfaces + migrations | **Substituir** |
| CLI | comandos Claude e CLIs por portal | CLI fina sobre application services | **Substituir** |
| IA | Claude embutido no workflow | `LLMProvider` opcional e intercambiável | **Substituir** |
| Testes | `unittest` + Bun tests/fixtures | `pytest`, fixtures/mocks HTTP e contract tests | **Adaptar** |
| Qualidade | scripts próprios + TS typecheck | Ruff + Pyright ou mypy; escolha única em ADR | **Adaptar** |
| CV/PDF | LaTeX + poppler | renderer opcional em fase posterior | **Estudar posteriormente** |
| Browser automation | não é o caminho normal | Playwright somente quando um portal específico permitir e justificar | **Estudar posteriormente** |
| API/web UI | inexistente | não adicionar no primeiro tracer bullet | **Não usar agora** |

Recomendação de simplicidade: o core não deve depender de Pydantic, SQLAlchemy, HTTP client, LLM SDK ou framework de CLI. Pydantic faz sentido nas fronteiras de configuração/payload; SQLite é a primeira persistência. A escolha entre `sqlite3` e SQLAlchemy/Alembic deve ser registrada em ADR depois de fechar aggregates e consultas, sem introduzir ORM apenas por antecipação.

## 12. Persistência, privacidade e segurança

O original ignora tracker, salary data, documentos, candidaturas, relatórios, secrets e estado do scraper ([`.gitignore`, linhas 21–35 e 57–105](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.gitignore#L21-L35)). Sua threat model reconhece o risco central: um LLM com acesso a arquivos lê conteúdo web não confiável ao lado de dados pessoais. As proteções por instrução reduzem risco, mas não são sandbox ([`SECURITY.md`, linhas 9–17](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SECURITY.md#L9-L17)).

Classificação: **manter e fortalecer**.

Requisitos para a implementação brasileira:

- banco, documentos importados, raw payloads, artefatos e `.env` nunca versionados;
- fixtures só com dados sintéticos/sanitizados;
- secrets por environment/config provider, nunca flag de CLI, log ou banco em texto claro;
- anúncio é data: remover scripts/markup ativo, não executar código e não seguir instruções do conteúdo;
- adapters só acessam hosts/endpoints previstos; links encontrados na descrição não viram fetch automático;
- raw snapshot imutável com hash e provenance;
- logs sem PII e sem corpo integral por padrão;
- IA recebe o mínimo de dados necessário e somente por um adapter autorizado;
- nenhum auto-apply, mensagem, e-mail ou upload no primeiro escopo;
- testes de adapters são offline; live smoke tests são manuais, limitados e explicitamente autorizados.

## 13. Elementos especificamente dinamarqueses

| Elemento | Original | Decisão brasileira | Classificação |
|---|---|---|---|
| Portais | Jobbank, Jobdanmark, Jobindex, Jobnet ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md#L196-L202)) | Gupy/Indeed/Vagas/CIEE/Nube/Programathor/Remotar após reconnaissance | **Substituir** |
| Geografia | regiões, municípios e códigos postais dinamarqueses específicos ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobnet-search/SKILL.md#L49-L61)) | cidade + UF + país + modalidade + restrição de deslocamento | **Substituir** |
| Tipos de vaga | `Fuldtidsjob`, `Studiejob`, `Praktikplads`, `Graduate/trainee` etc. ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobbank-search/SKILL.md#L47-L60)) | vínculo e programa separados: CLT/PJ/temporário + estágio/trainee/jovem aprendiz/regular | **Substituir** |
| Idioma de documento | CV configurável; carta acompanha Danish/English da vaga ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L86-L101)) | pt-BR default, mantendo idioma da vaga como configuração explícita | **Adaptar** |
| Eligibility gate | cidadania/residência, permit e security clearance ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md#L9-L31)) | work authorization genérico; para entry-level brasileiro, priorizar matrícula/semestre, jornada, formatura e localização | **Adaptar** |
| Salário | formato genérico, mas fuzzy matching trata caracteres/sufixos nórdicos e exemplos em DKK ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/tools/README_SALARY_TOOL.md#L9-L16)) | BRL, salário/bolsa, período, benefícios e normalização de nomes empresariais brasileiros | **Substituir** |
| Contato pré-candidatura | recomenda considerar ligação para dúvidas substantivas ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md#L197-L217)) | não assumir como prática universal; oferecer só quando houver contato e pergunta real | **Adaptar** |
| LaTeX e page counts | CV exatamente 2 páginas e carta 1 página ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L226-L251)) | template/limites configuráveis, validados contra ATS e estágio de carreira | **Estudar posteriormente** |

## 14. Matriz consolidada de decisão

| Elemento | Original | Brasil | Classificação |
|---|---|---|---|
| Lifecycle completo | Comandos conectados do setup ao aprendizado | Preservar como roadmap, por incrementos verticais | **Manter** |
| Local-first | Dados e artefatos locais | Aplicação local e SQLite inicialmente | **Manter** |
| Confirmação humana | Antes de escrever/aplicar e ao resolver conflitos | Tornar regra de use case | **Manter** |
| Honesty/factual grounding | Claims só a partir do perfil | Provenance tipada e auditável | **Manter** |
| Onboarding em três caminhos | documentos, CV ou entrevista | CV/import/manual primeiro; outros incrementais | **Adaptar** |
| Perfil Markdown | vários arquivos personalizados | `CandidateProfile` + facts/provenance | **Substituir** |
| Categorias por função | queries agrupam função e títulos variantes ([fonte](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/search-queries.md#L24-L68)) | taxonomy `JobCategory` com aliases pt-BR/en | **Adaptar** |
| Portal skill isolado | pasta, CLI e testes próprios | adapter Python isolado + contract tests | **Adaptar** |
| Contrato `search/detail` | shape mínimo comum | ports tipados + `SourceJob` e `JobOccurrence` | **Adaptar** |
| Health/fail-soft | erro de uma fonte não aborta busca | resultados parciais + telemetry/health | **Manter** |
| Portais dinamarqueses | quatro demos | nenhum no produto | **Não usar** |
| Fontes brasileiras | ausentes do upstream | adapters por pesquisa e tracer bullets | **Substituir** |
| LinkedIn automatizado | endpoint guest com warning de ToS | importação manual primeiro | **Estudar posteriormente** |
| WebSearch fallback | fallback com baixa confiança | possível adapter separado | **Estudar posteriormente** |
| Normalização mínima | cinco campos comuns | modelo de domínio rico e versionado | **Substituir** |
| Dedupe URL/empresa+título | exato + mass-posting | camadas exatas e similares preservando ocorrências | **Adaptar** |
| Quick fit + deep fit | scrape sinaliza; rank/apply aprofundam | triagem determinística + avaliação detalhada | **Manter** |
| Pesos 30/25/15/30 | rubric global | política brasileira testável/versionada | **Substituir** |
| Behavioral fit automático | dimensão de 15% | não pontuar sem evidência confiável | **Não usar inicialmente** |
| Gates | eligibility, idioma, localização | estágio/formação, horário, modalidade, idioma, blockers explícitos | **Adaptar** |
| LLM no scoring | agentes leem e pontuam texto | LLM opcional para extração/semântica; regra no core | **Substituir** |
| `seen_jobs.json` | estado de coleta/rank | SQLite | **Substituir** |
| Tracker CSV | pipeline de candidaturas | aggregates e eventos em SQLite | **Substituir** |
| Arquivo da candidatura | snapshot do enviado | preservar conceito/hashes | **Adaptar** |
| Drafter-reviewer | dois contextos e revisão | fase posterior, provider-agnostic | **Estudar posteriormente** |
| ATS/PDF loop | LaTeX + poppler | renderer/plugin posterior | **Estudar posteriormente** |
| Outcome/calibração | resultado real volta ao setup | feedback confirmado e versionado | **Adaptar** |
| Interview prep | snapshot + feedback + STAR | fase posterior | **Estudar posteriormente** |
| Upskill | heatmap de gaps e recursos | fase posterior, baseado em gap evidence | **Estudar posteriormente** |
| Agent Skills como runtime | implementação central | somente tooling local do desenvolvedor | **Não usar** |
| CI sem live portal | fixtures/typecheck/test offline | pytest/contract tests offline + smoke manual | **Manter** |
| Prompt-injection boundary | posting é data, não instrução | sanitização + boundaries técnicas e de prompt | **Manter e fortalecer** |

## 15. Lacunas e inconsistências verificadas no original

Estas lacunas não invalidam o valor do projeto como referência; elas mostram por que a implementação brasileira deve adotar contratos executáveis, identidade estável e testes de fronteira desde o primeiro incremento.

### 15.1 O contrato declarado não é o contrato executável

O gerador `/add-portal` declara um contrato uniforme: `search` e `detail`, `meta.count`, `meta.page` e, por resultado, `id`, `title`, `company`, `location`, `date` e `url` ([`add-portal.md`, linhas 74–85](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L74-L85)). Os adapters entregues, porém, não obedecem integralmente a esse shape:

- Jobdanmark expõe `slug`, não `id`, e usa `meta.currentPage`/`meta.totalItems` ([normalização, linhas 54–81](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobdanmark-search/cli/src/commands/search.ts#L54-L81), [meta, linhas 158–171](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobdanmark-search/cli/src/commands/search.ts#L158-L171));
- Jobnet expõe `jobAdId` e `meta.totalJobAdCount`/`meta.pageNumber` ([`search.ts`, linhas 82–131](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobnet-search/cli/src/commands/search.ts#L82-L131));
- Jobbank limita o envelope a `meta.total` ([`search.ts`, linhas 155–164](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobbank-search/cli/src/commands/search.ts#L155-L164)).

O teste cross-portal não detecta essa divergência: ele deriva e procura somente `title`, `company`, `location`, `date` e `url`, por inspeção textual do source code, sem validar JSON em runtime, tipos, nullability, `id` ou `meta` ([`test_scrape_contract.py`, linhas 31–74](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/tests/test_scrape_contract.py#L31-L74)). **Decisão: adaptar.** No Brasil, `JobSource` deve devolver objetos tipados; cada fixture deve passar pelo parser real e pelo mesmo contract test comportamental. Campos específicos ficam em `source_metadata`, sem deformar o contrato canônico.

### 15.2 Drift de integração, documentação e testes

- A documentação do Jobindex ainda descreve `GET /jobsoegning.json` e `result_list_box_html` ([README do CLI, linhas 32–40](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobindex-search/cli/README.md#L32-L40)), mas o código registra que o endpoint passou a retornar `204` e agora extrai `var Stash` da página HTML ([`helpers.ts`, linhas 80–115](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.agents/skills/jobindex-search/cli/src/helpers.ts#L80-L115)). **Decisão: adaptar.** Endpoint, parser, fixture e observação de provenance devem evoluir juntos; uma mudança de parser exige atualização documental na mesma alteração.
- `/add-portal` manda gerar um pequeno teste live e exige uma consulta real antes do registro ([linhas 87–118](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L87-L118)), enquanto a CI deliberadamente exclui live portal tests ([`ci.yml`, linhas 10–14](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.github/workflows/ci.yml#L10-L14)) e executa qualquer `*.test.ts` descoberto como fixture/mock ([linhas 154–195](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.github/workflows/ci.yml#L154-L195)). O mesmo gerador declara `allowed-tools` com `skills/<name>` embora a árvore e a descoberta da CI usem `.agents/skills/<name>` ([`add-portal.md`, linhas 87–93](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md#L87-L93), [`ci.yml`, linhas 154–185](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.github/workflows/ci.yml#L154-L185)). **Decisão: não reutilizar o gerador sem revisão.** Separar testes offline obrigatórios de smoke tests live, manuais e explicitamente marcados.

### 15.3 Privacidade declarada versus comportamento real do Git

`SECURITY.md` afirma que o perfil preenchido é gitignored ([linhas 9–17](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SECURITY.md#L9-L17)), mas `.gitignore` não inclui `CLAUDE.md` nem os arquivos de perfil ([linhas 21–35](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.gitignore#L21-L35)). O próprio setup reconhece corretamente que `/setup` grava dados pessoais em arquivos versionados e que um fork público os expõe ([`SETUP.md`, linhas 163–166](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SETUP.md#L163-L166) e [linha 301](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SETUP.md#L301)). **Decisão: substituir.** O produto brasileiro deve guardar perfil e documentos fora da árvore versionada por padrão e ter um teste automatizado que prove, com `git check-ignore`, quais paths sensíveis são ignorados. Documentação nunca deve prometer uma proteção que o repositório não aplica.

### 15.4 Identidade de candidatura e artefatos

- `/apply` permite uma nova linha para a mesma empresa e função quando candidaturas anteriores estão encerradas, mas arquiva em `documents/applications/<company>_<role>/job_posting.md`; o próprio comando reconhece que a recandidatura colide e mantém o anúncio antigo ([`apply.md`, linhas 320–342](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L320-L342)). **Decisão: substituir.** `Application` precisa de ID próprio; snapshots e outcomes devem ser indexados por esse ID, nunca apenas por slug de empresa/função.
- `/add-template` aceita `.tex`, `.typ` ou outro toolchain e define extensão/compile command no manifest ([linhas 55–85](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-template.md#L55-L85)), mas a estrutura de documentos e `/outcome` continuam procurando nomes `.tex` fixos ([`documents/README.md`, linhas 17–22](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/documents/README.md#L17-L22), [`outcome.md`, linhas 113–140](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/outcome.md#L113-L140)). **Decisão: adaptar posteriormente.** Artefatos precisam de metadados renderer-neutral (`kind`, `media_type`, `source_format`, `path`, `hash`, `created_at`).

### 15.5 Limites operacionais e vazamento de locale

O `/scrape` é uma execução interativa best-effort: por padrão consulta só as três categorias prioritárias, restringe a 14 dias, limita cada chamada a cerca de 20 itens e tolera falhas parciais ([`job-scraper/SKILL.md`, linhas 45–75](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md#L45-L75)). Não há scheduler, daemon, cursor durável nem garantia de cobertura exaustiva. **Decisão: manter o fail-soft, adaptar as garantias.** O primeiro tracer bullet pode ser manual, mas deve registrar janela, paginação/cursor, cobertura observada e motivo de interrupção; polling agendado fica para marco posterior.

Apesar da proposta de uso fora da Dinamarca, `/apply` classifica o idioma do anúncio apenas como Danish ou English ([linhas 21–29](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L21-L29)) e codifica a carta como Danish/English ([linhas 94–101](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md#L94-L101)). **Decisão: substituir.** Idioma deve ser um código BCP 47 aberto, com `pt-BR` como preferência configurável, jamais uma enum binária herdada.

## 16. Licença MIT e reutilização

O repositório declara licença MIT, copyright © 2026 Mads Lorentzen. Ela concede permissão para usar, copiar, modificar, combinar, publicar, distribuir, sublicenciar e vender cópias, desde que o aviso de copyright e o texto de permissão sejam incluídos em todas as cópias ou porções substanciais; o software é fornecido sem garantias ([`LICENSE`, linhas 1–20](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/LICENSE#L1-L20)).

Implicações práticas, sem constituir aconselhamento jurídico:

- ideias, lifecycle e padrões podem inspirar uma implementação própria;
- se código, prompts, templates ou documentação substanciais forem copiados/adaptados diretamente, preservar o aviso e o texto MIT junto da distribuição;
- registrar origem, arquivo e commit de qualquer trecho reutilizado;
- uma política segura é manter `THIRD_PARTY_NOTICES.md` e a licença original para componentes copiados, além da licença escolhida para este projeto;
- citar no README que o projeto foi inspirado por `MadsLorentzen/ai-job-search`, mesmo quando a implementação for própria;
- auditar separadamente licenças de fonts/assets/dependências antes de copiar templates ou binários; a existência da licença raiz não elimina essa verificação;
- preferir implementação independente dos comportamentos, como solicitado, e copiar somente onde houver benefício claro.

Até esta etapa, a recomendação é **não copiar código substancial**: usar o original como referência funcional e de testes/guardrails.

## 17. Histórico e lições de manutenção

O repositório saiu do commit de [initial release em 20 de março de 2026](https://github.com/MadsLorentzen/ai-job-search/commit/c66d599d7530ef6708aa107ffd2c3e0ed5af9478) para releases versionadas; o changelog trata releases como checkpoints revisados e recomenda tags em vez de `master` ([`CHANGELOG.md`, linhas 1–14](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L1-L14)). O baseline `v1.0.0` já continha todo lifecycle, portal skills, version markers, guardrails e suporte cross-runtime ([`CHANGELOG.md`, linhas 860–884](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L860-L884)).

Três incidentes documentados são especialmente relevantes para o projeto brasileiro:

1. **Drift entre adapters:** a release 1.6 adicionou teste cross-portal após campos obrigatórios sumirem de outputs reais ([`CHANGELOG.md`, linhas 18–39](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L18-L39)). Lição: contract tests desde o primeiro adapter.
2. **Vocabulário duplicado de status:** grafias divergentes quebraram readers diferentes ([`CHANGELOG.md`, linhas 479–503](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L479-L503)). Lição: uma única enum/state machine no domínio.
3. **Arquivos sensíveis em caminhos inesperados:** relatórios de gaps deixaram de ser ignorados porque paths relativos de skill resolviam em outra profundidade ([`CHANGELOG.md`, linhas 443–455](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md#L443-L455)). Lição: diretório de dados explícito, testes de ignore e nenhum dado pessoal dentro de árvores de tooling.

## 18. Primeiro tracer bullet recomendado

### Escopo

```text
perfil mínimo do candidato
        ↓
SearchRequest + um adapter real pesquisado/autorizado
        ↓
SourceJob
        ↓
normalização para Job + JobOccurrence
        ↓
persistência SQLite
        ↓
deduplicação preservando fontes
        ↓
MatchAssessment determinístico e explicável
        ↓
shortlist na CLI
```

### Incluído

- pacote Python tipado;
- `CandidateProfile` mínimo com localização, categorias, skills, formação e preferências;
- taxonomy inicial para Desenvolvimento, TI/Suporte/Infra, Sistemas, QA e Dados, com aliases pt-BR/en;
- ports de `JobSource` e repositories;
- uma integração real escolhida após reconnaissance;
- fixtures sanitizadas do payload real;
- normalizador, dedupe, scorer e CLI;
- SQLite local;
- testes de domínio, contract, parser, dedupe e ranking;
- Ruff e um type checker;
- configuração e dados pessoais ignorados.

### Fora do primeiro marco

- CV/carta/PDF;
- auto-apply;
- browser automation;
- LinkedIn automatizado;
- múltiplos portais simultâneos;
- entrevistas, tracking completo, outcome, upskill e dashboard;
- API web e interface gráfica;
- dependência obrigatória de LLM.

### Critérios de aceitação

1. testes rodam sem rede;
2. smoke test live é manual e limitado;
3. toda vaga mostra fonte, URL, data de coleta e campos desconhecidos honestamente;
4. duas ocorrências deduplicadas continuam preservadas;
5. score exibe breakdown, matches, gaps, flags e blockers;
6. resultado correto não depende de LLM;
7. uma falha do adapter produz erro tipado e não corrompe estado;
8. nenhum dado pessoal aparece em `git status`;
9. adicionar um segundo adapter não exige alterar o domínio nem o scorer.

## 19. Decisões que o domain modeling deve fechar

Esta pesquisa recomenda, mas não declara finais, os seguintes pontos:

- nome e fronteira entre `Job` (oportunidade canônica) e `JobOccurrence` (observação por fonte);
- distinção entre vínculo, programa de entrada, jornada, modalidade e senioridade;
- lifecycle exato de candidatura e seus eventos;
- estrutura de `Requirement`, `Evidence`, `SkillGap`, `FitDimension` e `MatchAssessment`;
- política de aliases/sinônimos e quem pode alterá-la;
- regra de merge/desmerge de duplicatas;
- quais gates são realmente impeditivos;
- localização do banco e política de retenção de raw payloads;
- contrato mínimo de `JobSource` e capability flags por portal;
- papel estritamente opcional de LLM e provenance de qualquer inferência.

## Fontes primárias principais

- [README no commit analisado](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/README.md)
- [Setup Guide](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SETUP.md)
- [`/setup`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/setup.md)
- [`/scrape`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-scraper/SKILL.md)
- [`/rank`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/rank.md)
- [`/apply`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/apply.md)
- [`/outcome`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/outcome.md)
- [`/interview`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/interview.md)
- [`/upskill`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/upskill/SKILL.md)
- [`/add-portal`](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/commands/add-portal.md)
- [Job Evaluation Framework](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/.claude/skills/job-application-assistant/04-job-evaluation.md)
- [Portal contract test](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/tests/test_scrape_contract.py)
- [Security Policy](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/SECURITY.md)
- [Changelog](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/CHANGELOG.md)
- [MIT License](https://github.com/MadsLorentzen/ai-job-search/blob/ab91c60cc47147d9416f0af758fb5e2d109956ce/LICENSE)
