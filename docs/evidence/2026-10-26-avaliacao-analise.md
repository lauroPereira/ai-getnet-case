# Evidência: avaliação do núcleo (análise das rodadas)

Tarefa: [14](../tasks/14-avaliacao-exemplos-desafio.md). Data: 2026-10-26. Verificação automatizada com o sistema real em processo (`gpt-6-luna`, `text-embedding-3-small`, busca web, Qdrant local, relógio do sistema). Relatório gerado pela última rodada: [2026-10-26-avaliacao-nucleo.md](2026-10-26-avaliacao-nucleo.md) (dados por caso em [JSON](2026-10-26-avaliacao-nucleo.json)).

## Conjunto

- 27 casos: os 10 exemplos do enunciado em inglês (`dev`, usados no desenvolvimento) e 17 reservados (`holdout`): as 10 versões em português, UC-12 (dado sensível), UC-13 (recurso de outro cliente), UC-14 (atendente humano), UC-16 (injeção de instruções), UC-17 (usuário desconhecido), UC-18 (mensagem vaga) e um produto inexistente.
- Verificações automáticas por caso: rota aceita, status, idioma, ferramentas esperadas, valores obrigatórios (em centavos), conteúdo obrigatório, conteúdo proibido, presença de fontes e ausência de violação na guarda de saída.
- Rubrica por modelo (`judge` v2, `gpt-6-luna`): responde à pergunta, clareza e tom, honestidade, de 1 a 5. É julgamento de modelo, não revisão humana.

## Rodadas

| Rodada | Mudança antes da rodada | Aprovados | Dev | Holdout | Rubrica (resp. / clareza / honest.) | p50 / p95 | Custo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | — | 27/27 | 10/10 | 17/17 | 4,19 / 4,56 / 4,15 (juiz v1) | 7,4 s / 14,2 s | US$0,057 |
| 2 | Texto de conta não localizada; juiz v2 | 25/27 | 10/10 | 15/17 | 4,26 / 4,56 / 4,04 | 8,8 s / 20,3 s | US$0,053 |
| 3 | `support` v3: regras de encaminhamento | 27/27* | 10/10 | 17/17 | 4,48 / 4,70 / 4,22 | 7,8 s / 15,7 s | US$0,053 |

\* Na rodada 3, o EX03 reprovou de início por um falso negativo do avaliador: a resposta dizia "have not yet been confirmed" e a verificação procurava "not been confirmed". A lista de expressões do EX03 e do PT03 foi ampliada e a rodada foi recalculada sem novas chamadas.

## O que as rodadas mostraram

- **Não determinismo:** a mesma configuração passou de 27/27 para 25/27 entre as rodadas 1 e 2. As duas falhas (PT05 e UC-13) foram encaminhamentos para humano cedo demais. O `support` v3 deixou explícito quando encaminhar: falha de ferramenta essencial, dados contraditórios ou pedido do lojista; nunca no primeiro contato sobre a maquininha nem por acesso negado a recurso de outro cliente.
- **Rubrica:** as notas baixas recorrentes são limitações do juiz, que só vê o título das fontes. Ele leu "Descontinuação dos pagamentos via WhatsApp Business" como contradição, embora a página oriente vender pelo WhatsApp com o Link de Pagamento; também desconfiou de valores vindos das ferramentas até a v2 explicar a origem "(your account)". As notas servem para triagem, não como medida de fidelidade.
- **Fidelidade:** a guarda de saída não bloqueou nenhum valor nas 81 respostas das três rodadas. Valores, datas e percentuais citados vieram das ferramentas ou dos trechos recuperados.
- **Isolamento:** UC-13 nunca expôs o valor do recebível de outro cliente.
- **Custo e latência:** cerca de US$0,002 por caso; as quatro perguntas com busca web (tempo e câmbio, nos dois idiomas) somam cerca de 80% do custo. Latência dominada pelas chamadas sequenciais de modelo (Router, especialista(s), Personality).

## Limitações

- Amostra pequena (27 casos). Os ajustes entre rodadas olharam casos do holdout (UC-17, PT05, UC-13), que deixam de ser reserva pura para essas mudanças.
- O conteúdo das respostas de busca web depende do momento da consulta; as verificações desses casos são deliberadamente amplas.
- Revisão humana de amostra: pendente, a cargo do responsável.
