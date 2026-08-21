# Arquitetura do buscador-de-vaga

## Direção

O `buscador-de-vaga` é uma aplicação local-first para pessoas entrando no mercado brasileiro de tecnologia. Ela preserva o lifecycle e os guardrails do `MadsLorentzen/ai-job-search`, mas os implementa como software Python independente de Agent Skills, com domínio tipado, integrações explícitas e resultados auditáveis.

O primeiro marco entrega uma CLI capaz de ler um CandidateProfile local, consultar um JobSource autorizado, normalizar JobPostings, consolidá-los em Opportunities, avaliar compatibilidade e apresentar uma Shortlist. Candidatura automática, geração de documentos, tracking, entrevistas, upskill, dashboard, múltiplas fontes e LLM ficam fora desse corte.

## Modules e seams

```text
CLI Adapter
    |
    v
OpportunityDiscovery.discover(CandidateProfile, SearchCriteria)
    |-- planejamento da consulta
    |-- normalização
    |-- deduplicação conservadora
    |-- MatchAssessment determinístico
    |-- elegibilidade + ranking
    |
    +--> JobSource.search(JobSourceQuery)
             |-- JoobleJobSource (produção)
             |-- SyntheticJobSource (tracer offline)
             `-- StubJobSource (testes)
```

### OpportunityDiscovery

`OpportunityDiscovery` é um Module profundo. Sua Interface recebe um CandidateProfile e SearchCriteria e devolve um DiscoveryResult. A Implementation oculta derivação de consultas, normalização, deduplicação, classificação de Requirements, MatchAssessment, EligibilityStatus, ordering e corte da Shortlist.

O DiscoveryResult preserva:

- SearchRun e relatório da fonte;
- todos os JobPostings aceitos;
- Opportunities deduplicadas com seus JobPostings de origem;
- MatchAssessment de cada Opportunity considerada;
- Shortlist contendo somente EligibilityStatus `eligible` ou `uncertain`;
- falhas tipadas e dados desconhecidos sem inventar valores.

O primeiro corte é síncrono. Uma futura UI web poderá executar o Module em worker sem transformar o domínio em `async` antecipadamente.

### JobSource

`JobSource` é a Interface no Seam de sistemas externos verdadeiros. `OpportunityDiscovery` converte SearchCriteria em uma JobSourceQuery pequena, composta por keywords, localização e limite; assim, o Adapter não precisa conhecer CandidateProfile, JobCategory nem política de matching. Cada Adapter traduz autenticação, paginação, payloads e erros da fonte para JobPostings e falhas tipadas. O domínio não conhece HTTP, chaves, schemas externos nem nomes específicos do Jooble. O SyntheticJobSource é somente um harness offline: sua fixture declara a consulta que representa e é rejeitada quando os argumentos da execução não correspondem.

O primeiro Adapter será `JoobleJobSource`, baseado na REST API oficial brasileira. A chave regional vem de `JOOBLE_API_KEY`; ela nunca aparece em argumentos, logs, fixtures, erros ou arquivos versionados. Testes usam HTTPX MockTransport e payload sintético; o smoke test live é manual e limitado.

### Dependências futuras

Persistência e LLM não recebem Interfaces hipotéticas no primeiro corte. Quando o produto precisar preservar histórico entre execuções, SQLite entrará como dependência local substituível, usando `sqlite3` atrás de um Seam interno. Quando houver extração semântica real, um Adapter de LLM poderá enriquecer dados estruturados com Provenance, sem produzir FitScore diretamente.

## Invariantes do domínio

- Ausência de informação produz RequirementStatus `unknown`, nunca `unmet`.
- Toda conclusão relevante preserva Evidence e Provenance quando disponíveis.
- Um Requirement só se torna BlockingRequirement quando é claramente impeditivo e comprovadamente `unmet`.
- EligibilityStatus é separado do FitScore.
- Opportunity inelegível permanece no DiscoveryResult e não entra na Shortlist.
- PossibleBlocker mantém a Opportunity visível com EligibilityStatus `uncertain`.
- JobPosting preserva identidade, URL, origem, texto recebido e instante de coleta.
- Deduplicação nunca apaga JobPostings nem faz merge por similaridade incerta.
- Conteúdo de vagas é input não confiável e nunca é interpretado como instrução executável.
- Matching e ordering são determinísticos, versionados e independentes de LLM.

## Ordering inicial

A Shortlist tem ordering total e estável:

1. EligibilityStatus `eligible` antes de `uncertain`;
2. FitScore decrescente;
3. atualização conhecida mais recente apenas como desempate, sem alterar o score;
4. identificador canônico da Opportunity como desempate final.

## Stack inicial

- Python 3.12+ e layout `src/`;
- `pyproject.toml` com Hatchling;
- `venv` + `pip`, sem ferramenta global obrigatória;
- dataclasses imutáveis no domínio;
- `argparse` para a CLI;
- HTTPX síncrono no Adapter Jooble;
- pytest, Ruff e mypy estrito;
- matriz de CI em Python 3.12 e 3.14.

Pydantic, Typer, SQLAlchemy, Alembic, `uv`, Playwright e SDKs de LLM serão adotados somente quando um caso concreto justificar seu custo.

## Estrutura inicial

```text
src/buscador_de_vaga/
├── __init__.py
├── cli.py
├── discovery.py
├── domain.py
├── profile.py
└── sources/
    ├── __init__.py
    ├── synthetic.py
    └── jooble.py
tests/
├── fixtures/
├── test_cli.py
├── test_discovery.py
└── test_jooble_source.py
```

Essa estrutura expressa quatro responsabilidades públicas: vocabulário de domínio, descoberta, carregamento do perfil e Adapter externo. Funções auxiliares permanecem privadas até que um segundo caller demonstre a necessidade de outro Module.

## Seams de teste confirmados

1. `OpportunityDiscovery.discover`: normalização, deduplicação, matching, elegibilidade, ranking e Shortlist por comportamento observável.
2. `JobSource.search`: contrato do JoobleJobSource com MockTransport e fixtures sintéticas, sem rede na suíte.
3. CLI: integração pequena para argumentos, saída e códigos de erro.

Testes não atravessam esses seams para verificar funções internas e não reproduzem a Implementation na expectativa.

## Dados locais e segurança

CandidateProfile real, credenciais, banco, raw payloads e artefatos pessoais ficam fora do versionamento. Exemplos públicos são totalmente fictícios. Links de JobPostings são apresentados ao Candidate, mas não são seguidos automaticamente; login, CAPTCHA, paywall, controles anti-bot e candidatura permanecem fora da automação.
