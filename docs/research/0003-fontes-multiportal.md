# Pesquisa de fontes multiportal

Issue relacionada: #25  
Spec principal: #24

## Objetivo

Avaliar tecnicamente novas fontes de vagas para expansão do buscador, priorizando oportunidades compatíveis com profissionais em início de carreira, especialmente estágio, trainee e júnior.

A pesquisa deve manter os princípios atuais do projeto:

1. Não depender de LLM para produzir resultados corretos.
2. Não contornar autenticação, CAPTCHA ou mecanismos de proteção.
3. Não automatizar plataformas quando não houver uma forma apropriada de integração.
4. Preservar a URL e a origem de cada oportunidade.
5. Tratar dados ausentes como desconhecidos.
6. Manter cada integração isolada atrás da interface JobSource.
7. Evitar dependência de serviços que exijam credenciais destinadas a recrutadores ou empresas.
8. Priorizar fontes úteis para candidatos em início de carreira.

CIEE está explicitamente fora do escopo deste marco.

## Fontes avaliadas

### 1. Remotar

Classificação revisada: não recomendada para automação.

Prioridade proposta: nenhuma para integração automatizada.

O Remotar possui páginas públicas de vagas com informações úteis para candidatos e para análise manual.

Durante a revisão posterior dos termos aplicáveis à plataforma, foi identificada proibição ao uso de mecanismos automatizados, software, scripts e tecnologias do tipo robot ou crawler para coleta ou cópia de conteúdo.

Por esse motivo, a disponibilidade pública das páginas não deve ser interpretada como autorização para coleta automatizada.

O projeto não implementará RemotarJobSource baseado em scraping.

O Remotar poderá continuar sendo considerado apenas como referência manual ou através de alguma integração oficial futura, caso a plataforma venha a disponibilizá-la.

Risco técnico: não aplicável, pois a integração automatizada não será implementada nas condições atuais.

Decisão revisada: não implementar automação ou scraping do Remotar.

### 2. Nube

Classificação proposta: página pública estruturada.

Prioridade proposta: muito alta.

O Nube é especialmente relevante para o objetivo atual do projeto porque possui grande foco em estágio.

As páginas públicas apresentam informações como:

Código da oportunidade.

Área.

Cidade e estado.

Tipo de oportunidade.

Valor da bolsa.

Benefícios.

Indicadores de modalidade presencial, híbrida ou home office quando disponíveis.

Informações relacionadas à candidatura.

Foram observadas oportunidades de Tecnologia da Informação no Rio de Janeiro.

Não foi identificada uma API pública oficial adequada ao uso deste projeto.

A candidatura ocorre dentro do ecossistema do Nube e deve inicialmente permanecer manual ou assistida.

Antes de implementar acesso automatizado às páginas públicas, os termos aplicáveis e regras de acesso do portal devem ser revisados.


Não foi identificada uma API pública oficial adequada ao uso deste projeto.

A candidatura ocorre dentro do ecossistema do Nube e deve permanecer manual ou assistida.

Apesar da relevância da plataforma para estágio, o projeto não deve implementar coleta automatizada até que exista uma forma oficial de integração, autorização adequada ou mecanismo explicitamente destinado ao acesso programático.

Risco técnico e operacional: pendente.

Decisão revisada: manter Nube como fonte desejável, porém bloqueada para implementação automatizada até existir uma forma oficial adequada.

### 3. ProgramaThor

Classificação revisada: não recomendada para automação.

Prioridade proposta: nenhuma para integração automatizada.

O ProgramaThor possui listagens públicas muito relevantes para desenvolvimento, incluindo oportunidades classificadas como Estágio e Júnior.

Entretanto, a revisão das regras da plataforma identificou proibição ao uso de robôs ou bots para coleta automatizada de dados.

Por esse motivo, o projeto não implementará ProgramaThorJobSource através de scraping das páginas públicas.

A disponibilidade pública das vagas poderá continuar sendo utilizada apenas para consulta manual ou por uma integração oficial futura, caso seja disponibilizada.

Risco técnico: não aplicável para o Marco 3, pois a automação não será implementada nas condições atuais.

Decisão revisada: não implementar scraping ou automação do ProgramaThor.


### 4. Adzuna

Classificação proposta: API oficial adequada ao projeto.

Prioridade proposta: alta.

A Adzuna disponibiliza uma API REST oficial para pesquisa de vagas.

A documentação oficial inclui o Brasil entre os mercados suportados através do código `br`.

A API permite realizar buscas utilizando informações como:

Palavras-chave.

Localização.

Quantidade de resultados.

Ordenação.

Filtros adicionais suportados pelo serviço.

Os resultados disponibilizam dados úteis para normalização em JobPosting, incluindo:

Identificador da vaga.

Título.

Descrição.

Empresa.

Localização.

Data de criação ou atualização quando informada.

URL de redirecionamento para a oportunidade original.

A integração exige credenciais próprias da API, destinadas ao consumo programático.

Isso torna a Adzuna significativamente mais adequada ao projeto do que fontes que exigiriam scraping de páginas HTML.

Risco técnico: baixo a médio, principalmente relacionado a limites da API e mudanças de contrato.

Decisão: recomendada como próxima fonte real após Jooble.

### 5. Remotive

Classificação proposta: API pública oficial.

Prioridade proposta: média a alta.

A Remotive oferece uma API pública voltada à descoberta de vagas remotas.

Os resultados possuem informações estruturadas úteis para o projeto, incluindo:

Identificador.

Título.

Empresa.

Categoria.

Descrição.

Tipo de trabalho.

Data de publicação.

Localização associada à vaga quando informada.

URL original da oportunidade.

A API possui suporte a tipos de vaga que podem incluir estágio.

A integração deve preservar a atribuição exigida pela plataforma e o link original da oportunidade.

Por possuir foco em trabalho remoto, a Remotive não substitui uma fonte brasileira generalista, mas complementa Jooble e Adzuna.

Risco técnico: baixo a médio.

Decisão: recomendada após Adzuna para ampliar oportunidades remotas.

### 6. Gupy

Classificação proposta: API oficial existente, mas inadequada para o caso de uso pessoal atual.

Prioridade proposta: baixa para integração direta.

A Gupy possui APIs oficiais de Recrutamento e Seleção.

A autenticação utiliza Bearer Token.

A documentação informa que o acesso à API está disponível para clientes dos planos Premium e Enterprise e que o token é gerado por usuários administradores da organização.

Existem endpoints oficiais relacionados a vagas, candidatos e candidaturas.

Também existe endpoint para criação de uma candidatura para determinada vaga e candidato.

Esse recurso, porém, pertence ao contexto de recrutamento da empresa que utiliza a Gupy.

Ele não representa uma API pública destinada a um candidato individual automatizar a própria candidatura em empresas externas.

Portanto, o projeto não deve solicitar, reutilizar ou tentar obter tokens pertencentes às empresas anunciantes.

O Remotar pode permitir descobrir algumas oportunidades originalmente hospedadas na Gupy sem que seja necessária uma integração direta com a API privada da empresa recrutadora.

Risco técnico para integração direta: alto.

Decisão inicial: não implementar GupyJobSource baseado na API empresarial neste momento.

A candidatura em vagas Gupy deve inicialmente permanecer manual ou assistida.

### 7. Indeed

Classificação proposta: plataforma com APIs oficiais destinadas principalmente a parceiros, ATSs e empregadores.

Prioridade proposta: baixa neste momento.

O Indeed mantém APIs oficiais para diferentes funções relacionadas a vagas, candidatos e empregadores.

A documentação atual apresenta recursos como:

Job Sync API.

Candidate Sync.

Indeed Apply.

Employer Registration.

Integrações para ATS.

O acesso aos recursos relevantes exige contexto de parceria, credenciais OAuth e, em determinados fluxos, acordo de desenvolvedor e aprovação da integração pelo Indeed.

Essas APIs não representam uma API pública destinada a um candidato individual automatizar buscas e candidaturas pessoais.

Por esse motivo, não devemos construir o Marco 3 dependendo dessas credenciais.

Risco técnico para integração oficial no contexto atual: alto.

Decisão inicial: adiar integração direta.

## Matriz de decisão

| Fonte | Tipo identificado | Estágio e Júnior | Dados úteis para matching | API adequada ao projeto | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Jooble | API oficial | Sim | Alta | Sim | Implementada |
| Adzuna | API oficial | Sim | Alta | Sim | Alta |
| Remotive | API pública oficial | Sim, principalmente remoto | Alta | Sim | Média a alta |
| Nube | Plataforma pública | Forte foco em estágio | Média | Pendente | Pendente |
| Remotar | Página pública | Sim | Alta | Automação não recomendada | Nenhuma |
| ProgramaThor | Página pública | Sim | Alta | Automação não recomendada | Nenhuma |
| Gupy | API oficial empresarial | Sim | Alta | Não para candidato individual | Baixa |
| Indeed | APIs oficiais para parceiros e empregadores | Sim | Alta | Não para o caso atual | Baixa |


## Ordem recomendada de implementação

A ordem revisada é:

1. Jooble, já implementada.
2. MultiSourceJobSource, já implementado.
3. Adzuna como próxima fonte real.
4. Remotive para ampliar vagas remotas.
5. Nube somente quando existir forma oficial adequada de integração.
6. Manter Gupy e Indeed adiados até existir um modelo de acesso adequado para candidatos individuais.
7. Não implementar scraping de Remotar ou ProgramaThor.
8. Implementar e aprimorar deduplicação entre fontes oficiais conforme novas integrações forem adicionadas.

## Arquitetura desejada

Jooble, Remotar, Nube e ProgramaThor devem implementar a mesma interface JobSource.

Os payloads externos nunca devem atingir diretamente o domínio.

Cada adapter deverá produzir JobPosting normalizado.

OpportunityDiscovery continuará responsável por normalização, deduplicação, avaliação, elegibilidade, ranking e Shortlist.

A arquitetura desejada conceitualmente é:

JoobleJobSource
AdzunaJobSource
RemotiveJobSource

Todos alimentam:

MultiSourceDiscovery

que alimenta:

OpportunityDiscovery

e finalmente:

DiscoveryResult e Shortlist.

## Estratégia para início de carreira

A expansão multiportal deve priorizar oportunidades classificáveis como:

Estágio.

Trainee.

Júnior.

Entrada ou Entry Level.

Vagas sem senioridade explícita podem permanecer avaliáveis como desconhecidas.

Vagas explicitamente Pleno ou Sênior devem receber tratamento específico pela política de matching futura, evitando competir igualmente com oportunidades adequadas a candidatos em início de carreira.

## Candidatura

O Marco 3 não realizará envio automático de candidatura.

Será introduzido posteriormente um conceito semelhante a ApplicationCandidate.

Uma oportunidade poderá se tornar candidata à aplicação quando satisfizer critérios como:

FitScore igual ou superior a 80.

Senioridade compatível.

Ausência de blocker confirmado.

Elegibilidade adequada.

Cobertura de evidência suficiente.

Fonte original conhecida.

O envio real da candidatura deverá respeitar as capacidades e regras de cada plataforma.

Quando não existir integração oficial adequada, a candidatura deverá permanecer manual ou assistida.

## Conclusão

A revisão posterior dos termos das plataformas mostrou que viabilidade técnica não é suficiente para justificar uma integração automatizada.

Remotar e ProgramaThor possuem conteúdo tecnicamente acessível, porém suas regras atuais tornam inadequada a implementação de coleta automatizada pelo projeto.

Nube continua sendo uma fonte altamente relevante para estágio, mas permanece pendente até existir uma forma oficial adequada de integração.

Adzuna e Remotive passam a ser as alternativas prioritárias porque oferecem interfaces oficialmente destinadas ao acesso programático.

Com MultiSourceJobSource já implementado, o próximo passo recomendado é criar AdzunaJobSource e integrá-lo ao fluxo existente junto ao Jooble.

Após validar a Adzuna com vagas reais brasileiras, a Remotive poderá ser adicionada para ampliar a cobertura de oportunidades remotas.