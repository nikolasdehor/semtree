# Caso técnico verificável

## Problema

Colar arquivos inteiros em um assistente consome contexto com imports, implementações e módulos que não ajudam a tarefa atual.

## Implementação

O Semtree percorre o repositório, extrai símbolos com tree-sitter, registra metadados em SQLite e seleciona trechos dentro de um orçamento configurável. O fluxo pode ser inspecionado no código e reproduzido pela CLI.

```bash
pip install "semtree[all]"
semtree index
semtree context "implementar paginação no endpoint X" --budget 4000
```

## Evidência pública

O script atual `benchmarks/run.py` cria um projeto sintético, executa cinco consultas definidas no código e imprime tokens brutos, tokens selecionados e a diferença percentual. Rode-o sem argumentos para obter uma medição do seu checkout. Ele não reproduz tabelas históricas nem aceita um arquivo externo de tarefas.

O resultado é técnico, não um depoimento de cliente. A seleção pode reduzir o volume de contexto e também omitir símbolos relevantes. O ganho real deve ser medido no repositório em que a ferramenta será usada.
