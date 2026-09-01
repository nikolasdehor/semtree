# GitHub Copilot Integration

Semtree works with GitHub Copilot Chat in VS Code by adding a reusable
instruction that asks Copilot to load structural context before generating code.

## Install

```bash
pip install "semtree[all]"
cd /path/to/your/project
semtree index
semtree setup --target copilot
```

The setup command updates `.vscode/settings.json` with
`github.copilot.chat.codeGeneration.instructions`.

## Manual VS Code settings

Add this to `.vscode/settings.json`:

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    {
      "text": "When given a task, first run: semtree context \"${input}\" to load structural context."
    }
  ]
}
```

## Suggested workflow

Use Semtree output as the first message in a Copilot Chat session:

```bash
semtree context "add retry with backoff to outbound API calls" --budget 4000
```

Then ask Copilot:

```text
Use the semtree context above to implement retry with exponential backoff and tests.
```

For quick symbol lookup:

```bash
semtree search "retry" --json
semtree search "AuthMiddleware"
```

Re-run `semtree index` after substantial edits so Copilot sees current symbol
locations and docstrings.
