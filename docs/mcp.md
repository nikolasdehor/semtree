# Servidor MCP

O executável `semtree-mcp` inicia um servidor MCP por `stdio` e expõe três ferramentas. O diretório do projeto vem primeiro de `SEMTREE_ROOT`; no Claude Code, o fallback é `CLAUDE_PROJECT_DIR`. Sem essas variáveis, o servidor procura a raiz a partir do diretório atual.

## `index_project`

Indexa o projeto atual de forma incremental ou força uma reindexação.

```json
{
  "name": "index_project",
  "arguments": {
    "force": false
  }
}
```

A resposta informa status, raiz, contagens de arquivos e símbolos, duração e até cinco erros de indexação.

## `get_context`

Monta contexto para uma consulta dentro de um orçamento.

```json
{
  "name": "get_context",
  "arguments": {
    "query": "entender a validação de sessão",
    "token_budget": 4000,
    "level": 2,
    "file": null
  }
}
```

Parâmetros:

- `query` é obrigatório;
- `token_budget` tem padrão 8000;
- `level` recebe um inteiro opcional; use valores de 0 a 3, como na CLI;
- `file` restringe o contexto ao caminho informado.

## `search_symbols`

Pesquisa nomes, assinaturas e docstrings por correspondência exata, FTS5 ou prefixo.

```json
{
  "name": "search_symbols",
  "arguments": {
    "query": "AuthHandler",
    "kind": "class",
    "limit": 20
  }
}
```

A resposta contém os símbolos encontrados e seus metadados. O filtro `kind` é opcional.

## Executar

Instale o extra MCP e inicie o processo:

```bash
pip install "semtree[mcp]"
SEMTREE_ROOT=/caminho/do/projeto semtree-mcp
```

A implementação atual usa somente `stdio`; não expõe transporte HTTP nem endpoint de rede.

O comando `semtree setup --target claude` grava `.mcp.json` na raiz; `semtree-mcp` deve estar no PATH do Claude Code, que fornece `CLAUDE_PROJECT_DIR` ao processo. O Claude Code exige aprovação do servidor de escopo do projeto antes do primeiro uso. `--target cursor` grava `.cursor/mcp.json`. Consulte [Integrações](getting-started/integrations.md) para exemplos e use `--dry-run` antes de escrever arquivos.
