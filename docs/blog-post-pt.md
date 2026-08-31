# Otimizando o Contexto para IAs de Programação com Semtree

Se você usa assistentes de inteligência artificial como Claude Code, Cursor ou GitHub Copilot no seu dia a dia, provavelmente já passou por isso: você pede para a IA implementar uma nova funcionalidade, mas ela se perde no meio do caminho. A resposta demora, o código sugerido tenta reinventar a roda ou ignora padrões que já existem no seu repositório.

O problema na maioria das vezes não está na capacidade do modelo de IA, mas na forma como alimentamos o contexto dele.

## O problema do "Contexto Inchado"

Quando colamos arquivos inteiros no prompt ou deixamos que o assistente leia livremente o diretório "src", estamos cometendo um erro fundamental. Arquivos de código contêm muito "ruído": dezenas de imports que não importam para a tarefa atual, implementações detalhadas de métodos auxiliares e linhas em branco.

Isso causa dois problemas severos. Primeiro, o uso de tokens explode, encarecendo chamadas de API e esgotando limites diários. Segundo, sofremos com a degradação de atenção (o famoso "lost in the middle"). Quando a IA recebe 45.000 tokens de texto cru, ela tem muito mais dificuldade para focar nas três ou quatro assinaturas de função que realmente importam para o bug que você quer corrigir.

## A solução: Contexto Cirúrgico com Semtree

Para resolver esse gargalo, criei o **Semtree**, uma biblioteca em Python desenhada especificamente para melhorar a qualidade do contexto de assistentes de IA. 

O Semtree abandona a ideia de passar texto cru. Em vez disso, ele utiliza o *tree-sitter* para analisar a sintaxe das linguagens hoje suportadas (Python, JavaScript/TypeScript, Go, Rust, Java, C e C++) e construir um índice estrutural do projeto.

O que isso significa na prática? Quando você pede para o assistente "adicionar rate limiting na rota de login", o Semtree atua como um filtro inteligente. Em vez de ler todo o arquivo de autenticação, ele extrai apenas as informações cruciais:
- Assinaturas de classes e métodos
- Docstrings
- Metadados do Git (quem alterou o arquivo pela última vez e quando)

## Redução drástica de Tokens

A proposta do Semtree é reduzir o volume de contexto enviado ao assistente. O resultado varia conforme repositório, consulta, linguagens suportadas, estado do índice e orçamento configurado.

O repositório inclui um benchmark sintético reproduzível que compara o código bruto com o contexto selecionado pela versão presente no checkout. Ele mede volume, não qualidade da resposta: menos tokens pode reduzir custo e latência, mas não garante melhor precisão nem elimina perda de contexto.

## Integração nativa via MCP

Ferramentas excelentes não devem exigir fluxos de trabalho complexos. O Semtree foi projetado para operar nos bastidores. Ele implementa o protocolo MCP (Model Context Protocol) de forma nativa. 

Ao rodar o comando de setup, o Semtree configura o servidor MCP para Claude Code e Cursor. Para Copilot e Codex, ele grava instruções que chamam o comando `semtree context`; esses dois alvos não recebem automaticamente as três ferramentas MCP.

## Conclusão

O desenvolvimento assistido por IA também depende de gerenciamento de contexto. O Semtree permite selecionar menos código com critérios estruturais e medir o volume entregue, sem prometer por si só respostas melhores ou mais rápidas.

Se você está cansado de ver sua IA se perder em repositórios grandes, o Semtree oferece uma solução prática e de código aberto para organizar o caos.

---
**Sobre o autor:**
Nikolas de Hor é desenvolvedor de software em Goiânia.
Contato: nikolasdehor79@gmail.com
Link do projeto: https://github.com/DeHor-Labs/semtree
