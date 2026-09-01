# X Thread: Semtree e o Contexto para IAs 🌳🚀

1/7 Enviar arquivos inteiros ao Claude Code ou Cursor pode ocupar o orçamento de contexto com código que não participa da tarefa. 🧵

2/7 Em uma alteração localizada, assinaturas e docstrings podem ajudar a encontrar os pontos relevantes antes da leitura dos arquivos completos. É aqui que entra o **Semtree**.

3/7 O Semtree usa tree-sitter para indexar linguagens suportadas e extrair símbolos, assinaturas e docstrings. O resultado é um índice estrutural local consultável por nome, assinatura e documentação.

4/7 O resultado precisa ser medido no seu caso. O benchmark local compara volume bruto e contexto selecionado em um projeto sintético; menos tokens pode ajudar em custo e latência, mas não garante precisão nem elimina perda de contexto.

5/7 Além disso, ele inclui metadados importantes que a IA normalmente não vê, como o git blame. O modelo consegue saber quem foi o autor de uma função e quando ela foi modificada, ajudando na compreensão do projeto.

6/7 O Semtree oferece setup para Claude Code e Cursor via MCP. O comando pode gravar a configuração do projeto; use `--dry-run` para inspecionar as mudanças antes.

7/7 O Semtree é open source: você pode testar a seleção de contexto, medir o volume e decidir quando ainda precisa abrir os arquivos completos.

Feito por Nikolas de Hor em Goiânia.
Link: https://github.com/DeHor-Labs/semtree

#AI #CodingAssistants #ClaudeCode #Cursor #Python #OpenSource
