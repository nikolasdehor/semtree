# Semtree

**Contexto estrutural para AI assistants.** Indexação de código-fonte para Claude Code, Cursor, Copilot e Codex.

[![PyPI](https://img.shields.io/pypi/v/semtree?color=6e40c9&label=PyPI)](https://pypi.org/project/semtree/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](https://github.com/DeHor-Labs/semtree/blob/main/LICENSE)

## O problema

Você pode acabar enviando arquivos inteiros quando uma tarefa depende de poucas declarações. Isso consome parte do orçamento de contexto com implementações que talvez não sejam necessárias para aquela consulta.

## A solução

Com as gramáticas opcionais instaladas, o Semtree usa **tree-sitter** para parsear seu código-fonte e extrair símbolos suportados, assinaturas e docstrings. Sem elas, algumas linguagens usam fallbacks limitados por expressões regulares. A recuperação seleciona esse material dentro de um orçamento de contexto configurável.

```mermaid
flowchart LR
    A[Seu repo] -->|tree-sitter ou fallback limitado| B[Indexer]
    B --> C[(SQLite + BM25)]
    C -->|get_context| D[Claude / Cursor via MCP]
    C -->|search_symbols| D
    C -->|index_project| D
```

## Resultado prático

- Menos volume de contexto para o modelo processar, conforme a seleção e o orçamento
- Volume selecionado mensurável antes de enviar contexto ao assistente
- Benchmark local para medir tokens brutos e contexto selecionado no seu ambiente, sem promessa de redução fixa.

## Quick start

```bash
pip install "semtree[all]"

# Indexa o projeto atual
semtree index

# Vê o contexto que seria entregue ao agente
semtree context "implementar paginação no endpoint X"
```

## Integração com Claude Code

Crie ou atualize `.mcp.json` na raiz do projeto:

```json
{
  "mcpServers": {
    "semtree": {
      "command": "semtree-mcp",
      "args": []
    }
  }
}
```

O caminho recomendado é executar `semtree setup --target claude`, que preserva outros servidores quando a configuração existente é válida. O comando não sobrescreve JSON inválido. `semtree-mcp` precisa estar no PATH usado pelo Claude Code; a raiz é obtida em runtime por `CLAUDE_PROJECT_DIR`, sem gravar o caminho local no arquivo compartilhável. Reinicie o Claude Code e aprove o servidor de escopo do projeto quando solicitado; sem essa aprovação, as ferramentas não ficam disponíveis.

Depois da aprovação, use em qualquer pergunta:

> "Use o semtree para ver o contexto desse repo e me ajude a refatorar a função X"

## Onde ir agora

[:material-rocket: Comece pelo guia rápido](getting-started/quickstart.md){ .md-button .md-button--primary }
[:material-school: Como funciona](concepts/how-it-works.md){ .md-button }
[:material-github: Ver no GitHub](https://github.com/DeHor-Labs/semtree){ .md-button }

## Antes de adotar

- [Veja o caso técnico verificável](case-study.md)
- [Tire dúvidas no FAQ](faq.md)
- [Entenda a privacidade do processamento local](privacy.md)
