# Primeiro marco: descoberta e ranking de vagas

## Problem Statement

Uma pessoa entrando no mercado brasileiro de tecnologia encontra vagas espalhadas em fontes com títulos, campos e níveis de detalhe inconsistentes. Ela precisa gastar tempo comparando oportunidades manualmente, não consegue distinguir compatibilidade comprovada de informação ausente e corre o risco de priorizar vagas irrelevantes ou descartar vagas promissoras por requisitos apenas preferenciais.

## Solution

Entregar uma aplicação local-first em Python que leia um CandidateProfile privado, consulte uma fonte de vagas legitimamente integrável, converta cada JobPosting para o vocabulário comum, consolide duplicatas em Opportunities e produza MatchAssessments determinísticos e explicáveis. A CLI apresentará uma Shortlist ordenada, manterá possíveis impeditivos visíveis, conservará Opportunities inelegíveis no DiscoveryResult auditável e nunca dependerá de LLM para gerar um resultado correto.

O primeiro JobSource será a REST API oficial do Jooble Brasil. A execução live será explícita, limitada a uma página e autenticada por `JOOBLE_API_KEY`; toda a suíte automatizada será offline.

## User Stories

1. Como Candidate, quero manter meu CandidateProfile fora do Git, para que meus dados pessoais não sejam publicados acidentalmente.
2. Como Candidate, quero declarar categorias profissionais de interesse, para que a busca reflita as áreas em que pretendo trabalhar.
3. Como Candidate, quero que cada JobCategory reconheça aliases em português e inglês, para que títulos semanticamente equivalentes sejam encontrados sem depender de uma string literal.
4. Como Candidate, quero registrar Evidence favorável e desfavorável com Provenance, para que as conclusões sobre requisitos possam ser auditadas.
5. Como Candidate, quero informar localização e modalidades de trabalho aceitas, para que Opportunities incompatíveis sejam identificadas.
6. Como Candidate, quero escolher uma categoria e localização em uma execução da CLI, para controlar o escopo e o consumo da fonte externa.
7. Como Candidate, quero consultar vagas brasileiras por uma integração autorizada, para evitar depender de scraping ou contorno de controles de acesso.
8. Como Candidate, quero receber uma mensagem acionável quando `JOOBLE_API_KEY` não estiver configurada, para saber como habilitar a busca live.
9. Como Candidate, quero que uma busca sem resultados seja tratada como sucesso vazio, para distingui-la de uma falha técnica.
10. Como Candidate, quero que timeout, autenticação inválida, quota, indisponibilidade e quebra de contrato sejam diferenciados, para saber se devo corrigir configuração ou tentar novamente.
11. Como Candidate, quero que cada JobPosting preserve fonte, identificador externo, URL e instante de coleta, para poder verificar sua procedência.
12. Como Candidate, quero que `source_updated_at` permaneça distinto de data de publicação, para que o sistema não apresente uma data inventada.
13. Como Candidate, quero que campos ausentes permaneçam desconhecidos, para que o sistema não os transforme em zero, falso ou informação presumida.
14. Como Candidate, quero que conteúdo de vagas seja tratado apenas como dado, para que instruções maliciosas em anúncios não comandem a aplicação.
15. Como Candidate, quero que anúncios repetidos da mesma fonte sejam consolidados, para não revisar a mesma Opportunity várias vezes.
16. Como Candidate, quero que publicações consolidadas permaneçam ligadas à Opportunity, para não perder URLs e Provenance durante a deduplicação.
17. Como Candidate, quero que merges incertos sejam evitados, para que vagas genuinamente diferentes não sejam achatadas.
18. Como Candidate, quero que títulos normalizados sejam associados a JobCategories, para comparar a natureza da função em vez de exigir títulos idênticos.
19. Como Candidate, quero que o MatchAssessment compare categoria, skills, natureza entry-level e localização/modalidade, para receber uma visão multidimensional da compatibilidade.
20. Como Candidate, quero que cada Requirement tenha RequirementStatus `met`, `unmet` ou `unknown`, para distinguir comprovação, contradição e falta de informação.
21. Como Candidate, quero que um Requirement `unknown` não conceda pontos, para que o FitScore não presuma competência.
22. Como Candidate, quero que um Requirement `unknown` não vire SkillGap confirmado, para que ausência de informação não seja apresentada como deficiência.
23. Como Candidate, quero ver Requirements desconhecidos relevantes na explicação, para poder complementar meu perfil ou investigar a vaga.
24. Como Candidate, quero que um SkillGap exista apenas diante de Evidence confiável que contradiga o Requirement, para que gaps sejam factuais.
25. Como Candidate, quero que requisitos preferenciais não eliminem automaticamente vagas de estágio ou júnior, para não tratar listas aspiracionais como gates.
26. Como Candidate, quero que somente um Requirement claramente impeditivo e comprovadamente `unmet` produza EligibilityStatus `ineligible`, para evitar exclusões injustificadas.
27. Como Candidate, quero que um PossibleBlocker resulte em EligibilityStatus `uncertain`, para que a Opportunity continue visível com a dúvida explícita.
28. Como Candidate, quero que EligibilityStatus seja separado do FitScore, para que um score alto não esconda um impedimento e um possível impedimento não force score zero.
29. Como Candidate, quero que Opportunities inelegíveis permaneçam no DiscoveryResult com justificativa, para auditar por que ficaram fora da Shortlist.
30. Como Candidate, quero ver o breakdown do FitScore por FitDimension, para compreender o que favoreceu ou limitou a compatibilidade.
31. Como Candidate, quero ver Strengths, SkillGaps, Requirements desconhecidos e PossibleBlockers, para tomar a decisão final de candidatura.
32. Como Candidate, quero que scores tragam a versão da política, para que resultados antigos continuem interpretáveis após mudanças de pesos.
33. Como Candidate, quero que a Shortlist coloque Opportunities elegíveis antes das incertas e use ordering determinístico, para obter resultados reproduzíveis.
34. Como Candidate, quero limitar o tamanho da Shortlist, para concentrar minha revisão nas melhores Opportunities.
35. Como Candidate, quero abrir a URL original e me candidatar manualmente, para manter login, CAPTCHA, formulários e envio sob meu controle.
36. Como Maintainer, quero adicionar um segundo JobSource sem alterar matching ou domínio, para expandir fontes sem acoplamento.
37. Como Maintainer, quero que cada Adapter transforme payload externo em JobPosting tipado, para impedir que schemas de portais vazem ao core.
38. Como Maintainer, quero contract tests do JoobleJobSource com fixture sintética, para detectar drift sem consumir a quota da API.
39. Como Maintainer, quero testar normalização, deduplicação, matching e ranking através de `OpportunityDiscovery.discover`, para preservar liberdade de refatorar a Implementation.
40. Como Maintainer, quero um pequeno teste da CLI, para verificar argumentos, apresentação principal e códigos de saída sem duplicar todos os cenários do core.
41. Como Maintainer, quero Ruff, mypy estrito e pytest como feedback loops, para detectar problemas de estilo, tipos e comportamento antes de publicar mudanças.
42. Como Maintainer, quero executar a suíte em Python 3.12 e 3.14, para proteger tanto a versão mínima declarada quanto o ambiente atual de desenvolvimento.
43. Como Maintainer, quero que logs e erros removam secrets e raw payloads, para evitar vazamento da chave regional ou conteúdo não confiável.
44. Como Maintainer, quero um smoke test live separado e manual, para validar o contrato real sem tornar CI dependente da rede ou consumir repetidamente a quota.
45. Como Maintainer, quero que o clone público funcione sem `.agents/`, AGENTS.md ou outros arquivos locais de agentes, para que o produto seja independente do ambiente de desenvolvimento.

## Implementation Decisions

- O produto será um modular monolith local-first em Python 3.12+, inicialmente acessado por CLI e independente de Agent Skills em runtime.
- A stack inicial será Hatchling, `venv` + `pip`, dataclasses imutáveis, `argparse`, HTTPX síncrono, pytest, Ruff e mypy estrito.
- Pydantic, Typer, SQLAlchemy, Alembic, `uv`, Playwright, UI web e SDKs de LLM não entram neste marco.
- `OpportunityDiscovery` será um Module profundo com uma operação `discover`, recebendo CandidateProfile e SearchCriteria e devolvendo DiscoveryResult.
- A Implementation de `OpportunityDiscovery` ocultará planejamento da consulta, normalização, deduplicação, matching, elegibilidade, ranking e criação da Shortlist.
- `JobSource.search` será a Interface no Seam externo. O primeiro Adapter será JoobleJobSource; testes usarão Adapter sintético e HTTPX MockTransport.
- SearchCriteria selecionará uma JobCategory, localização e limite por SearchRun. A primeira versão realizará uma única chamada/página por execução para proteger a quota vitalícia.
- CandidateProfile será carregado de JSON local e conterá categorias, localização, modalidades aceitas e Evidence com EvidenceAssertion e Provenance. Um exemplo inteiramente fictício será versionado; o perfil real residirá em diretório ignorado.
- A taxonomy inicial cobrirá Desenvolvimento, TI/Suporte/Infraestrutura, Sistemas, Qualidade e Dados, com aliases pt-BR/en derivados dos perfis prioritários definidos pelo produto.
- JoobleJobSource mapeará somente campos documentados. Valores específicos da fonte não serão promovidos silenciosamente a fatos mais fortes; em particular, `updated` vira `source_updated_at`, não `published_at`.
- A deduplicação inicial será conservadora: primeiro por JobSource + external ID ou URL canônica; depois por empresa, título normalizado e localização quando todos estiverem presentes e forem equivalentes. Similaridade textual incerta apenas sinalizará possível duplicata em fase posterior.
- JobPosting preservará o valor original dos campos e Opportunity guardará todos os JobPostings consolidados.
- RequirementImportance será `blocking`, `preferred` ou `unknown`. Apenas linguagem explicitamente obrigatória poderá produzir `blocking`; listas genéricas de requisitos de vagas de entrada não serão promovidas automaticamente.
- RequirementStatus será `met`, `unmet` ou `unknown`. EvidenceAssertion `supports` pode produzir `met`; `contradicts` pode produzir `unmet`; ausência ou ambiguidade produz `unknown`.
- EligibilityStatus será `eligible`, `ineligible` ou `uncertain`. BlockingRequirement comprovadamente `unmet` produz `ineligible`; PossibleBlocker produz `uncertain`.
- A versão inicial do FitScore terá quatro FitDimensions, totalizando 100 pontos: alinhamento de JobCategory (40), skills explicitamente avaliáveis (25), EntryProgram/Seniority (20) e localização/WorkplaceMode (15).
- RequirementStatus `unknown` contribui com zero, permanece explicado e reduz a cobertura de evidência. O MatchAssessment mostrará separadamente a proporção da política sustentada por informações avaliáveis.
- BlockingRequirements não alteram matematicamente o FitScore; afetam EligibilityStatus e participação na Shortlist.
- A Shortlist ordenará primeiro `eligible`, depois `uncertain`, em seguida FitScore decrescente, `source_updated_at` conhecida mais recente e ID canônico da Opportunity.
- Uma falha de fonte será traduzida para erro tipado. Busca válida sem itens devolve DiscoveryResult vazio; se a única fonte falhar, a operação termina com erro acionável sem estado parcial corrompido.
- O Adapter não seguirá URLs encontradas, não fará scraping de páginas de detalhe, login, CAPTCHA, auto-apply ou execução de conteúdo da vaga.
- Secrets serão lidos de environment, com `JOOBLE_API_KEY` como configuração do primeiro Adapter. `.env`, perfis reais, bancos e dados locais serão ignorados pelo Git.
- A implementação será própria. O README citará inspiração em `MadsLorentzen/ai-job-search`; reutilização substancial futura exigirá preservação dos avisos MIT originais.

## Testing Decisions

- Bons testes verificarão comportamento observável por Interfaces públicas e usarão literais conhecidos como fonte independente de verdade. Não serão testadas funções privadas, ordem de chamadas internas ou estrutura incidental.
- O seam `OpportunityDiscovery.discover` cobrirá normalização, deduplicação, RequirementStatus, EligibilityStatus, FitScore, ordering, explicações e Shortlist usando um StubJobSource no limite externo.
- O seam `JobSource.search` cobrirá JoobleJobSource com HTTPX MockTransport: request, mapping, campos ausentes, `403`, `429`, timeout, `5xx` e payload incompatível.
- O seam da CLI cobrirá argumentos essenciais, resultado principal e códigos de saída, sem repetir toda a matriz do Module.
- O desenvolvimento seguirá red → green por cenário vertical: um teste falha, entra a implementação mínima e então o próximo comportamento é escolhido.
- Não haverá chamadas reais ao Jooble em pytest ou CI. Uma fixture sintética usará domínio `.invalid` e nenhum conteúdo, credencial ou descrição real.
- Ruff e mypy serão executados regularmente; a suíte completa será executada no encerramento do ticket.
- Como o repositório ainda não possui testes, não há prior art interno além dos seams e regras documentados nesta spec, no CONTEXT.md e nos ADRs.

## Out of Scope

- Persistência em SQLite e histórico entre SearchRuns.
- Mais de um JobSource ativo por execução.
- Scraping ou automação de LinkedIn, Gupy, Indeed, Vagas.com, CIEE, Nube, ProgramaThor e Remotar.
- Paginação extensa, scheduler, daemon, concorrência e retries automáticos.
- Similaridade textual/semântica para deduplicação incerta.
- Extração genérica de Requirements por LLM e qualquer dependência obrigatória de IA.
- Importação de currículo, entrevista de onboarding e extração automática de CandidateProfile.
- Adaptação de currículo, carta de apresentação, mensagens ou envio de candidatura.
- Tracking de Applications, Outcome, preparação para Interview, StudyRecommendation, dashboard e UI web.
- Banco de dados, API HTTP própria, autenticação multiusuário ou deploy em nuvem.
- Smoke test live automatizado ou consumo de quota na CI.

## Further Notes

- A pesquisa de referência está fixada no `MadsLorentzen/ai-job-search` v1.6.0, commit `ab91c60cc47147d9416f0af758fb5e2d109956ce`.
- A pesquisa de fontes concluiu que o Jooble é a opção inicial com contrato público mais adequado; a chave brasileira deve ser solicitada separadamente e pode estar sujeita a condições adicionais.
- A API do Jooble oferece apenas parte do detalhe necessário para um MatchAssessment rico. A primeira política deve declarar campos desconhecidos e cobertura de evidência, sem fingir análise da descrição completa.
- O titular MIT foi provisoriamente preenchido como `Caslu-rj`, nome de usuário GitHub identificado no ambiente local; poderá ser ajustado ao criar o repositório remoto.
- A spec deve ser publicada como GitHub issue com label `ready-for-agent` assim que remote e autenticação estiverem configurados.
