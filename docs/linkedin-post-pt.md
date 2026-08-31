# LinkedIn Post: Semtree e a Otimização de Contexto

Seu assistente de código com IA está consumindo tokens demais e entregando respostas confusas?

Muitos desenvolvedores reclamam que, em repositórios grandes, ferramentas como Claude Code ou Cursor começam a ignorar regras, reinventar implementações ou demorar muito para responder. A causa quase sempre é a mesma: contexto inchado.

Fornecer arquivos inteiros de código fonte para a IA processar é ineficiente. A maior parte das linhas lidas são implementações auxiliares que só servem como ruído para a tarefa atual.

Para resolver esse desperdício de contexto, lancei o **Semtree**.

O Semtree é um indexador estrutural que organiza a comunicação entre o seu repositório e o seu assistente de IA. Em vez de entregar arquivos brutos, ele usa análise de AST (via tree-sitter) para extrair símbolos suportados, assinaturas, tipos, docstrings e contexto do Git.

Impacto prático na sua rotina:
✅ **Orçamento explícito:** O contexto selecionado respeita um limite configurável e pode ser comparado com o volume bruto pelo benchmark local.
✅ **Menos texto desnecessário:** A seleção pode reduzir o volume processado, conforme o repositório e a consulta.
✅ **Limites verificáveis:** Redução de tokens não prova precisão; revisão humana e testes continuam necessários.
✅ **Integração explícita:** Claude Code e Cursor podem usar as ferramentas MCP; Copilot e Codex recebem instruções para chamar o contexto pela CLI.

Trabalhar com IA não exige jogar todo o repositório na tela. Exige entregar o contexto certo.

O Semtree é de código aberto e já está disponível para testes. Convido todos a conferir o repositório no GitHub.

---
**Nikolas de Hor**
Desenvolvedor | Goiânia, Brasil
Projeto: https://github.com/DeHor-Labs/semtree

#SoftwareDevelopment #ArtificialIntelligence #ClaudeCode #CursorAI #OpenSource #Produtividade #Semtree
