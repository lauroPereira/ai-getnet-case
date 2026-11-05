# Relatório do Supervisor — 04/11/2026

Retomada da v0.8.0 do case Getnet no Codex, em São Paulo, de 04/11 até 00h17 de 05/11 para validar o último ajuste e registrar a entrega. A v0.8.0 permanece em QA. A sessão foi encerrada a pedido do responsável.

## Períodos

- **Manhã.** Correção e revisão da jornada Visa, integração local da avaliação e desenvolvimento da campanha com ledger persistente.
- **14h03 a 16h12.** A prova da estimativa passou em revisão, a suíte aptou o candidato inicial e a amostragem mediu um custo acima do saldo disponível.
- **16h33 a 20h24.** A extensão de teto foi revisada e aplicada. A primeira fase D12 concluiu e parou na reprovação das jornadas de negócio.
- **23h07 a 00h17.** Recuperação das traces, triagem e correções T74. A suíte detectou a cópia de rótulos desatualizada no catálogo. O espelhamento passou em revisão e a última execução da suíte passou integralmente.

## Done

| Frente | Resultado |
| --- | --- |
| T71 e T72b | Revisão da calibração apta. A jornada de habilitação Visa passou pela correção e pela revisão independente, e a avaliação foi integrada localmente à branch da versão. |
| T73 | Implementação da campanha com duas fases D12, guarda cumulativa, orçamento fixo por campanha e manifesto de QA. O fluxo excepcional foi revisado em passagens sucessivas e passou a suíte estrita antes de usar os ledgers reais. |
| Orçamento | Teto primário elevado a US$1,70 com backup e histórico preservado. A campanha `v080-qa` foi montada uma única vez com US$1,10 e estimativa revalidada de US$1,03174096. |
| QA real r3 | `f8daab03` executou 44 casos três vezes, com 132 julgamentos completos, e quatro conversas com dez turnos. CA-51 ficou em 9/13, 11/13 e 10/13 ante mínimo de 12/13. As conversas passaram 3/4. |
| Triagem T74 | 132 traces recuperadas do runtime local, com máximo de dois saltos e origem das decisões gravada. O replay offline das 39 respostas das jornadas passou de 30/39 para 39/39 com os rótulos revistos. O parecer real r3 e seus julgamentos foram preservados. |
| Correções T74 | Tratamento da confirmação isolada, instrução de procedimento no Knowledge após Support, controle do fallback web e evidência do protocolo para o juiz. Os controles negativos da rubrica foram revistos. O catálogo foi sincronizado, a revisão foi apta e a suíte estrita de `4c3c8a9` passou com **1.097 testes**, Ruff e validação de skills. |

[Relatório de retomada](2026-11-04-retomada-codex.md) · [Transição de orçamento](../evidence/v080-orcamento-transicao.md) · [QA r3](../evidence/v080-d12-pre-holdout-r3.md) · [Triagem T74](../evidence/v080-qa-triagem-r4.md) · [Revisão T74](../evidence/v080-reviewer-t74-r2.md)

## Doing no encerramento

Nenhuma execução ativa. O candidato corrigido está fixado e validado offline. A última suíte levou 14 min 06 s de pytest e 14 min 34 s no total. O reteste pago do candidato corrigido ficou pendente. [Manifesto r4](../evidence/v080-candidato-r4.json)

## To do registrado

- Reteste real de **22 casos × 3** e quatro conversas no candidato corrigido. A seleção foi conferida em dry-run. O bloco de `REPLAN-TOOL-DOWN` precisa de conexão recusada apenas para o mock de preços. O limite incremental preparado é US$0,25, dentro do mesmo cap, com saldo reservado para as fases restantes.
- Juiz repetido, smoke Docker, holdout como último passo técnico e CSV de calibração. Integração na `main` depende do fechamento e da calibração humana.
- A avaliação do cliente Claude API/Sonnet 5.5 na aplicação pertence à v0.9.0 depois do QA da v0.8.0.

[Tarefa de revalidação](../tasks/74-correcao-qa-pre-holdout-v080.md) · [Recorte e orçamento](../evidence/v080-revalidacao-orcamento-r4.md)

## Custo da aplicação e tempo

| Medida | Valor |
| --- | ---: |
| Preparação e amostras pré-campanha, incluindo confirmação de preços | US$0,04968577 |
| Campanha pré-holdout, primeira fase D12 | US$0,38283761 |
| Gasto registrado durante o QA, da preparação à parada da campanha | **US$0,43252338** |
| Comprometido total no ledger primário | US$0,94504185 |
| Restante no primário de US$1,70 | US$0,75495815 |
| Restante no cap de US$1,10 | US$0,71716239 |
| Reservas abertas | 0 nos dois ledgers |

A fase D12 levou 24 min 25 s. Seu custo se divide em US$0,31739322 na OpenAI, incluindo embeddings, e US$0,06544439 na DeepSeek. A confirmação das duas jornadas antes da montagem custou US$0,00272923 e está incluída nas amostras. As correções T74 e sua validação offline ficaram sem gasto de provedor da aplicação. Custo e tempo de subagentes estão no arquivo separado de comparação.

No último fechamento, `C:` tinha 7,71 GiB livres. Antes da última suíte, havia 0,99 GB de RAM livre, 11,04 GB de folga virtual e zero alertas recentes de memória.

## Decisões e falhas da execução

- O Supervisor iniciou cedo um piloto Luna em T72b. Seus 8,10 min e US$0,02795 equivalentes ficaram separados da comparação operacional. A análise entregue é retrospectiva, a partir dos registros existentes.
- Uma revisão T73 exibiu duas linhas do holdout em busca ampla. Descartei a passagem e fiz revisão nova com pacote isolado. Na triagem T74, outra busca foi ampla demais e não exibiu linhas do arquivo lacrado. A campanha não executou o holdout.
- O roteiro r3 deixou `REPLAN-TOOL-DOWN` com o mock saudável. As três execuções desse caso ficaram inválidas para CA-49. O JSON da campanha não exportou os campos de trace, mas o runtime os preservou. Recuperei os 132 registros depois.
- Separei a correção da aplicação e a correção da medição em dois Developers, com arquivos distintos. O QA preparou o reteste em paralelo. Com autorização do responsável, troquei a frente de produto para Terra e usei Terra na revisão independente. Os registros de Luna e Terra foram mantidos separados.
- A correção do fallback web usa o sinal de suficiência emitido pelo próprio modelo de busca. Com marcador ausente ou citação inválida, conserva a lacuna. A rubrica determinística cobre frases e negações previstas, e o juiz continua sendo um controle adicional.
- A primeira suíte completa da T74 terminou com 1.096 aprovações e uma falha de espelhamento no catálogo. Sincronizei os rótulos via Developer, confirmei a revisão do delta e rodei novamente no candidato fixo.

## Estado local

| Repositório ou worktree | Branch ou estado | HEAD de produto |
| --- | --- | --- |
| Backend principal | `codex/v0.8.0-replan` | `4c3c8a98ddfc4f7af7bba877177f3479152159b5` |
| Backend estável | `main` | `bd0920a` |
| Web principal | `main` local | `0a8e12f` |
| Time B | `codex/v0.8.0-avaliacao` | `af16869` |
| Time B v0.7.0 | `codex/v0.7.0-ticketing` | `2226d4c` |
| Revisões preexistentes | `review-a`, `review-a2`, `review-web` | `af16869`, `10171c1`, `cd7d55d` |
| T73 r1, r2 e r3 | Worktrees isolados | `60ef1eb`, `9deca61`, `9057aaa` |

Os caminhos, os logs, as bases, os pacotes de revisão e a telemetria bruta estão em um inventário de registros, e a comparação Luna × Sonnet × Opus por papel em um relatório à parte; os dois são material local do responsável (`discovery/relatorios/`), fora do repositório, porque trazem caminhos da máquina e medições de ferramentas que não fazem parte do produto.

## Depende de você

Nenhuma ação para este fechamento. A calibração humana continua como condição da futura integração da v0.8.0.
