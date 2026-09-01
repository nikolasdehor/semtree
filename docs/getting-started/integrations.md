# Integrações

O Semtree oferece duas formas de integração:

- Claude Code e Cursor podem executar as três ferramentas pelo servidor `semtree-mcp` via `stdio`;
- Copilot e Codex recebem instruções para chamar `semtree context` pela CLI.

O comando `setup` escreve arquivos no projeto. Visualize o resultado antes:

```bash
semtree setup --target all --dry-run
```

## Claude Code

```bash
semtree setup --target claude
```

O comando cria ou atualiza `.mcp.json` na raiz do projeto, preservando outros servidores quando o JSON e `mcpServers` são válidos:

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

O executável `semtree-mcp` precisa estar no PATH usado pelo Claude Code. Em runtime, o servidor usa `CLAUDE_PROJECT_DIR`, fornecido pelo próprio Claude Code, por isso o arquivo compartilhável não contém um caminho absoluto do checkout.

Se `.mcp.json` contiver JSON inválido ou `mcpServers` não for um objeto, o setup não sobrescreve o arquivo e informa o erro. Depois de configurar, reinicie o Claude Code. Por segurança, o Claude Code solicita aprovação antes de usar um servidor de escopo do projeto vindo de `.mcp.json`; as ferramentas só ficam disponíveis após essa aprovação.

## Cursor

```bash
semtree setup --target cursor
```

O comando grava `.cursor/mcp.json` com o mesmo servidor `stdio` e a raiz do projeto em `SEMTREE_ROOT`.

## GitHub Copilot

```bash
semtree setup --target copilot
```

Esse alvo adiciona uma instrução em `.vscode/settings.json` para executar `semtree context`. Ele não registra as três ferramentas MCP.

## Codex

```bash
semtree setup --target codex
```

Esse alvo adiciona uma seção a `AGENTS.md` ou `CODEX.md`, orientando o uso de `semtree context`. Ele não altera a configuração MCP global do Codex.

## Configuração manual de um cliente MCP

Para outro cliente compatível com servidores `stdio`, use o executável `semtree-mcp`, sem argumentos de transporte, e defina `SEMTREE_ROOT` no ambiente do processo. A versão atual não oferece servidor HTTP.

Após configurar Claude ou Cursor, as ferramentas disponíveis são `index_project`, `get_context` e `search_symbols`. Confira os schemas em [Servidor MCP](../mcp.md).
