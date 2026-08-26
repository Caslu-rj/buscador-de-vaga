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

Classificação proposta: página pública estruturada.

Prioridade proposta: muito alta.

O Remotar possui páginas públicas de vagas com informações úteis para o domínio do projeto.

Foram observados campos como:

Título da vaga.

Empresa.

Senioridade.

Tipo de contratação.

Modalidade de trabalho.

Descrição.

Responsabilidades.

Requisitos.

Tecnologias.

Origem da oportunidade.

URL da vaga.

Algumas oportunidades também identificam explicitamente a plataforma original, por exemplo Gupy.

Isso é particularmente interessante para o projeto porque permite preservar Provenance e pode auxiliar na deduplicação entre diferentes fontes.

Também existem oportunidades classificadas como Júnior e oportunidades voltadas a estágio.

Não foi identificada nesta pesquisa uma API pública oficial voltada para consumo deste projeto.

Antes de implementar acesso automatizado às páginas públicas, os termos aplicáveis e regras de acesso do portal devem ser revisados.

Risco técnico: médio.

Uma integração baseada em estrutura HTML pode quebrar quando o site alterar sua apresentação.

Decisão inicial: recomendado para investigação como primeiro novo JobSource.

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

Risco técnico: médio.

Decisão inicial: recomendado como uma das primeiras fontes adicionais, principalmente por sua relevância para estágio.

### 3. ProgramaThor

Classificação proposta: página pública estruturada.

Prioridade proposta: alta.

O ProgramaThor possui listagem pública dedicada a vagas de desenvolvimento.

A interface pública permite filtrar oportunidades por características importantes para o projeto, incluindo:

Tipo de contrato Estágio.

Senioridade Júnior.

Pleno.

Sênior.

Cidade.

Remoto.

Tecnologias.

Faixa salarial quando informada.

Tipo e tamanho da empresa quando informados.

Foram encontradas páginas públicas contendo oportunidades classificadas simultaneamente como Estágio e Júnior.

Apesar de algumas URLs possuírem o termo `jobs-api`, isso não deve ser interpretado como evidência de uma API pública oficial.

Até o momento, a pesquisa confirma uma página web estruturada, não um contrato público de API destinado ao consumo programático.

Antes de implementar acesso automatizado, os termos aplicáveis e regras de acesso devem ser revisados.

Risco técnico: médio.

Decisão inicial: recomendado após validar Remotar e Nube.

### 4. Gupy

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

### 5. Indeed

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
| Remotar | Página pública estruturada | Sim | Alta | Não identificada | Muito alta |
| Nube | Página pública estruturada | Sim, forte foco em estágio | Média | Não identificada | Muito alta |
| ProgramaThor | Página pública estruturada | Sim | Alta | Não identificada | Alta |
| Gupy | API oficial empresarial | Sim | Alta | Não para candidato individual | Baixa |
| Indeed | APIs oficiais para parceiros e empregadores | Sim | Alta | Não para o caso atual | Baixa |

## Ordem recomendada de implementação

A ordem inicial recomendada é:

1. Criar suporte a múltiplos JobSources em uma única descoberta.
2. Investigar Remotar como primeiro adapter adicional.
3. Investigar Nube como segunda fonte, priorizando estágio.
4. Investigar ProgramaThor como terceira fonte.
5. Implementar deduplicação entre diferentes fontes.
6. Utilizar Gupy apenas quando houver um método apropriado de descoberta ou redirecionamento.
7. Adiar Indeed enquanto não existir uma forma adequada de integração para o caso de uso do projeto.

## Arquitetura desejada

Jooble, Remotar, Nube e ProgramaThor devem implementar a mesma interface JobSource.

Os payloads externos nunca devem atingir diretamente o domínio.

Cada adapter deverá produzir JobPosting normalizado.

OpportunityDiscovery continuará responsável por normalização, deduplicação, avaliação, elegibilidade, ranking e Shortlist.

A arquitetura desejada conceitualmente é:

JoobleJobSource
RemotarJobSource
NubeJobSource
ProgramaThorJobSource

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

A pesquisa indica que a expansão multiportal é tecnicamente viável sem alterar o núcleo determinístico já existente.

Remotar, Nube e ProgramaThor são os candidatos mais interessantes para o próximo estágio de investigação.

Gupy e Indeed possuem APIs oficiais, porém seus modelos de acesso atuais não correspondem ao uso de um candidato individual automatizando suas próprias candidaturas.

O próximo passo recomendado é implementar primeiro a capacidade de agregação de múltiplos JobSources e, em seguida, validar tecnicamente o primeiro adapter público antes de adicionar as demais fontes.