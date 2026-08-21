# Matching determinístico e explicável

Decidimos que elegibilidade, FitScore e explicações serão produzidos por uma política determinística e versionada, usando os estados `met`, `unmet` e `unknown`; apenas um Requirement claramente impeditivo e comprovadamente `unmet` torna uma Opportunity inelegível. LLMs poderão futuramente extrair ou enriquecer informações por um Adapter opcional, mas nunca serão necessários para calcular o resultado correto, preservando auditabilidade e independência de fornecedor em troca de menor sofisticação semântica inicial.
