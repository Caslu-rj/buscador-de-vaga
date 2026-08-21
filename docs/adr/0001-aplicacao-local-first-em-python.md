# Aplicação local-first independente de Agent Skills

Decidimos construir um modular monolith local-first em Python 3.12+, inicialmente acessado por CLI, no qual Agent Skills orientam o desenvolvimento mas nunca são dependências do produto público. Essa escolha troca entrega imediata como serviço web multiusuário pela privacidade, simplicidade operacional e testabilidade de uma aplicação que mantém dados pessoais fora do repositório e poderá introduzir SQLite quando houver estado durável para preservar.
