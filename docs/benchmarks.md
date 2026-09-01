# Benchmark local

O repositório inclui `benchmarks/run.py`, que compara dois volumes de texto:

1. todos os arquivos indexáveis de um projeto;
2. o contexto montado pelo Semtree para cada consulta.

O script conta tokens nos dois textos e imprime a diferença absoluta e percentual. Ele não mede precisão da resposta de um modelo, latência, memória ou qualidade de recuperação.

## Executar no projeto sintético

Na raiz de um clone do repositório:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
python benchmarks/run.py
```

Sem `--root`, o script cria temporariamente uma API de exemplo e executa as cinco consultas declaradas em `DEFAULT_QUERIES`.

## Executar em outro projeto

```bash
python benchmarks/run.py --root /caminho/do/projeto
```

Opções implementadas:

- `--root PATH`: usa um projeto existente em vez da amostra temporária;
- `--budget N`: define o orçamento de tokens de cada contexto; o padrão é 1200;
- `--query TEXTO`: substitui as consultas padrão e pode ser repetido.

Exemplo:

```bash
python benchmarks/run.py \
  --root /caminho/do/projeto \
  --budget 2000 \
  --query "localizar a validação de sessão" \
  --query "encontrar a criação de faturas"
```

## Interpretar o relatório

Cada linha apresenta a consulta, os tokens do conjunto bruto, os tokens do contexto selecionado, a diferença e o percentual correspondente. O resultado depende do projeto, da consulta, das linguagens suportadas, do estado do índice e do orçamento.

Uma redução de volume não demonstra que todos os símbolos necessários foram recuperados. Avalie também a cobertura do seu caso, os testes e a revisão humana antes de adotar o contexto gerado.
