# Viabilidade de fontes de vagas para o primeiro tracer bullet

Pesquisa realizada em 21 de agosto de 2026. O objetivo foi identificar uma fonte real de vagas de entrada em tecnologia que possa sustentar um primeiro fluxo automatizado sem contornar login, CAPTCHA, controles anti-bot ou restrições contratuais.

## Conclusão executiva

**Recomendação: começar pela REST API do Jooble no domínio brasileiro.** Ela é a única interface encontrada nesta pesquisa que é declaradamente destinada a permitir que outro site consulte vagas e publique os resultados em seu próprio design. A chave deve ser solicitada no [formulário oficial do Jooble Brasil](https://br.jooble.org/api/about), e a documentação atual exige uma chave específica para cada país. O plano gratuito tem limite vitalício de 500 requisições por chave, portanto ele é adequado para um tracer bullet pequeno, não para coleta intensiva nem para chamadas em toda execução de CI ([documentação oficial da REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)).

Não recomendo ingerir automaticamente LinkedIn, Gupy, Indeed, Vagas.com, CIEE, Nube, ProgramaThor ou Remotar no primeiro incremento. Todos têm uma destas barreiras: proibição expressa de scraping/bots ou reprodução, ausência de API pública de busca, integração restrita a parceiros/clientes, ou resultados relevantes atrás de login. A interface HTML pública de um portal não deve ser tratada como autorização para coleta automatizada.

Esta é uma avaliação técnica e operacional baseada nos contratos e documentos públicos atuais, não um parecer jurídico. Para qualquer fonte cujo contrato não autorize claramente o caso de uso, a decisão segura é obter permissão escrita antes de automatizar.

## Critérios e escala

- **Mecanismo legítimo**: API, feed, plugin ou navegação humana que o próprio portal documenta para aquele uso.
- **Autenticação/custo**: credenciais, conta, parceria ou plano exigidos para busca, integração e candidatura.
- **Controles**: CAPTCHA documentado, regras anti-bot, `robots.txt`, limites e restrições de reprodução. Quando a fonte oficial não documenta CAPTCHA, o relatório registra **não documentado**, sem inferir que ele inexiste.
- **Estabilidade para integração**: **alta** para API documentada e destinada ao consumo; **média** para integração oficial restrita a parceria; **baixa** para HTML dirigido a pessoas e sem contrato de dados. Esta nota não mede disponibilidade do site.
- **Cobertura de entrada em tecnologia**: presença oficial de filtros ou páginas para estágio, aprendiz, trainee, júnior ou tecnologia.
- **Risco operacional**: probabilidade de bloqueio, quebra, violação de termos, baixa cobertura ou dependência comercial no caso de uso deste projeto.

## Matriz resumida

| Fonte | Mecanismo público legítimo | Autenticação, CAPTCHA, anti-bot e custo | Entrada em tecnologia | Estabilidade | Risco para ingestão automática |
| --- | --- | --- | --- | --- | --- |
| LinkedIn | Busca web e acesso de visitante; API de **publicação** apenas para parceiros aprovados | Visitantes podem ser solicitados a entrar; scraping, bots e contorno de limites são proibidos; há recursos Premium | Ampla; filtros oficiais incluem estágio e nível de experiência | Baixa para HTML; média para API parceira, que não é de busca | **Crítico** |
| Gupy | Portal público; API de vagas para empresas clientes | API usa Bearer token e só está disponível nos planos Premium/Enterprise; termos do candidato proíbem agregar/copiar partes da plataforma | Ampla no Brasil; portal oferece atalhos para estágio e jovem aprendiz | Baixa para portal; alta para API contratada, fora do caso de uso | **Alto/crítico** |
| Indeed | Busca web; Publisher JavaScript Plugin para parceiros | Termos proíbem bots/scraping e permitem medidas técnicas; plugin e APIs exigem parceria/OAuth | Ampla; busca brasileira exibe estágios em TI | Baixa para HTML; média para plugin parceiro | **Crítico** |
| Vagas.com | Busca web pública limitada | Candidatura e funções completas exigem conta; candidatos não pagam; reprodução depende de autorização | Boa; busca oficial possui filtros de tecnologia, estágio e júnior/trainee | Baixa | **Alto** |
| CIEE | Vitrine pública limitada; API de Vitrine oferecida a instituições de ensino | Mais oportunidades ficam na área logada; serviços ao estudante são gratuitos; não há onboarding público da API geral | **Muito alta para estágio/aprendiz**, inclusive TI | Baixa para HTML; média se houver parceria institucional | **Alto** |
| Nube | Listagens públicas e páginas por curso/área | Login para candidatura; candidato não paga; o portal proíbe reprodução sem autorização escrita | **Muito alta para estágio/aprendiz**; página específica de TI | Baixa | **Alto** |
| ProgramaThor | Listagem e detalhes públicos | Perfil é exigido para candidatura; código de conduta proíbe bots de coleta; plano pago é opcional para candidatos | **Muito alta e especializada em desenvolvimento**, com júnior e estágio | Baixa | **Crítico** |
| Remotar | Listagem e detalhes públicos | Cadastro libera todos os recursos; termos proíbem mecanismos, scripts e Robot/Crawler | Alta para tecnologia júnior, mas apenas trabalho remoto | Baixa | **Crítico** |
| Jooble Brasil | REST API oficial e busca web | Chave regional; plano gratuito com 500 requisições vitalícias; CAPTCHA não faz parte do contrato da API | Ampla, agregada, com resultados brasileiros de estágio/júnior em software | **Alta para o tracer bullet** | **Médio** |

### Outra fonte nacional triada

A Empregare anuncia uma `API pública` e webhooks, mas os materiais oficiais localizados posicionam essa interface dentro do produto pago de Recrutamento & Seleção, para integrar o sistema da empresa cliente a ERPs, HCMs e outras ferramentas; integrações personalizadas dependem de contrato ([produto e integrações](https://www.empregare.com/pt-br/business/sistemas/recrutamento-selecao), [visão comercial](https://www.empregare.com/pt-br/business/por-que-investir)). Não foi localizado um contrato público de **busca de vagas para candidatos**, com endpoint, schema, credencial self-service e permissão de republicação. Por isso, ela não é claramente superior para este tracer bullet e não foi promovida à matriz como fonte implementável. Uma demonstração comercial poderia reabrir essa avaliação no futuro.

## Avaliação por fonte

### LinkedIn

- **Mecanismo legítimo:** pessoas visitantes podem pesquisar vagas e se candidatar a várias oportunidades que redirecionam ao site da empresa sem criar conta; vagas sem redirecionamento exigem login. A própria ajuda avisa que uma pessoa visitante pode ser solicitada a entrar para continuar a pesquisa ([busca como visitante](https://www.linkedin.com/help/linkedin/answer/a523136/searching-on-linkedin?lang=en), [candidatura como visitante](https://www.linkedin.com/help/linkedin/answer/a513481/apply-for-jobs-as-guest-user?lang=en)).
- **API:** a API documentada é para criar e administrar anúncios, não para oferecer busca geral ao candidato. Seu uso é restrito a developers aprovados e exige acordo com restrições de dados; quem não é parceiro deve solicitar ingresso no programa Talent Solutions ([Apply Connect / Job Posting API](https://learn.microsoft.com/en-us/linkedin/talent/apply-connect/create-apply-connect-jobs?view=li-lts-2025-04), [termos específicos da Job Posting API](https://www.linkedin.com/legal/l/job-posting-api-terms)).
- **Controles e custo:** o User Agreement proíbe scripts, robots, crawlers, scraping, acesso automatizado não autorizado e contorno de controles ou limites. O crawling só é permitido após autorização expressa do LinkedIn; a solicitação é feita por e-mail e pode ser revogada ([User Agreement, seção 8.2](https://www.linkedin.com/legal/user-agreement), [Crawling Terms](https://www.linkedin.com/legal/crawling-terms)). A busca básica existe sem paywall, mas alguns insights e filtros são Premium ([boas práticas de busca](https://www.linkedin.com/help/linkedin/answer/a512477)). CAPTCHA não é documentado como contrato de integração e não deve ser automatizado se surgir.
- **Cobertura:** os filtros oficiais incluem localização, data, estágio, nível de experiência, tipo de contrato e trabalho remoto; a busca retorna no máximo 1.000 resultados ([filtros de vagas](https://www.linkedin.com/help/linkedin/answer/a507441/filter-and-sort-job-search-results?lang=en)). É uma fonte valiosa para descoberta manual, não para o coletor.
- **Avaliação:** estabilidade **baixa** e risco **crítico** para ingestão. Não implementar adapter nem usar endpoints internos observados no navegador.

### Gupy

- **Mecanismo legítimo:** o Portal Gupy oferece pesquisa pública por cargo, estado e cidade e destaca `Home office`, `Jovem aprendiz`, `Estágio` e `PCD`; a própria Gupy informa grande cobertura nacional de empresas e vagas ([Portal Gupy](https://portal.gupy.io/job-search)). A candidatura e todas as funcionalidades da pessoa candidata passam por cadastro, login e conta individual ([termos atuais para pessoas candidatas](https://www.gupy.io/termos-de-uso-recrutamento-e-selecao-candidatos)).
- **API:** existe um endpoint documentado `GET /api/v1/jobs`, com filtros e paginação, mas todas as requisições exigem Bearer token. A Gupy declara que a API só está disponível a clientes dos planos Premium e Enterprise; o token é gerado na área administrativa do cliente ([listagem de vagas](https://developers.gupy.io/reference/findjobs), [autenticação](https://developers.gupy.io/v2.0/reference/authentication)). Isso serve à empresa dona das vagas, não a um agregador público de todo o portal.
- **Controles e custo:** os termos proíbem à pessoa candidata agregar, copiar ou duplicar partes do Gupy, inclusive oportunidades expiradas, e proíbem testar ou violar autenticação e segurança ([termos atuais](https://www.gupy.io/termos-de-uso-recrutamento-e-selecao-candidatos)). A API contratada responde `401/403` sem autorização e `429` ao exceder o limite ([códigos e rate limit](https://developers.gupy.io/v2.0/reference/response-codes-and-errors)). CAPTCHA não está documentado como parte do contrato público; se a interface humana o apresentar, ele é um limite, não uma etapa automatizável.
- **Cobertura:** o portal tem alcance nacional e filtro específico para estágio ([busca de estágio](https://portal.gupy.io/job-search/jobTypes%5B%5D%3Dvacancy_type_internship)). A cobertura é forte, mas o acesso automatizado legítimo exigiria contrato com a Gupy ou autorização de cada empresa para sua própria página de carreiras.
- **Avaliação:** estabilidade **baixa** e risco **alto/crítico** pelo portal; estabilidade **alta** somente para cliente autorizado consultando suas próprias vagas via API. Não usar endpoints internos ou páginas `*.gupy.io` como API implícita.

### Indeed

- **Mecanismo legítimo:** a busca pública brasileira apresenta vagas e filtros por cargo/localidade, inclusive oportunidades de estágio em TI ([busca brasileira por estágio](https://br.indeed.com/empregos-de-Estagio)). Para publishers, o caminho oficial de exibição é o Publisher JavaScript Plugin, que renderiza um subconjunto de cards do Indeed e links de volta ao portal ([catálogo de integrações](https://docs.indeed.com/job-postings/), [Publisher JavaScript Plugin](https://docs.indeed.com/indeed-plus/publisher-js-plugin/)).
- **API/parceria:** o plugin não entrega um contrato de dados para normalização no backend e só fica disponível após tornar-se parceiro e obter identificadores fornecidos pelo Indeed. As APIs usam OAuth e credenciais do Partner Console, também provisionadas após parceria ([autenticação](https://docs.indeed.com/authentication), [pré-requisitos do plugin](https://docs.indeed.com/indeed-plus/publisher-js-plugin/)). O catálogo atual não oferece uma API pública de busca geral equivalente ao que este projeto precisa; essa conclusão é uma inferência do conjunto oficial de integrações documentadas.
- **Controles e custo:** as Site Rules proíbem acesso a dados por meios automatizados sem permissão, bots, scrapers, spiders, AI/Agentic AI, extração e candidatura automatizada; o Indeed se reserva o direito de detectar e impedir automação não autorizada ([Terms of Service, seção 21](https://www.indeed.com/legal)). O plugin é uma relação de parceria, não um endpoint gratuito anônimo. CAPTCHA não é documentado como API; qualquer desafio apresentado na web deve permanecer no fluxo humano.
- **Cobertura:** ampla no Brasil e com vagas de entrada, porém agregada e sujeita à qualidade dos anúncios de terceiros; o próprio Indeed esclarece que anúncios podem ser indexados automaticamente e que não controla o conteúdo externo ([Terms of Service, termos para Job Seekers](https://www.indeed.com/legal)).
- **Avaliação:** estabilidade **baixa** e risco **crítico** para scraping; estabilidade **média** para o plugin oficial, que ainda não atende à necessidade de um backend de busca/ranking.

### Vagas.com

- **Mecanismo legítimo:** a central de ajuda documenta busca por cargo, área, localização ou empresa, ordenação por data/relevância e filtros variáveis ([como pesquisar vagas](https://ajuda.vagas.com.br/portal/pt-br/kb/articles/pesquisar-vagas)). O portal permite navegação limitada sem conta; candidatura e funcionalidades completas exigem cadastro e login ([termos do aplicativo e portal](https://www.vagas.com.br/candidatos/termos-de-uso-aplicativo), [como se candidatar](https://ajuda.vagas.com.br/portal/pt-br/kb/articles/candidatar-vaga)). Não foi encontrada documentação oficial de API ou feed de busca para candidatos.
- **Controles e custo:** busca, currículo, alertas e candidatura são gratuitos para candidatos ([gratuidade](https://ajuda.vagas.com.br/portal/pt-br/kb/articles/assinatura-vagas)). Os termos protegem telas e conteúdos contra reprodução total ou parcial sem autorização expressa; a versão web também descreve `Vagas as a Service` como publicação **para dentro** do Vagas.com, não como API de leitura ([termos do candidato](https://www.vagas.com.br/candidatos/termos-de-uso), [termos do aplicativo e portal](https://www.vagas.com.br/candidatos/termos-de-uso-aplicativo)). CAPTCHA não é documentado; o HTML e o `robots.txt` não substituem autorização de uso dos dados.
- **Cobertura:** a página oficial de tecnologia expõe filtros de `Estágio`, `Júnior/Trainee`, `Informática/T.I.` e modalidade de trabalho, demonstrando cobertura útil de entrada ([vagas de tecnologia](https://www.vagas.com.br/vagas-de-tecnologia)).
- **Avaliação:** estabilidade **baixa** e risco **alto** para ingestão. Pode ser oferecido como link de pesquisa manual enquanto não houver autorização ou integração comercial.

### CIEE

- **Mecanismo legítimo:** o CIEE mantém uma Vitrine de Vagas pública com filtros, mas a própria página orienta entrar na área logada para ver mais oportunidades. Cadastro é o primeiro passo para candidatura ([vagas de estágio em TI](https://portal.ciee.org.br/quero-uma-vaga/estagio-ti/)).
- **API/parceria:** há uma `API de Vitrine de Vagas`, apresentada oficialmente como produto para conectar vagas ao portal de uma Instituição de Ensino Superior. Não foi localizada documentação pública de endpoint, schema ou emissão self-service de credenciais; portanto, o caminho legítimo é uma parceria institucional, não descobrir chamadas privadas da página ([CIEE Conecta 2026](https://portal.ciee.org.br/ciee-conecta-2026/), [exemplo institucional da API](https://portal.ciee.org.br/universo-ciee/workshop-fisicos-negros-brasil-eua-ufba-2025/)).
- **Controles e custo:** o CIEE informa que nenhum serviço para jovens e estudantes é cobrado e que a candidatura depende dos critérios legais de estágio ([página oficial de estágio](https://portal.ciee.org.br/quero-uma-vaga/estagio/)). Sua política registra prevenção a fraude/autenticação e coleta de IP/páginas após login, mas não publica um contrato de automação para terceiros ([Política de Privacidade](https://portal.ciee.org.br/politica-de-privacidade/)). CAPTCHA não é documentado; login ou desafio deve permanecer humano.
- **Cobertura:** é a fonte mais especializada em primeira experiência: estágio, aprendizagem, níveis médio/técnico/superior e uma página dedicada a TI, incluindo programação, suporte, segurança e testes ([vagas de estágio em TI](https://portal.ciee.org.br/quero-uma-vaga/estagio-ti/)).
- **Avaliação:** estabilidade **baixa** e risco **alto** sem parceria; estabilidade potencialmente **média** com a API institucional. Vale buscar parceria numa fase posterior caso estudantes sejam o público central.

### Nube

- **Mecanismo legítimo:** as listagens e filtros são visíveis publicamente, mas o portal exige login para candidatura. O painel oficial informa volume de vagas/empresas e deixa claro que o candidato não paga ([painel de vagas](https://www.nube.com.br/estudantes/painel_vagas), [login](https://www.nube.com.br/estudantes/vagas/filtro-de-vagas)). Não foi localizada documentação pública de API ou feed.
- **Controles e custo:** o rodapé do próprio painel proíbe a reprodução do conteúdo por meio eletrônico ou impresso sem autorização escrita do Nube ([painel de vagas](https://www.nube.com.br/estudantes/painel_vagas)). CAPTCHA e controles anti-bot específicos não são documentados; a ausência de um API contract e a proibição de reprodução bastam para não automatizar.
- **Cobertura:** a página dedicada a TI lista cursos técnicos, tecnólogos e superiores e apresenta vagas de estágio em desenvolvimento, dados, suporte e infraestrutura, com modalidade e bolsa ([estágios em TI](https://www.nube.com.br/vagas-de-estagio/tecnologia-da-informacao-ti)). É excelente para descoberta humana de vagas de entrada.
- **Avaliação:** estabilidade **baixa** e risco **alto** para ingestão. Solicitar autorização escrita ou parceria antes de qualquer adapter.

### ProgramaThor

- **Mecanismo legítimo:** listagem, filtros e detalhes de vagas são públicos, com foco explícito em pessoas desenvolvedoras. Para se candidatar é necessário criar perfil, completá-lo e atingir o match exigido; candidatos podem acessar e candidatar-se sem compra, embora existam benefícios opcionais pagos ([vagas](https://programathor.com.br/jobs), [FAQ](https://programathor.com.br/faq), [Termos de Serviço, seções 3, 4 e 6](https://programathor.com.br/terms)). Não foi encontrada API pública de busca; menções a API nos termos tratam de integrações/parceiros e compartilhamento de dados do usuário.
- **Controles:** o Código de Conduta proíbe expressamente robôs/bots para coleta de dados e prevê suspensão ou encerramento da conta ([Código de Conduta, seção 4](https://programathor.com.br/conduct)). CAPTCHA não é documentado, mas a proibição de bots já encerra a opção de crawling.
- **Cobertura:** é a fonte mais especializada do grupo para desenvolvimento; a listagem oferece filtros `Júnior`, `Estágio`, tecnologias, tamanho de empresa, remoto e localização. Vagas atuais de estágio possuem detalhes técnicos e perfil de entrada ([listagem](https://programathor.com.br/jobs), [exemplo oficial de estágio Front-End](https://programathor.com.br/jobs/32299-estagio-desenvolvedor-a-front-end)).
- **Avaliação:** estabilidade **baixa** e risco **crítico** para ingestão, apesar da alta relevância. Usar somente navegação/link manual ou integração autorizada por escrito.

### Remotar

- **Mecanismo legítimo:** páginas de vaga são públicas e direcionam à fonte de candidatura; cadastro libera recursos adicionais e vagas exclusivas ([exemplo oficial de vaga júnior via Gupy](https://remotar.com.br/job/155890/vetta/analista-de-gestao-junior), [exemplo de vaga júnior via Solides](https://remotar.com.br/job/137443/aggrandize/desenvolvedor-front-end-junior)). Não foi encontrada documentação oficial de API ou feed público.
- **Controles:** os termos proíbem reprodução/distribuição sem autorização, uso de mecanismos, software ou scripts e cópias por tecnologia de buscador `Robot/Crawler`; também proíbem sobrecarregar a infraestrutura ([Termos de Uso](https://remotar.com.br/termos-de-uso)). CAPTCHA não é documentado, mas crawlers estão expressamente fora do uso permitido.
- **Cobertura:** forte para trabalho 100% remoto e com labels de júnior, PcD, CLT/PJ e origem da vaga. Há vagas de suporte, sistemas, desenvolvimento e QA de entrada ([vaga de suporte júnior](https://remotar.com.br/job/155675/confidencial/analista-de-suporte-tecnico-jr), [vaga de sistemas júnior](https://remotar.com.br/job/155482/yduqs-vagas-tech/pessoa-analista-de-sistemas-junior-foco-em-operacao-e-sustentacao)). A limitação estrutural é cobrir apenas remoto.
- **Avaliação:** estabilidade **baixa** e risco **crítico** para ingestão. Não construir crawler, mesmo que as páginas sejam fáceis de ler.

### Jooble Brasil — fonte adicional e recomendada

O Jooble é um agregador internacional com operação e domínio específicos para o Brasil, não uma empresa brasileira. Ele foi incluído porque oferece uma interface pública de integração claramente superior às encontradas nos portais nacionais avaliados.

- **Mecanismo legítimo:** a página brasileira diz explicitamente que a REST API foi criada para webmasters e mecanismos de pesquisa consultarem vagas e publicarem as respostas em seu próprio site e design ([Jooble REST API Brasil](https://br.jooble.org/api/about)). A documentação define `POST /api/{api_Key}`, os parâmetros `keywords`, `location`, `radius`, `salary`, `page`, `ResultOnPage`, `SearchMode` e `companysearch`, além dos campos de resposta `id`, `title`, `location`, `snippet`, `salary`, `source`, `type`, `link`, `company` e `updated` ([documentação da REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)).
- **Autenticação, controles e custo:** a integração exige uma chave obtida no domínio do país-alvo. A documentação atual informa que cada chave regional só acessa as vagas daquele país e que o plano gratuito possui cota **vitalícia** de 500 requisições por chave; respostas documentadas incluem `403` para chave inválida e `404` para endpoint ausente ([documentação da REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)). Não há CAPTCHA no contrato da API. Não há paywall dentro dessa cota, mas o formulário solicita nome, cargo, e-mail, website e telefone ([formulário brasileiro](https://br.jooble.org/api/about)).
- **Cobertura:** o Jooble declara agregar fontes públicas e manter pesquisa localizada por país ([como o Jooble funciona](https://br.jooble.org/how-jooble-works/)). A busca brasileira tem resultados específicos para estágio em desenvolvimento de software e vagas júnior de API/desenvolvimento ([desenvolvimento de software no Brasil](https://br.jooble.org/vagas-de-emprego-desenvolvimento-de-software/Brasil), [exemplo de desenvolvedor de API júnior](https://br.jooble.org/jdp/-8048806375164094193)). Como agregador, pode conter duplicatas, resultados vencidos ou links intermediários; o produto deve sempre preservar origem, URL e data `updated`, sem alegar que esta seja a data original de publicação.
- **Estabilidade e risco:** estabilidade **alta** para o escopo do tracer bullet porque há schema e finalidade de integração documentados. Risco **médio**: cota pequena, dependência de uma chave externa e qualidade herdada das fontes agregadas. A documentação foi modificada em 16 de agosto de 2026, o que mostra manutenção recente, mas também exige acompanhar mudanças de contrato ([documentação da REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)).

## Interface recomendada, sem implementação

O domínio da aplicação não deve conhecer campos ou autenticação do Jooble. Um contrato conceitual mínimo — independente da stack final — seria:

```ts
type JobSearchCriteria = {
  terms: string[];
  location: string;
  page?: number;
};

type JobListing = {
  source: "jooble";
  sourceId: string;
  title: string;
  company?: string;
  location: string;
  summary?: string;
  salaryText?: string;
  employmentType?: string;
  sourceUpdatedAt?: string;
  url: string;
};

interface JobSource {
  search(criteria: JobSearchCriteria): Promise<{
    items: JobListing[];
    page: number;
    hasMore: boolean;
  }>;
}
```

Decisões de fronteira:

- O adapter `JoobleJobSource` mapearia somente os campos documentados pela API; `updated` deve virar `sourceUpdatedAt`, não `publishedAt`, pois a documentação o define como última atualização ([schema oficial](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)).
- A chave deve ficar fora do repositório e ser redigida dos logs, pois a API a coloca no próprio path `POST /api/{api_Key}` ([endpoint oficial](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)).
- O primeiro fluxo deve buscar uma página pequena por ação explícita do usuário, armazenar a resposta normalizada por pouco tempo e abrir `url` para candidatura humana. Não deve candidatar, resolver CAPTCHA, fazer login em terceiros nem seguir páginas para extrair descrições completas.
- A identidade de deduplicação dentro desta fonte pode ser `jooble:<sourceId>`; deduplicação entre fontes deve ficar fora do adapter e não faz parte do primeiro tracer bullet.
- A API real não deve ser chamada por testes unitários ou em toda execução de CI por causa da cota vitalícia de 500 chamadas ([limite oficial](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)). Um único smoke test manual e controlado após receber a chave é suficiente para validar o contrato real.

## Fixture segura para testes

Use uma resposta totalmente sintética que copie apenas a **forma** documentada, nunca descrições reais, credenciais ou dados pessoais:

```json
{
  "totalCount": 1,
  "jobs": [
    {
      "id": 9000001,
      "title": "Pessoa Desenvolvedora Júnior",
      "location": "Brasil - remoto",
      "snippet": "Fixture sintética para validar normalização e ranking.",
      "salary": "A combinar",
      "source": "fixture.example",
      "type": "Tempo integral",
      "link": "https://example.invalid/jobs/9000001",
      "company": "Empresa Exemplo",
      "updated": "2026-08-20T12:00:00Z"
    }
  ]
}
```

O TLD `.invalid` é reservado para testes e nunca deve resolver na Internet ([RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)). Essa fixture permite testar validação, mapping, ordenação e erros sem consumir a cota, depender de disponibilidade externa ou redistribuir conteúdo de uma vaga real.

## Próximos passos recomendados

1. Criar o repositório/site no GitHub e solicitar a chave no [formulário do Jooble Brasil](https://br.jooble.org/api/about), descrevendo com precisão que o produto exibirá resultados e redirecionará a pessoa candidata.
2. Confirmar por escrito eventuais condições adicionais, atribuição e opção após as 500 requisições antes de assumir uso recorrente.
3. Implementar primeiro o contrato `JobSource` contra a fixture sintética; depois habilitar `JoobleJobSource` com uma única consulta manual de validação.
4. Medir, numa amostra pequena, relevância para `estágio`, `júnior`, `trainee`, `desenvolvimento`, `dados`, `QA` e `suporte`, além de duplicatas e links vencidos. Só então decidir se vale negociar uma segunda fonte.
5. Se o foco do produto for especificamente estudantes, priorizar contato comercial/institucional com CIEE ou Nube. Se o foco for desenvolvimento, solicitar parceria à ProgramaThor. Não iniciar crawling enquanto essa autorização não existir.
