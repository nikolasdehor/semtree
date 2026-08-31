# X Thread: Semtree e o Contexto para IAs 🌳🚀

1/7 Você já percebeu que quanto mais arquivos você joga no Claude Code ou Cursor, mais confusa a IA fica? Colar texto cru de arquivos destrói o foco do modelo e consome todos os seus tokens. 🧵

2/7 O problema não é a IA, é o ruído. Se você precisa alterar uma rota, o assistente não precisa ler 500 linhas de métodos utilitários, apenas as assinaturas e as docstrings importam. É aqui que entra o **Semtree**.

3/7 O Semtree usa tree-sitter para indexar linguagens suportadas e extrair símbolos, assinaturas e docstrings. O resultado é um índice estrutural local consultável por nome, assinatura e documentação.

4/7 O resultado precisa ser medido no seu caso. O benchmark local compara volume bruto e contexto selecionado em um projeto sintético; menos tokens pode ajudar em custo e latência, mas não garante precisão nem elimina perda de contexto.

5/7 Além disso, ele inclui metadados importantes que a IA normalmente não vê, como o git blame. O modelo consegue saber quem foi o autor de uma função e quando ela foi modificada, ajudando na compreensão do projeto.

6/7 A integração é instantânea. O Semtree suporta o protocolo MCP nativamente. Com um comando, ele se conecta ao Claude Code ou Cursor e permite que a própria IA consulte os símbolos mantendo-se dentro de um orçamento de tokens seguro.

7/7 Pare de colar arquivos inteiros e comece a enviar contexto inteligente para o seu assistente. O Semtree é open source e fácil de configurar.

Feito por Nikolas de Hor em Goiânia.
Link: https://github.com/DeHor-Labs/semtree

#AI #CodingAssistants #ClaudeCode #Cursor #Python #OpenSource
