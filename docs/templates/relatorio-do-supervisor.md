# Modelo: Relatório do Supervisor

O Supervisor usa este relatório para contar a Lauro o que aconteceu num período de trabalho, em blocos de horário. Adaptado do `ampeli-sdd` (formato aprovado por Lauro em 01/11/2026) na etapa 0 da evolução pós-feedback, em 2026-11-03.

## Quando fazer

- Quando Lauro pedir um resumo.
- Ao fim de um bloco longo de trabalho, como uma noite ou um dia de fluxo.
- Depois de uma interrupção da sessão, para mostrar o que estava parado e o que foi retomado.

## Como montar

1. **Horários vêm de registro, não de memória.**
   - Use a hora dos commits deste repositório com `git log --since=<início> --date=format:'%d/%m %H:%M' --format='%ad %s'`.
   - Complete com a hora de merges, campanhas reais e builds Docker, quando importar.
   - O início sem commit fica como "até HHhMM", nunca como hora inventada.
2. **Agrupe em blocos de assunto** (de 30 min a 3 h cada) e dê um nome curto a cada bloco.
3. **Escreva cada bloco pelo resultado para o avaliador.**
   - Diga o que passou a funcionar e onde: branch da versão, `main` local ou Docker.
   - Cite a tarefa (`T63`, `T65`) entre parênteses, nunca como sujeito da frase.
   - SHAs, `request_id` e nomes de classe ficam na tarefa e na evidência, não no relatório.
4. **Mostre intervalos parados ou interrompidos** como bloco próprio, com o que foi retomado.
5. **Feche com "Falta"** (o que resta do plano) **e com "Depende de você"** (ações do responsável, ou "nada").
6. Não ponha segredo, chave, CPF nem dado real de pessoa, nem conteúdo de `discovery/`. Nem caminho pessoal (home, nome de usuário, `AppData`, scratchpad): caminho relativo ou marcador como `<scratchpad da sessão>` (AGENTS.md, "Caminhos pessoais", crítico).
7. Inclua o gasto da campanha real (delta do ledger) ao lado do custo equivalente dos agentes; são controles separados.

## Onde registrar

- Responder no chat.
- Gravar em `docs/relatorios/AAAA-MM-DD-<período>.md` quando cobrir um bloco de trabalho. Pedidos rápidos de "como estamos?" só vão para o chat.

## Modelo

```markdown
# Relatório do Supervisor — <período, ex.: noite de 31/10 a manhã de 01/11/2026>

Período: <início> às <fim>. Base: commits deste repositório <primeiro>..<último>.

- **<início> às <fim> — <assunto do bloco>:** <o que passou a funcionar, onde, (tasks)>.
- **<início> às <fim> — <assunto>:** <...>.
- **<início> às <fim> — parado:** <motivo>; <o que foi retomado>.

**Custo e tempo por tarefa** (de `tools/scripts/medir-agentes.py`, leitura em `docs/wiki/agents/README.md`):

| Tarefa | Modelo do Developer | Passagens dev / rev / qa | Min. ativos | US$ equiv. (agentes) |
| --- | --- | --- | ---: | ---: |

Campanha real da versão: <US$, delta do ledger, teto do plano>. Rodadas de correção pedidas pela revisão: <N>.

**Falta:** <o que resta do plano, na ordem>.

**Depende de você:** <ações do responsável, objetivas> | nada agora.
```
