# Busca de Vagas em Tecnologia no Brasil

Este contexto descreve um assistente de procura de emprego para pessoas que estão entrando no mercado brasileiro de tecnologia. O produto transforma publicações dispersas em oportunidades comparáveis, explica sua compatibilidade com o perfil profissional e apoia a jornada até o resultado da candidatura.

## Pessoas e perfil

**Candidate**:
A pessoa que procura uma vaga e cuja trajetória, evidências profissionais e preferências orientam a busca e a avaliação de compatibilidade.
_Avoid_: User, Applicant

**CandidateProfile**:
A representação estruturada das evidências profissionais, objetivos, preferências e restrições declaradas pelo Candidate. O currículo é uma das fontes do perfil, não o próprio perfil.
_Avoid_: Resume, CV, UserProfile

**Evidence**:
Um fato verificável do CandidateProfile que sustenta ou contradiz uma conclusão, como formação, projeto, experiência, curso, certificação, idioma, disponibilidade ou tecnologia conhecida.
_Avoid_: Keyword, Claim

**EvidenceAssertion**:
A direção explícita de uma Evidence: `supports` quando o fato favorece o atendimento de um Requirement ou `contradicts` quando demonstra seu não atendimento.
_Avoid_: RequirementStatus, BooleanSkill

**Provenance**:
A origem identificável de uma Evidence, de um campo de JobPosting ou de uma inferência derivada, suficiente para explicar de onde a informação veio.
_Avoid_: Source, Metadata

**Preference**:
Uma condição desejada pelo Candidate que orienta a busca ou o ranking sem necessariamente eliminar uma oportunidade.
_Avoid_: Requirement

**Constraint**:
Uma condição do Candidate que torna uma oportunidade inviável quando não é satisfeita, como disponibilidade, localização ou modalidade de trabalho.
_Avoid_: Preference, Blocker

## Mercado e oportunidades

**JobSource**:
Um portal ou sistema externo no qual publicações de vagas podem ser consultadas legitimamente.
_Avoid_: Scraper, Site

**JobPosting**:
A publicação de vaga exatamente como encontrada em um JobSource, mantendo a identidade e a procedência daquela fonte.
_Avoid_: Job, Opportunity

**Opportunity**:
A vaga lógica apresentada ao Candidate após normalização e deduplicação; pode reunir vários JobPostings referentes à mesma posição.
_Avoid_: JobPosting, Listing

**JobCategory**:
Uma categoria semântica de trabalho que reúne cargos, aliases e sinônimos equivalentes para fins de busca e compatibilidade.
_Avoid_: LiteralTitle, SearchTerm

**SearchCriteria**:
O conjunto explícito de categorias, localização, modalidades e demais filtros que delimitam uma busca de JobPostings.
_Avoid_: QueryString, SearchTerm

**SearchRun**:
Uma execução delimitada de busca, com SearchCriteria, fontes consultadas, instante da coleta e resultado ou falha de cada JobSource.
_Avoid_: Search, Scrape

**Requirement**:
Uma condição declarada ou inferida de uma Opportunity, classificada conforme sua importância para a candidatura.
_Avoid_: Skill, Keyword

**RequirementKind**:
A natureza específica do assunto de um Requirement, como JobCategory, skill, EntryProgram, Seniority, localização ou WorkplaceMode.
_Avoid_: FitDimension, RequirementImportance, RequirementStatus

**RequirementImportance**:
A classificação de um Requirement como impeditivo, preferencial ou incerto, baseada no texto da Opportunity e preservando a evidência dessa classificação.
_Avoid_: MandatoryFlag, Weight

**EmploymentArrangement**:
A forma de vínculo ou contratação da Opportunity no mercado brasileiro, como CLT, PJ ou temporário.
_Avoid_: EmploymentType, Contract

**EntryProgram**:
A natureza do programa de entrada associado à Opportunity, como estágio, trainee, jovem aprendiz ou posição regular.
_Avoid_: EmploymentArrangement, Seniority

**Seniority**:
O nível de experiência esperado para a Opportunity, separado do EntryProgram e do título literal da vaga.
_Avoid_: EntryProgram, ExperienceYears

**WorkSchedule**:
A jornada ou disponibilidade de horário exigida pela Opportunity, incluindo carga horária, turno e restrições relevantes.
_Avoid_: WorkplaceMode, Availability

**WorkplaceMode**:
A modalidade de local de trabalho da Opportunity: remota, híbrida ou presencial.
_Avoid_: RemoteType, LocationType

## Compatibilidade e priorização

**MatchAssessment**:
A avaliação explicável entre um CandidateProfile e uma Opportunity, composta por estados de requisitos, elegibilidade, dimensões, pontos fortes, gaps e possíveis impeditivos.
_Avoid_: Match, Ranking, Analysis

**RequirementStatus**:
A conclusão `met`, `unmet` ou `unknown` sobre a relação entre uma Evidence do CandidateProfile e um Requirement; ausência de informação sempre resulta em `unknown`.
_Avoid_: BooleanMatch, HasSkill

**EligibilityStatus**:
A conclusão `eligible`, `ineligible` ou `uncertain` do MatchAssessment, separada do FitScore e determinada apenas por requisitos realmente impeditivos.
_Avoid_: FitScore, Approved

**FitDimension**:
Um eixo específico do MatchAssessment, como área, senioridade, tecnologias, formação, experiência, localização, modalidade ou disponibilidade.
_Avoid_: Criterion, Factor

**FitScore**:
O resultado numérico agregado de um MatchAssessment, expresso de 0 a 100 e acompanhado da explicação que o sustenta.
_Avoid_: Rank, Percentage

**SkillGap**:
Uma competência relevante para a Opportunity cujo RequirementStatus é comprovadamente `unmet`; um estado `unknown` não constitui SkillGap.
_Avoid_: MissingKeyword, Weakness

**BlockingRequirement**:
Um Requirement claramente impeditivo cujo RequirementStatus é `unmet` com evidência confiável; torna o EligibilityStatus `ineligible` independentemente do FitScore.
_Avoid_: SkillGap, Constraint

**PossibleBlocker**:
Um Requirement possivelmente impeditivo cuja importância ou atendimento ainda é incerto; mantém a Opportunity visível e torna a dúvida explícita.
_Avoid_: BlockingRequirement, SkillGap

**Shortlist**:
Uma seleção ordenada das Opportunities mais promissoras com EligibilityStatus `eligible` ou `uncertain`; Opportunities inelegíveis permanecem no resultado auditável, fora desta seleção.
_Avoid_: SearchResult, Favorites

## Jornada de candidatura

**Application**:
O registro da candidatura do Candidate a uma Opportunity, incluindo materiais enviados, estado atual e histórico relevante.
_Avoid_: Apply, Submission

**ApplicationMaterial**:
Um artefato preparado para uma Application, como currículo adaptado, carta de apresentação ou mensagem de contato.
_Avoid_: Document, Content

**Interview**:
Uma etapa de avaliação vinculada a uma Application para a qual o Candidate pode se preparar com base na Opportunity e em seu CandidateProfile.
_Avoid_: Meeting, Screening

**Outcome**:
O resultado observado de uma Application, usado para acompanhar a jornada e melhorar avaliações futuras sem inventar causalidade.
_Avoid_: Status, Result

**StudyRecommendation**:
Uma sugestão de aprendizagem fundamentada em SkillGaps recorrentes nas Opportunities relevantes ao Candidate.
_Avoid_: Course, Upskill
