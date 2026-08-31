# Privacidade

Última atualização: 31 de agosto de 2026.

## Documentação pública

Este site é uma documentação estática. Ele não oferece cadastro, formulário de contato nem upload de código. A hospedagem e os links externos podem registrar dados técnicos de acesso conforme as políticas dos respectivos provedores.

## Processamento pelo Semtree

Por padrão, o Semtree lê o repositório informado e grava o índice em `.ctx/index.db` na própria máquina. O projeto não inclui telemetria própria nem envia automaticamente o índice para a DeHor Labs.

Quando um assistente de IA usa os trechos devolvidos pelo Semtree, esse conteúdo pode ser processado pelo provedor configurado no assistente. Revise a política e as opções de retenção desse provedor antes de usar código confidencial.

## Controle local

- use regras de exclusão para impedir a indexação de diretórios sensíveis;
- mantenha `.ctx/index.db` fora do Git;
- remova o arquivo local para apagar o índice;
- revise o resultado de `semtree setup --dry-run` antes de gerar configurações.

Questões de segurança podem ser reportadas pelo processo descrito no [repositório](https://github.com/DeHor-Labs/semtree/blob/main/SECURITY.md).
