# Instalação

## Pré-requisitos

- Python 3.11 ou mais recente;
- SQLite com FTS5, normalmente incluído nas distribuições atuais do Python.

## Instalação recomendada

O extra `all` inclui parsing, contagem de tokens e servidor MCP:

=== "pipx"

    ```bash
    pipx install "semtree[all]"
    ```

=== "uv tool"

    ```bash
    uv tool install "semtree[all]"
    ```

=== "pip em ambiente virtual"

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install "semtree[all]"
    ```

## Extras opcionais

Instale apenas o necessário quando quiser controlar as dependências:

```bash
pip install semtree
pip install "semtree[parse]"
pip install "semtree[tokens]"
pip install "semtree[mcp]"
```

- o pacote base fornece a CLI, SQLite e fallback limitado por expressões regulares;
- `parse` instala as oito gramáticas tree-sitter usadas pela extração estrutural;
- `tokens` instala o contador tiktoken;
- `mcp` instala o servidor `semtree-mcp`.

## Verificar

```bash
semtree --version
semtree --help
python -c "import semtree.mcp"
```

O import confirma que o módulo MCP está disponível sem iniciar o servidor `stdio`.

## Próximos passos

- [Quickstart](quickstart.md)
- [Integrações](integrations.md)
