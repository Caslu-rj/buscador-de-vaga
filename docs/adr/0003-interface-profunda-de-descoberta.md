# Interface profunda de descoberta

Decidimos expor `OpportunityDiscovery.discover` como a única Interface do Module de descoberta e `JobSource.search` como seu único Seam variável inicial, mantendo normalização, deduplicação, matching e ordering dentro da Implementation. A alternativa foi escolhida após comparar uma função mínima, um fluxo otimizado para CLI e um pipeline assíncrono configurável: ela maximiza Depth e Locality para o primeiro caller sem antecipar Interfaces de persistência, política ou LLM antes de existir um segundo comportamento real.
