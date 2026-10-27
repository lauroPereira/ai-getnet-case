# Tarefa: Preparação independente do projeto web

## Objetivo

Criar a base documental de ai-getnet-case-web por snapshot controlado do template.

## Especificação relacionada

RF-41–43 e decisão 0007; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Aprovação do destino externo e de AGENTS/CLAUDE/cópias geradas descritos na proposta; destino ausente/vazio reconferido.

## Arquivos prováveis

Somente arquivos novos de base em `C:\workspace\ai-getnet-case-web`, conforme proposta.

## Passos

1. Supervisor aplica project-create, confere destino/links e registra hashes/versão da fonte, sem alterar o template.
2. Copiar somente componentes reutilizáveis; adaptar instruções exatamente conforme texto aprovado e criar README próprio.
3. Gerar cópias de skills pelo script do destino e validar estrutura, origem, neutralidade e referências.
4. Preparar SDD próprio da interface e passagem ao Developer; manter sem Git/remoto até autorização de integração inicial.

## Critérios de conclusão

- [x] Nenhum arquivo preexistente sobrescrito; destino/source preservados.
- [x] Nenhum segredo, .git, discovery, docs/raw ou conteúdo real de outro projeto copiado.
- [x] Manifesto/origem com versão/hashes e adaptações; skills sincronizadas verificadas.
- [x] Base distinta de produto; backend acessível exclusivamente por API.

## Validação

Base criada pelo Supervisor após aprovação: template 0.2.0, commit limpo
`7f556a5a8afbaba865e382fb436e96a8be5b6886`, 47 arquivos-fonte identificados,
54 arquivos iniciais e 18 cópias geradas (9 skills). `validate-project.ps1`,
`validate-agent-flow.ps1` e validação Python estrutural padrão aprovados.
Não são testes do produto. Fonte reconferida sem mudança, sem Git ou .env
no destino. [Manifesto de base](../evidence/v040-base-web.json).

## Status

Concluída: base documental preparada e validada; produto segue para o Developer.
