# CLI

O pacote instala dois executáveis: `semtree`, para operações locais, e `semtree-mcp`, para o servidor MCP por `stdio`.

Use `semtree --root /caminho/do/projeto <comando>` para selecionar outra raiz. Sem `--root`, a CLI procura um marcador de projeto a partir do diretório atual.

## Indexação

```bash
semtree index
semtree index --force
semtree index --quiet
```

`index` não recebe um caminho posicional. A execução incremental pula arquivos cujo hash não mudou; `--force` reprocessa todos. O banco padrão é `.ctx/index.db`.

## Contexto

```bash
semtree context "implementar paginação"
semtree context "entender auth" --budget 4000 --level 2
semtree context "validar entrada" --file src/api.py
semtree context "revisar pagamento" --output contexto.md
```

Opções: `--budget/-b`, `--level/-l` de 0 a 3, `--file/-f` e `--output/-o`. A saída é Markdown; não existe opção `--format` na versão atual.

## Busca

```bash
semtree search "validate_token"
semtree search "Auth" --kind class --limit 10
semtree search "login" --json
```

`search` consulta nomes, assinaturas e docstrings. `--kind/-k` filtra o tipo, `--limit/-n` limita resultados e `--json` muda a serialização. A consulta não aceita sintaxe própria de wildcard.

## Estado e memória

```bash
semtree status
semtree memory add rule estilo "Use imports absolutos"
semtree memory add ref arquitetura docs/architecture.md
semtree memory add note migracao "Revisar antes do release"
semtree memory list
semtree memory list --kind rule
semtree memory remove note migracao
```

`status` mostra raiz, banco, número de arquivos e símbolos, idade da atualização, orçamento e uso de metadados Git. A versão atual não possui comandos `stats` ou `clean`.

## Setup de assistentes

```bash
semtree setup --target all --dry-run
semtree setup --target claude
semtree setup --target cursor
semtree setup --target copilot
semtree setup --target codex
```

Claude Code recebe configuração em `.mcp.json` na raiz e solicita aprovação do servidor de escopo do projeto antes do primeiro uso. Cursor recebe `.cursor/mcp.json`. Copilot recebe uma instrução de contexto em `.vscode/settings.json`; Codex recebe uma instrução em `AGENTS.md` ou `CODEX.md`. Confira [Integrações](getting-started/integrations.md).

## Configuração

```bash
semtree config
semtree config --show
semtree config --init
```

`--init` grava os padrões em `.ctx/semtree.json`. O servidor MCP reconhece `SEMTREE_ROOT` e usa `CLAUDE_PROJECT_DIR` como fallback no Claude Code; o logging também lê `SEMTREE_DEBUG`. As demais opções documentadas ficam no arquivo JSON, não em variáveis de ambiente.

Para listar a interface instalada, use `semtree --help` e `semtree <comando> --help`.
