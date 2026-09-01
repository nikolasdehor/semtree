# LinkedIn Post: Semtree e a Seleção de Contexto

Quanto contexto do repositório o seu assistente de código com IA recebe em cada tarefa?

Em repositórios grandes, fornecer mais arquivos do que a tarefa exige pode ocupar o orçamento de contexto sem melhorar a resposta.

Dependendo da consulta, arquivos inteiros incluem implementações auxiliares que não participam da mudança em análise.

Para tornar esse volume observável e configurável, lancei o **Semtree**.

O Semtree é um indexador estrutural. Com as gramáticas opcionais instaladas, ele usa árvores sintáticas do tree-sitter para extrair declarações suportadas, assinaturas, docstrings disponíveis e metadados do Git. Sem elas, algumas linguagens usam fallbacks limitados por expressões regulares.

O que é verificável:
✅ **Orçamento explícito:** O contexto selecionado respeita um limite configurável e pode ser comparado com o volume bruto pelo benchmark local.
✅ **Menos texto desnecessário:** A seleção pode reduzir o volume processado, conforme o repositório e a consulta.
✅ **Limites verificáveis:** Redução de tokens não prova precisão; revisão humana e testes continuam necessários.
✅ **Integração explícita:** Claude Code e Cursor podem usar as ferramentas MCP; Copilot e Codex recebem instruções para chamar o contexto pela CLI.

É possível inspecionar o recorte e o volume antes de decidir se eles atendem à tarefa.

O Semtree é de código aberto e já está disponível para testes. Convido todos a conferir o repositório no GitHub.

---
**Nikolas de Hor**
Desenvolvedor | Goiânia, Brasil
Projeto: https://github.com/DeHor-Labs/semtree

#SoftwareDevelopment #ArtificialIntelligence #ClaudeCode #CursorAI #OpenSource #Produtividade #Semtree
