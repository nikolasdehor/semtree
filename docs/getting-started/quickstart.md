# Quickstart

## 1. Instalar

```bash
pip install "semtree[all]"
```

O extra `all` inclui as gramáticas tree-sitter, a contagem de tokens e o servidor MCP.

## 2. Indexar o projeto atual

```bash
cd /caminho/do/projeto
semtree index
```

O comando percorre os arquivos configurados, extrai símbolos das linguagens suportadas e grava o banco local em `.ctx/index.db`. Em execuções seguintes, hashes permitem pular arquivos sem alteração.

Para indexar outra raiz sem mudar de diretório:

```bash
semtree --root /caminho/do/projeto index
```

## 3. Montar contexto

```bash
semtree context "entender a autenticação" --budget 4000
```

A saída em Markdown reúne símbolos encontrados por nome, assinatura e docstring dentro do orçamento. Ela pode omitir contexto relevante; revise o resultado antes de usá-lo.

## 4. Buscar símbolos

```bash
semtree search "validate_token"
semtree search "Auth" --kind class --limit 10
```

Use `--json` quando precisar de uma saída estruturada.

## 5. Integrar um assistente

Confira primeiro os arquivos que seriam escritos:

```bash
semtree setup --target all --dry-run
```

Claude Code e Cursor podem receber o servidor MCP. Copilot e Codex recebem instruções para chamar a CLI. Veja [Integrações](integrations.md) e [Servidor MCP](../mcp.md).

## Próximos passos

- [Como funciona](../concepts/how-it-works.md)
- [CLI completa](../cli.md)
- [Benchmark local](../benchmarks.md)
- [Privacidade](../privacy.md)
