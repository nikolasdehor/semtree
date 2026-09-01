# Por que tree-sitter

[Tree-sitter](https://tree-sitter.github.io/tree-sitter/) produz árvores sintáticas a partir do texto-fonte. O Semtree usa essas árvores para localizar declarações sem iniciar compiladores ou servidores de linguagem.

## Cobertura implementada

O extra `semtree[parse]` instala gramáticas para:

- Python;
- JavaScript e TypeScript;
- Go;
- Rust;
- Java;
- C e C++.

Cada linguagem possui um visitor no `extractor.py`. Os visitors reconhecem apenas os tipos de declaração implementados para aquela gramática; a cobertura não é igual entre linguagens.

## O que a análise entrega

Quando reconhecido, um símbolo contém nome, tipo, linhas inicial e final, assinatura e docstring. O indexador pode acrescentar autor e data por `git blame`.

Tree-sitter fornece estrutura sintática. A versão atual do Semtree não resolve imports, dependências, referências, chamadas ou tipos entre arquivos, nem executa as queries declarativas mostradas em exemplos genéricos de tree-sitter.

## Fallback

Se uma gramática não estiver instalada, Python, JavaScript, TypeScript, Go, Rust e Java possuem um fallback limitado por expressões regulares. C e C++ dependem da gramática para extrair símbolos. Outras extensões configuradas podem ser catalogadas como arquivos, sem símbolos estruturais.

## Adicionar uma linguagem

Adicionar apenas a gramática não basta. Uma contribuição completa precisa:

1. declarar a dependência em `pyproject.toml`;
2. registrar a gramática em `src/semtree/indexer/parser.py`;
3. mapear as extensões em `src/semtree/indexer/walker.py`;
4. implementar o visitor e, se desejado, o fallback em `src/semtree/indexer/extractor.py`;
5. adicionar testes e atualizar esta página.

O custo e a velocidade variam com número e tamanho dos arquivos, gramáticas instaladas, Git e armazenamento. O projeto não publica uma comparação fixa com LSPs.
