# Contribuir

Contribuições são bem-vindas. Algumas formas de ajudar:

## Como ajudar

- **Issues**: reporte bugs ou peça features em [github.com/DeHor-Labs/semtree/issues](https://github.com/DeHor-Labs/semtree/issues)
- **Pull requests**: fork, branch, PR
- **Novas linguagens**: adicionar a gramática, o visitor de extração e testes para a linguagem
- **Casos de uso reais**: compartilhe como você usa o Semtree

## Setup de dev

```bash
git clone https://github.com/DeHor-Labs/semtree
cd semtree

# Instalar uv (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync --all-extras
```

## Comandos

```bash
# Testes
uv run pytest

# Lint + format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Build
uv build

# Docs locais
uv run mkdocs serve
```

## Adicionar suporte a nova linguagem

1. Instale a gramática: `uv add tree-sitter-<lang>`
2. Registre a gramática em `src/semtree/indexer/parser.py` e no extra `parse` do `pyproject.toml`.
3. Adicione o mapeamento da extensão em `src/semtree/indexer/walker.py`.
4. Implemente o visitor correspondente em `src/semtree/indexer/extractor.py`.
5. Adicione testes e atualize a tabela em `docs/concepts/tree-sitter.md`.

## Padrões

- PEP 8 + ruff format
- Testes pytest para o comportamento alterado
- Mensagens de commit em imperativo, sem AI footers
- Português pt-BR com acentos em strings/docs user-facing, inglês em código
