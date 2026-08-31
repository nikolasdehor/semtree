# Perguntas frequentes

## O Semtree envia meu repositório para algum servidor?

Não por conta própria. A indexação e a busca usam arquivos locais e um banco SQLite em `.ctx/index.db`. O trecho devolvido a um assistente pode ser enviado ao provedor de IA configurado nesse assistente, sob as regras dele.

## Ele substitui o contexto completo do projeto?

Não. O Semtree seleciona símbolos dentro de um orçamento de contexto. Consultas ambíguas ou mudanças amplas ainda podem exigir arquivos completos e revisão manual.

## Quais linguagens são analisadas?

O parser opcional cobre Python, JavaScript, TypeScript, Go, Rust, Java, C e C++. Outros arquivos podem aparecer na árvore, mas não recebem a mesma extração estrutural.

## Preciso configurar cada assistente manualmente?

Não necessariamente. `semtree setup` gera configurações para Claude Code, Cursor, Copilot e Codex. Use `--dry-run` para revisar as mudanças antes de gravá-las.

## A redução de tokens é garantida?

Não. Os benchmarks documentam cenários específicos, não uma garantia universal. O ganho depende do tamanho do repositório, da consulta e do orçamento configurado.

## O índice deve entrar no Git?

Não. `.ctx/index.db` é um artefato local regenerável e pode conter caminhos, símbolos e notas do projeto. Mantenha-o fora do versionamento.
