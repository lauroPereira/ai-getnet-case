# Tarefa: Regressão e candidato dos dois projetos

## Objetivo

Fixar e validar o candidato backend/web com revisão e validação independentes.

## Especificação relacionada

CA-28, CA-32–37, CA-44 e RNF-13; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Tarefas 27–31 completas no escopo aprovado; autorizações de rede e de gasto real separadas.

## Arquivos prováveis

Testes, histórias, manifestos Git/hashes, README/changelog e evidências dos dois projetos.

## Passos

1. Executar validação estrita Python, AppTest, núcleo/jornadas/conversas sem custo e Docker/MCP proporcionais.
2. Fixar candidato dos dois projetos, história, contratos, catálogo, fixtures e ambiente; usar hashes Git ou bytes com algoritmo explícito.
3. Submeter o candidato a revisão independente em contexto novo; correções geram candidato revisado.
4. Após revisão apta, validar pela história; preparar estimativa real por provedor e pedir autorização antes de chamadas pagas.
5. Relatar critérios comprovados, lacunas e retorno; commits, pushes, remotos e tags exigem aceite humano específico da entrega.

## Critérios de conclusão

- [x] Regressão do núcleo e v0.3.0 preservada, com custos/modos separados. *Regressão real do núcleo na v0.6.0.*
- [x] Revisão e validação independentes identificam o mesmo candidato backend/web.
- [x] Nenhum requisito real concluído somente por testes programados; lacunas explícitas.
- [x] APIs dentro de US$5 e autorização adicional própria; nenhum ledger reiniciado.
- [x] Integração/publicação somente após autorização correspondente.

## Resultado

Candidato backend e web fixado com hashes. Suíte estrita final: backend 216 testes, web 14; AppTest e fluxo HTTP sintéticos cobrem login, perfil, conversa, comparação, uso único, administração, catálogo, trace e logout. Sem chamadas pagas nesta versão; JEV real (CA-32) na v0.5.0 e regressão real do núcleo na v0.6.0. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
