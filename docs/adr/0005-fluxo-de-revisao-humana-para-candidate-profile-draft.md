# 0005: Fluxo de Revisão Humana para CandidateProfileDraft

## Status
Aceito

## Contexto
O parsing determinístico de currículos extrai informações estruturadas (categorias, skills, níveis de experiência, idiomas) a partir de texto não estruturado em PDF/DOCX. Como arquivos de currículo variam amplamente em formatação e redação, qualquer mecanismo automático está sujeito a omissões ou falsos positivos.

Se o perfil do candidato (`CandidateProfile`) fosse sobrescrito diretamente pelo resultado bruto do parser, o cálculo do `MatchAssessment` e `FitScore` poderia ser comprometido por dados incompletos ou incorretos, gerando perda de confiança no sistema.

## Decisão
Decidimos introduzir um estado intermediário explícito chamado `CandidateProfileDraft`.

O fluxo funcionará da seguinte forma:
1. **Importação:** O usuário fornece um documento (`ResumeDocument`).
2. **Geração do Rascunho:** O `ResumeParser` processa o arquivo e produz um `CandidateProfileDraft`, contendo uma lista de `Evidence` acompanhadas de sua `Provenance` e grau de confiança.
3. **Revisão Humana (Human-in-the-loop):** O candidato visualiza as evidências extraídas no rascunho através da CLI (ou futuros canais) e pode confirmar, editar ou descartar itens antes da consolidação final.
4. **Consolidação:** Apenas após a confirmação do candidato, o `CandidateProfileDraft` é convertido no `CandidateProfile` oficial utilizado nos algoritmos de descoberta e compatibilidade.

## Consequências
- **Positivas:**
  - O candidato mantém controle total sobre os fatos que compõem seu perfil profissional.
  - Evita distorções no `MatchAssessment` provocadas por erros de parsing.
  - Aumenta a transparência do sistema ao mostrar a proveniente exata de cada evidência extraída.
- **Negativas:**
  - Requer uma etapa de confirmação por parte do usuário via CLI (`importar-curriculo --review` / JSON draft export).
