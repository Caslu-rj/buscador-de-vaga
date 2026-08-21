# Avaliação da stack Python inicial

**Data da pesquisa:** 21 de agosto de 2026  
**Escopo:** primeiro tracer bullet do `buscador-de-vaga`, em Windows, com Python 3.14.0 instalado e compatibilidade declarada com Python 3.12 ou superior.

## Conclusão executiva

Começar com uma stack pequena e explícita:

| Área | Escolha inicial | Adiar até haver necessidade comprovada |
| --- | --- | --- |
| Projeto e build | `pyproject.toml`, layout `src/` e Hatchling | outro frontend ou backend de build |
| Ambiente | `venv` + `pip`, sem ativação obrigatória | `uv`, adotado de uma vez com `uv.lock` |
| Modelo de domínio | `dataclasses` imutáveis e decodificação explícita nas bordas | Pydantic |
| Persistência | nenhuma no primeiro caminho vertical; depois `sqlite3` | SQLAlchemy e Alembic |
| CLI | `argparse` | Typer |
| HTTP | HTTPX síncrono | programação assíncrona e outro cliente |
| Testes | pytest | plugins sem caso de uso concreto |
| Lint e formato | Ruff | Black, isort e Flake8 separados |
| Tipagem estática | mypy em modo estrito | Pyright ou dois verificadores simultâneos |

Assim, a única dependência de runtime do primeiro tracer bullet é HTTPX. Hatchling é dependência de build; pytest, Ruff e mypy são dependências de desenvolvimento. `dataclasses`, `argparse`, `sqlite3`, `os` e `json` vêm da biblioteca padrão.

## Critérios

1. Preservar a versão mínima declarada, Python 3.12, mesmo que o ambiente local use 3.14.
2. Entregar cedo um caminho de ponta a ponta: consultar um `JobSource`, converter a resposta em `JobPosting` e exibir o resultado pela CLI.
3. Manter I/O nas bordas e o domínio independente de bibliotecas de validação, banco e CLI.
4. Acrescentar abstrações somente quando elas eliminarem complexidade já observada.
5. Não exigir ferramentas instaladas globalmente.

## Projeto, build e ambiente

### `pyproject.toml` e Hatchling

O `pyproject.toml` deve ser a fonte de verdade para metadados, dependências, entry point e configuração das ferramentas. O guia oficial da PyPA recomenda um pacote regular sob `src/` e explica que o bloco `[build-system]` torna explícito o backend usado pelo frontend de build; o tutorial usa Hatchling como opção inicial. O campo `requires-python` comunica aos instaladores quais versões são aceitas ([PyPA: Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)).

Hatchling é adequado aqui porque implementa os padrões de build editável e de wheel sem trazer um framework de aplicação ([Hatch: Build configuration](https://hatch.pypa.io/latest/config/build/)). A versão atual declara Python 3.14 entre as versões suportadas ([Hatchling no PyPI](https://pypi.org/project/hatchling/)).

Estrutura alvo:

```text
src/
  buscador_de_vaga/
tests/
pyproject.toml
```

### Começar com `venv` + `pip`

Essa opção já está disponível no Python instalado e não adiciona uma etapa de bootstrap. A documentação do Python caracteriza ambientes virtuais como descartáveis e não portáveis; eles devem ser ignorados pelo Git e recriados, não copiados ([Python 3.14: `venv`](https://docs.python.org/3.14/library/venv.html)). Em Python 3.12, `setuptools` deixou de ser uma dependência básica de `venv`, mas `pip` continua sendo inicializado por padrão; o backend declarado resolve o build isolado.

No PowerShell, não é necessário ativar o ambiente:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Isso também evita depender da política de execução do PowerShell para o script `Activate.ps1`.

### Quando migrar para `uv`

`uv` é compatível com Windows e Python 3.14, possui wheel para Windows e pode ser instalado por `pip`; portanto, não exige instalação global nem o instalador do sistema ([uv: instalação](https://docs.astral.sh/uv/getting-started/installation/), [uv no PyPI](https://pypi.org/project/uv/)). Caso tempos de instalação, atualização de dependências ou reprodutibilidade passem a incomodar, ele pode ser bootstrapado em um ambiente local separado:

```powershell
py -3.14 -m venv .tools\uv
.tools\uv\Scripts\python.exe -m pip install "uv==0.12.5"
.tools\uv\Scripts\uv.exe sync --locked
```

Ao fazer essa migração:

- ignorar `.tools/` e `.venv/`;
- versionar `uv.lock`;
- usar `uv sync --locked` no CI e `uv run ...` para comandos do projeto;
- deixar de usar `pip install -e ".[dev]"` como fluxo oficial, evitando dois gerenciadores como fontes de verdade.

O lock do `uv` é multiplataforma e a sincronização pode validar que ele não está desatualizado ([uv: locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)). O ganho é real, mas não é necessário para provar o primeiro caminho vertical.

## Modelo de domínio: `dataclasses` antes de Pydantic

Usar `@dataclass(frozen=True, slots=True)` para tipos internos como `JobPosting`, critérios de busca e resultados de avaliação. A biblioteca padrão gera inicialização e comparação a partir dos campos anotados, mas não valida os tipos em runtime ([Python 3.14: `dataclasses`](https://docs.python.org/3.14/library/dataclasses.html)). Por isso, cada adaptador de `JobSource` deve decodificar o JSON não confiável explicitamente, validar campos obrigatórios e somente então construir o objeto de domínio.

Pydantic oferece validação, serialização e JSON Schema a partir de type hints, inclusive para dataclasses e `TypedDict` ([Pydantic: Models](https://pydantic.dev/docs/validation/latest/concepts/models/)). A linha v2 atual declara suporte a Python 3.14 ([Pydantic no PyPI](https://pypi.org/project/pydantic/)). Mesmo assim, adicioná-lo agora duplicaria uma borda de entrada pequena e poderia acoplar o modelo de domínio ao formato de uma API.

Gatilhos para adotar Pydantic v2, preferencialmente somente nas bordas:

- duas ou mais fontes com payloads aninhados e divergentes;
- erros de validação estruturados que precisem ser apresentados ao usuário;
- serialização e JSON Schema recorrentes;
- código manual de decodificação que se torne maior ou mais frágil que o modelo validado.

## Persistência: `sqlite3` antes de SQLAlchemy

O primeiro tracer bullet pode consultar uma fonte, normalizar os dados e imprimi-los sem banco. Isso testa a integração mais incerta antes de criar schema. Quando persistência local entrar, usar `sqlite3` atrás de uma interface de repositório, com migrations SQL versionadas e testes em banco temporário.

O módulo `sqlite3` implementa DB-API 2.0, grava em arquivo sem servidor separado e é indicado pela própria documentação para prototipar antes de migrar para um banco maior ([Python 3.14: `sqlite3`](https://docs.python.org/3.14/library/sqlite3.html)). Regras práticas:

- consultas sempre parametrizadas;
- transações explícitas, sem depender silenciosamente do modo legado;
- argumentos opcionais de `sqlite3.connect()` por nome, pois seu uso posicional foi descontinuado em 3.13 e se tornará keyword-only em 3.15;
- conexão fechada explicitamente;
- um arquivo temporário por teste via `tmp_path`.

SQLAlchemy 2 oferece tanto SQL Expression Language quanto ORM e Unit of Work ([SQLAlchemy 2.0: overview](https://docs.sqlalchemy.org/en/20/intro.html)); a versão atual publica suporte a Python 3.14 ([SQLAlchemy no PyPI](https://pypi.org/project/SQLAlchemy/)). Essa capacidade custa uma nova camada conceitual que o schema inicial ainda não justifica.

Reavaliar SQLAlchemy quando houver relacionamentos e consultas dinâmicas relevantes, mais de um backend de banco, necessidade clara de Unit of Work ou repetição difícil de conter no adaptador `sqlite3`. Se chegar esse momento, escolher SQLAlchemy 2.x conscientemente, começando por Core se o domínio não precisar de ORM; adicionar Alembic somente quando migrations programáticas trouxerem benefício.

## CLI: `argparse` antes de Typer

`argparse` já cobre argumentos, opções, validação básica, ajuda e subcomandos sem dependência externa ([Python 3.14: `argparse`](https://docs.python.org/3.14/library/argparse.html)). É suficiente para um comando como `buscar-vagas`, que recebe consulta e filtros e chama um caso de uso.

Python 3.14 acrescentou ajuda colorida e sugestões para erros. Como o projeto promete Python 3.12+, não passar `color=` ou `suggest_on_error=` ao construtor sem compatibilidade condicional; o caminho inicial mais simples é não depender desses recursos.

Typer deriva uma CLI de type hints e oferece ajuda rica, completion e grupos de comandos, mas traz uma camada adicional e dependências de apresentação ([Typer: documentação](https://typer.tiangolo.com/), [Typer no PyPI](https://pypi.org/project/typer/)). Adotá-lo somente se a CLI se tornar uma interface de produto com vários grupos, prompts ou completion realmente utilizados.

## HTTP: HTTPX síncrono e isolado no adaptador

HTTPX é a única dependência de runtime recomendada. Ele fornece API síncrona e assíncrona, timeouts, pooling e anotações de tipo ([HTTPX](https://www.python-httpx.org/)). Para uma única fonte e baixo volume, usar a API síncrona:

- um `httpx.Client` reutilizado por operação, fechado por context manager;
- timeout explícito de conexão, leitura, escrita e pool; HTTPX aplica por padrão timeout após cinco segundos de inatividade, mas explicitar a política documenta a decisão ([HTTPX: Timeouts](https://www.python-httpx.org/advanced/timeouts/));
- `raise_for_status()` e tradução de falhas HTTP para erros do adaptador;
- cliente ou transport injetável para testes, sem consumir quota nem acessar rede no CI;
- credencial obtida de variável de ambiente, nunca persistida.

A versão estável publicada atualmente é 0.28.1. Ela declara `Requires-Python >=3.8`, mas os classifiers da publicação vão somente até Python 3.12; isso não prova incompatibilidade com 3.14, apenas significa que a publicação não o declara explicitamente ([HTTPX no PyPI](https://pypi.org/project/httpx/)). Portanto, usar `httpx>=0.28.1,<1`, testar instalação/importação e uma requisição simulada em Python 3.12 e 3.14, e não adotar uma prévia 1.0 sem decisão específica.

## Testes, lint, formato e tipos

### pytest

pytest oferece descoberta simples, introspecção de `assert` e fixtures; `tmp_path` atende aos testes de SQLite sem plugin ([pytest: Get Started](https://docs.pytest.org/en/stable/getting-started.html)). A versão atual declara Python 3.14 e requer Python 3.10 ou superior ([pytest no PyPI](https://pypi.org/project/pytest/)).

No primeiro tracer bullet:

- testes unitários dos decoders e regras de domínio;
- teste do caso de uso com `JobSource` falso;
- teste do adaptador HTTP com transporte simulado e payload salvo como fixture;
- nenhum teste contra a API real no CI;
- quando houver banco, teste de integração com arquivo sob `tmp_path`.

### Ruff

Ruff reúne linter e formatter, lê `pyproject.toml` e pode substituir a combinação inicial de Flake8, isort e Black ([Ruff](https://docs.astral.sh/ruff/)). Ele entende Python 3.14, mas o `target-version` deve ser `py312`, pois esse é o menor runtime suportado; a ferramenta também consegue inferir esse alvo de `project.requires-python` ([Ruff: target-version](https://docs.astral.sh/ruff/settings/#target-version)).

Comandos de CI:

```powershell
ruff check .
ruff format --check .
```

### mypy em vez de Pyright

mypy é a escolha inicial porque é instalado pelo mesmo ecossistema Python, configura-se em `[tool.mypy]` e permite começar um projeto novo com `strict = true` ([mypy: Getting started](https://mypy.readthedocs.io/en/stable/getting_started.html), [mypy: configuração](https://mypy.readthedocs.io/en/stable/config_file.html)). A versão atual publica suporte a Python 3.14 ([mypy no PyPI](https://pypi.org/project/mypy/)). Configurar `python_version = "3.12"`; caso contrário, o default acompanha o interpretador que executa mypy e poderia aceitar recursos exclusivos de 3.14.

Pyright é um verificador rápido e completo, porém sua instalação oficial de CLI usa o ecossistema Node/npm; o pacote de Python é mantido separadamente e providencia Node quando necessário ([Pyright: instalação](https://github.com/microsoft/pyright/blob/main/docs/installation.md)). Isso adicionaria outro runtime e lock apenas para tipagem. Preferi-lo se a equipe já padronizar Node/Pylance e quiser paridade exata com o editor. Não executar mypy e Pyright no CI ao mesmo tempo inicialmente: eles têm configurações e diagnósticos distintos sem entregar duas vezes o valor.

Comando de CI:

```powershell
mypy src tests
```

## Esqueleto recomendado de `pyproject.toml`

As faixas abaixo registram o conjunto avaliado na data desta pesquisa; um lock futuro deve fixar versões transitivas.

```toml
[build-system]
requires = ["hatchling>=1.32,<2"]
build-backend = "hatchling.build"

[project]
name = "buscador-de-vaga"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.28.1,<1",
]

[project.optional-dependencies]
dev = [
  "mypy>=2.3,<3",
  "pytest>=9.1,<10",
  "ruff>=0.16.4,<0.17",
]

[project.scripts]
buscar-vagas = "buscador_de_vaga.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/buscador_de_vaga"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--strict-config", "--strict-markers"]

[tool.ruff]
target-version = "py312"

[tool.ruff.lint]
extend-select = ["I"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_configs = true
```

## Caminho incremental

1. **Fundação:** criar pacote em `src/`, entry point com `argparse`, `pyproject.toml`, pytest, Ruff e mypy; validar tudo em Python 3.12 e 3.14.
2. **Primeiro tracer bullet:** implementar um `JobSource` HTTP com HTTPX síncrono, decodificar uma resposta em `JobPosting` dataclass e imprimir um resultado normalizado. Usar fixture e transporte simulado nos testes.
3. **Persistência:** quando o produto precisar guardar execuções ou oportunidades, introduzir um repositório `sqlite3` e migrations SQL pequenas. O caso de uso não deve importar `sqlite3` diretamente.
4. **Mais fontes:** manter um decoder por fonte. Só adotar Pydantic se a validação repetida e os payloads divergentes criarem complexidade mensurável.
5. **Escala observada:** reavaliar SQLAlchemy, Typer, async e `uv` separadamente, usando os gatilhos desta pesquisa. Nenhum deles precisa entrar como pacote preventivo.

## Compatibilidade com Python 3.14

- Executar a matriz de CI em **3.12 e 3.14**: a primeira protege o contrato mínimo; a segunda protege o ambiente de desenvolvimento atual.
- Configurar Ruff e mypy para **3.12**, não para o interpretador local.
- Evitar os parâmetros de `argparse` exclusivos de 3.14 no caminho comum.
- Usar os argumentos opcionais de `sqlite3.connect()` por nome e controlar transações explicitamente, preparando o código para as mudanças já descontinuadas.
- Hatchling, uv, Pydantic v2, SQLAlchemy, Typer, pytest, Ruff e mypy publicam suporte atual a 3.14. A ressalva específica é HTTPX 0.28.1, que exige um smoke test na matriz por não declarar esse classifier.

## Decisão recomendada

Adotar agora `pyproject.toml` + Hatchling, `venv` + `pip`, dataclasses, `argparse`, HTTPX síncrono, pytest, Ruff e mypy. Não adicionar banco ao primeiro tracer bullet; quando persistência entrar, começar com `sqlite3`. Deixar `uv`, Pydantic, SQLAlchemy e Typer registrados como opções com gatilhos objetivos, não como dependências antecipadas.
