# Selecionando Contexto Estrutural para IAs de Programação com Semtree

Assistentes de inteligência artificial como Claude Code, Cursor ou GitHub Copilot precisam receber algum recorte do repositório para trabalhar. Enviar arquivos completos é uma opção; selecionar declarações antes do envio é outra.

O Semtree permite inspecionar e medir esse segundo caminho, sem afirmar que ele melhora a resposta do modelo.

## O problema do "Contexto Inchado"

Quando colamos arquivos inteiros no prompt, parte do orçamento pode ser ocupada por implementações que não ajudam a tarefa atual.

O efeito varia conforme o modelo e o projeto, mas o volume enviado pode aumentar custo, latência e consumo de limites. Medir o contexto selecionado ajuda a avaliar esse trade-off sem assumir que menos texto sempre produz uma resposta melhor.

## Uma opção: seleção estrutural com Semtree

O **Semtree** é uma biblioteca em Python que indexa declarações e monta um recorte estrutural dentro de um orçamento configurável.

Com as gramáticas opcionais instaladas, o Semtree utiliza o *tree-sitter* para analisar a sintaxe das linguagens hoje suportadas (Python, JavaScript/TypeScript, Go, Rust, Java, C e C++) e construir um índice estrutural do projeto. Sem elas, algumas linguagens usam fallbacks limitados por expressões regulares.

Quando a consulta é "adicionar rate limiting na rota de login", a busca e a política configurada selecionam símbolos do índice. O recorte pode incluir:
- Assinaturas de classes e métodos
- Docstrings
- Metadados do Git (quem alterou o arquivo pela última vez e quando)

O recorte também pode omitir código necessário; ele deve ser conferido antes da implementação.

## Medição de volume

A proposta do Semtree é reduzir o volume de contexto enviado ao assistente. O resultado varia conforme repositório, consulta, linguagens suportadas, estado do índice e orçamento configurado.

O repositório inclui um benchmark sintético reproduzível que compara o código bruto com o contexto selecionado pela versão presente no checkout. Ele mede volume, não qualidade da resposta: menos tokens pode reduzir custo e latência, mas não garante melhor precisão nem elimina perda de contexto.

## Integração nativa via MCP

O Semtree implementa um servidor local do Model Context Protocol (MCP) por `stdio`.

Ao rodar o comando de setup, o Semtree configura o servidor MCP para Claude Code e Cursor. Para Claude Code, a configuração fica em `.mcp.json` na raiz e exige aprovação do servidor de escopo do projeto antes do primeiro uso. Para Copilot e Codex, o setup grava instruções que chamam o comando `semtree context`; esses dois alvos não recebem automaticamente as três ferramentas MCP.

## Conclusão

O desenvolvimento assistido por IA também depende de gerenciamento de contexto. O Semtree permite selecionar menos código com critérios estruturais e medir o volume entregue, sem prometer por si só respostas melhores ou mais rápidas.

O projeto é aberto e permite reproduzir localmente a indexação, a busca e a medição de volume antes de decidir se o recorte atende ao seu caso.

---
**Sobre o autor:**
Nikolas de Hor é desenvolvedor de software em Goiânia.
Contato: nikolasdehor79@gmail.com
Link do projeto: https://github.com/DeHor-Labs/semtree
