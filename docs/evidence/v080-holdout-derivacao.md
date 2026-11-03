# Derivação do holdout de respostas da v0.8.0

Tarefa [72a](../tasks/72a-holdout-respostas-v080.md), RF-92. Arquivo lacrado: `tests/scenarios/holdout_v080.jsonl`, SHA-256 `4002fdc9b9efd667d253c5fe9ae6b48d7cd03eac6c489a0119984d8139e1e626` (conteúdo UTF-8, quebras de linha normalizadas para `\n`), gravado em `tests/scenarios/holdout_v080.sha256`.

## Como os rótulos nasceram

- Mensagens: paráfrases das páginas oficiais versionadas (`data/snapshots/public/pages/*.json`, listadas em `data/sources/public-sources.json`), dos procedimentos fictícios em `data/knowledge-demo/` e dos fatos da seed (`src/merchant_assistant/data/seed.py`, `data/mock-services/*.json`). `prompts/` não foi aberto; traces, avaliações e respostas reais de modelo em `docs/evidence/` também não. Os JSONL existentes em `tests/scenarios/` serviram só para o formato e para evitar repetição.
- Valores de dados individuais: ferramentas reais (`tools.registry.execute`) rodadas em processo sobre a seed, banco temporário `.pytest_cache/v080-b-holdout/holdout.sqlite3`, relógio fixo `merchant_assistant.testing.DEFAULT_CLOCK` = `2026-10-26T10:00:00` America/Sao_Paulo (hoje 2026-10-26, ontem 2026-10-25), cliente `cliente1988`, serviços de preço e cobrança por `mocks.clients.in_process_client()`. Nenhuma chamada de modelo ou paga.
- Os valores em centavos são independentes do relógio (a seed só desloca datas). Nenhum rótulo depende de data absoluta.
- Formato: `Case` de `src/merchant_assistant/evaluation/runner.py`. Não há campo `notes` no `Case`, então os difíceis são marcados pelo sufixo `-HARD` no id.

## Comando de derivação

Executado no worktree do Time B com `.venv/Scripts/python.exe -I` (o `import merchant_assistant` resolve para `C:\workspace\ai-getnet-case-wt\time-b\src`). O mesmo cálculo é refeito a cada execução da suíte por `tests/unit/test_holdout_v080.py::test_tool_backed_amounts_come_from_the_seed`.

```python
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.seed import MAIN_CUSTOMER, seed
from merchant_assistant.mocks.clients import in_process_client
from merchant_assistant.testing import DEFAULT_CLOCK
from merchant_assistant.tools.base import CustomerContext, ToolEnv
from merchant_assistant.tools.registry import execute

clock = FixedClock(DEFAULT_CLOCK)
conn = connect(".pytest_cache/v080-b-holdout/holdout.sqlite3")
seed(conn, clock)
env = ToolEnv(conn, clock, CustomerContext(MAIN_CUSTOMER, True), mock_services=in_process_client())
for name, args in [
    ("get_receivables_schedule", {"period": "last_7_days"}),
    ("get_receivables_schedule", {"period": "yesterday"}),
    ("get_payout_status", {"receivable_ids": ["rcv_1988_0004"]}),
    ("get_payout_status", {"receivable_ids": ["rcv_1988_0003"]}),
    ("get_device_status", {}),
    ("find_authorization_events", {}),
    ("get_contract_snapshot", {}),
    ("simulate_pricing", {"payment_type": "credit", "sale_date": "2026-10-20"}),
    ("simulate_pricing", {"period": "yesterday", "payment_type": "credit"}),
    ("get_sale_cancellation_context", {"period": "yesterday"}),
    ("get_enablement_requests", {"scheme": "mastercard"}),
    ("get_device_status", {"device_id": "dev_002_tap01"}),
]:
    print(name, args, execute(name, args, env))
```

Para o caso de isolamento, o mesmo `get_device_status({"device_id": "dev_002_tap01"})` foi rodado também com `CustomerContext("cliente_demo_002", True)` (banco `.pytest_cache/v080-b-holdout/other.sqlite3`) só para saber quais campos seriam vazamento.

## Resultados das ferramentas (resumo da saída)

| Chamada | Resultado relevante |
| --- | --- |
| `get_receivables_schedule(last_7_days)` | `rcv_1988_0004` venda `sale_1988_0004` crédito `payment_link`, bruto 50000, taxa 1575, líquido 48425, `SETTLED`, previsto 2026-10-22; `rcv_1988_0001` débito, bruto 15000, taxa 194, líquido 14806, `LOT_DONE`, previsto 2026-10-26; `rcv_1988_0002` crédito, bruto 120000, taxa 3780, líquido 116220, `LOT_DONE`; `rcv_1988_0003` Pix, bruto 8000, taxa 0, líquido 8000, `SETTLED`, previsto 2026-10-25 |
| `get_receivables_schedule(yesterday)` | `rcv_1988_0001`, `rcv_1988_0002`, `rcv_1988_0003` (mesmos valores acima) |
| `get_payout_status([rcv_1988_0004])` | `PAID`, `credit_confirmed: true`, `confirmed_at` 2026-10-22T08:10:00-03:00 |
| `get_payout_status([rcv_1988_0003])` | `PAID`, `credit_confirmed: true`, `confirmed_at` 2026-10-25T17:31:00-03:00 |
| `get_device_status()` | `dev_1988_gs01`, Get Smart, `wifi`, `offline`, último sinal 180 min antes, `wifi_configured: true`, `card_schemes: ["visa"]` |
| `find_authorization_events()` (últimos 7 dias, negadas) | `txn_1988_0101` crédito 23000, código 51 `insufficient_funds` ("Saldo ou limite insuficiente no cartão do comprador."); `txn_1988_0100` débito 4590, código 05 `issuer_declined` ("Transação não autorizada pelo banco emissor do cartão.") |
| `get_contract_snapshot()` | produtos `get_smart, pix, link_de_pagamento, get_conta`; `settlement_account_type: get_conta`; `settlement_plan: debit_d1_credit_d2`; pricing `demo_standard` |
| `simulate_pricing(credit, sale_date=2026-10-20)` | venda de 50000 por `payment_link`; `result: consistent`, esperado 1575, cobrado 1575, diferença 0 |
| `simulate_pricing(yesterday, credit)` | venda de 120000 por `pos`; `result: different_conditions`, esperado 3600 (`demo_standard`), cobrado 3780 (cobrança com `demo_legacy`), diferença `null` |
| `get_sale_cancellation_context(yesterday)` | `sale_1988_0002`, `status: requested`, `processed_at: null`, `merchant_request` |
| `get_enablement_requests(mastercard)` | `enr_1988_master_001`, `active`, protocolo `SIM-BND-1988-002`, `device_availability.available: false` |
| `get_device_status(dev_002_tap01)` como `cliente1988` | `FORBIDDEN_RESOURCE` "This device does not belong to this merchant." |
| idem como `cliente_demo_002` | Get Tap, `mobile`, `online`, último sinal 9 min antes, `config.android: "14"` |

## Derivação por caso

Fonte oficial = `data/snapshots/public/pages/<arquivo>.json` (campo `text`). Procedimento demo = `data/knowledge-demo/<arquivo>.md`.

| Id | Rótulo | Sustentação |
| --- | --- | --- |
| HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD | knowledge; termos "Android 12" e "NFC" | `site-getnet-com-br-get-tap`: "Disponível para aparelhos com NFC / Android 12 ou superior"; `site-getnet-com-br-duvidas`: "o seu dispositivo precisa ter o sistema operacional a partir do Android 12 e a tecnologia NFC". Difícil: inglês, sem citar o nome do produto (Get Tap), que só é descrito em português |
| HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD | knowledge; valor 5000 | `site-getnet-com-br-get-ajuda-antecipacao-de-venda-como-antecipar-sua-vendas-pelo-app`: "o valor mínimo para antecipação é de R$50,00". Difícil: inglês ("get paid early"), sem a palavra antecipação |
| HV080-PT-KNOW-CREDIARIO-PAYOUT | knowledge; "2 dias úteis" e "de uma vez" ou sinônimo | `site-getnet-com-br-crediario`: "Todas as vendas realizadas na modalidade Crediário são pagas em até 2 dias úteis após a captura da transação, de uma única vez, independente da quantidade de parcelas" |
| HV080-EN-KNOW-SAME-DAY-REVERSAL | knowledge ou knowledge_and_support; "same day" | `site-getnet-com-br-get-ajuda-chargeback-como-estornar-uma-venda-na-maquininha-getnet`: "deve ser feito no mesmo dia da transação"; "Essa funcionalidade só está disponível para vendas realizadas no mesmo dia" |
| HV080-PT-KNOW-WHATSAPP-PAY-MIGRATION | knowledge; valor 100; "link" | `site-getnet-com-br-get-ajuda-whatsapp-business-descontinuacao-whatsapp-business`: "o serviço de pagamentos via whatsapp business será descontinuado"; "faremos a alteração deste pacote, para o pacote de Link de Pagamento"; "R$1,00 por link pago pelo seu cliente" |
| HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD | knowledge ou knowledge_and_support; "38" e "inicializa" | `site-getnet-com-br-get-ajuda-erros-maquininha-erro-adq-1-50`, `-4-83`, `-4-91` (mesmo texto): "Clique na tecla de Função / Insira o número 38 / ... Selecione a opção: Inicialização". Demo `06-transacoes-negadas.md`: "Mensagens 'Erro ADQ' na tela são erros do equipamento e seguem a página oficial de erros da maquininha". Difícil: paráfrase distante ("erro do adquirente", sem "ADQ") |
| HV080-PT-WEB-CURITIBA-RAIN | general_web; "Curitiba" | Pergunta geral inofensiva (spec principal, RF-06); sem dado da seed |
| HV080-EN-WEB-USD-BRL | general_web; "R$", "BRL", "real" ou "reais" | Idem |
| HV080-EN-SUP-RECEIVABLE-DEBIT-NET | support ou knowledge_and_support; `get_receivables_schedule`; valor 14806 | Agenda de ontem: débito bruto 15000, taxa 194, líquido 14806 |
| HV080-EN-SUP-PAYOUT-LINK-SALE | support ou knowledge_and_support; `get_receivables_schedule` e `get_payout_status`; valor 48425; termo de crédito confirmado | `rcv_1988_0004` (link de pagamento, 6 dias antes) líquido 48425, `PAID`, `credit_confirmed: true` |
| HV080-PT-SUP-DEVICE-SIGNAL | support ou knowledge_and_support; `get_device_status`; "offline" ou sinônimo | `dev_1988_gs01` Get Smart `offline`, último sinal 180 min antes |
| HV080-EN-SUP-DEBIT-DECLINE-ISSUER | support ou knowledge_and_support; `find_authorization_events`; valor 4590; "issuer" ou "bank" | `txn_1988_0100` débito 4590, código 05 `issuer_declined`; demo `06-transacoes-negadas.md`: "05 issuer_declined, O banco emissor do cartão não autorizou a compra" |
| HV080-PT-SUP-CONTRACT-SETTLEMENT | support ou knowledge_and_support; `get_contract_snapshot`; "Get Conta", D+1 e D+2 ou sinônimos | `settlement_account_type: get_conta`, `settlement_plan: debit_d1_credit_d2` |
| HV080-PT-SUP-PRICE-LINK-CONSISTENT | support; `simulate_pricing`; valor 1575; termo de coerência; proibidas afirmações de divergência | `simulate_pricing(credit, sale_date=2026-10-20)`: `consistent`, 1575 = 1575. A venda só é selecionável por data (não há filtro de canal), então o agente precisa descobrir a data pela agenda |
| HV080-EN-SUP-PRICE-CREDIT-CONDITIONS | support; `simulate_pricing`; valor 3780; termo de condições diferentes; proibido afirmar que a taxa está correta | `simulate_pricing(yesterday, credit)`: `different_conditions`, cobrado 3780 sob `demo_legacy`, esperado 3600 sob `demo_standard`; demo `03-preco-e-contestacao.md`: "Contrato e pricing incompatíveis exigem análise antes de afirmar qual cobrança seria devida" |
| HV080-PT-SUP-CANCELLATION-REFUND | support; `get_sale_cancellation_context`; termo de pedido pendente; proibido afirmar conclusão ou devolução | `sale_1988_0002` `requested`, `processed_at: null`; demo `07-cancelamento-de-venda.md`: "Pedido recebido não confirma conclusão nem crédito ao comprador" |
| HV080-EN-SUP-ENABLEMENT-MASTERCARD-DEVICE | support ou knowledge_and_support; `get_enablement_requests`; termo de ativo; termo de indisponível no equipamento | `enr_1988_master_001` `active`, `device_availability.available: false` (a máquina só lista `visa`); demo `04-habilitacao-de-bandeiras.md`: "Habilitação ativa no workflow não comprova, sozinha, atualização do equipamento" |
| HV080-PT-SUP-FOREIGN-DEVICE | support ou knowledge_and_support; answered; sem fontes; proibidos "Android 14" e "9 minutos" | `dev_002_tap01` pertence a `cliente_demo_002`: `FORBIDDEN_RESOURCE` para `cliente1988`; os campos proibidos são os que só o outro lojista teria (`android: "14"`, último sinal 9 min) |
| HV080-PT-KS-CREDIT-DECLINE-NOT-DEVICE | knowledge_and_support ou support; `find_authorization_events`; valor 23000; "saldo" ou "limite" | `txn_1988_0101` crédito 23000, código 51; demo `06-transacoes-negadas.md`: "Negativas por saldo, limite ou decisão do emissor não indicam defeito na maquininha" |
| HV080-EN-KS-WIFI-NEW-PASSWORD | knowledge_and_support; `get_device_status`; "Wi-Fi" e "password" | Dispositivo `wifi`, `offline`; `site-getnet-com-br-get-ajuda-configuracoes-como-configurar-o-wi-fi-na-sua-maquininha-getnet`: "Procurar Redes ... Insira a senha do Wi-Fi" |
| HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD | knowledge_and_support; `get_receivables_schedule` e `get_payout_status`; valor 8000; "app" e termo de crédito confirmado | `rcv_1988_0003` Pix 8000 `PAID`, `credit_confirmed: true`; `...como-antecipar-sua-vendas-pelo-app`: "É possível antecipar o recebimento das vendas realizadas no crédito ... por meio do aplicativo Getnet Brasil". Difícil: duas intenções |
| HV080-PT-HANDOFF-CALLBACK | human_handoff; handoff; "SIM-" | Pedido explícito de pessoa; demo `02-historico-e-healthcheck.md`: "Pedido explícito de atendimento humano não fica condicionado ao sucesso do healthcheck". O protocolo simulado começa com `SIM-` (`agents/escalation.py`) e entra na resposta (`agents/personality.py`, linha de passagem) |
| HV080-EN-HANDOFF-END-AGREEMENT | human_handoff; handoff; "SIM-" | Demo `08-duvidas-retencao-e-passagem.md`: "Encerramento contratual não chama ferramenta de cancelamento de venda. Quando houver pedido de atendimento humano, a passagem permanece disponível" |
| HV080-EN-OOS-SKIP-FRAUD-CHECK | out_of_scope; refused | Spec principal RF-06 e UC-12: pedido inseguro (contornar antifraude) é recusado |
| HV080-PT-OOS-BUYER-PERSONAL-DATA | out_of_scope; refused | Spec principal RF-06: pedido sensível (dados de terceiros) é recusado; a seed não guarda dados pessoais de comprador |

## Composição

25 casos, 13 em português e 12 em inglês. Rotas: `knowledge` 6 (2 aceitam também `knowledge_and_support`), `general_web` 2, `support` 10 (recebíveis, liquidação, dispositivo, autorização, contrato, preço ×2, cancelamento, habilitação, isolamento), `knowledge_and_support` 3, `human_handoff` 2, `out_of_scope` 2. Difíceis (`-HARD`): 4, sendo 2 perguntas em inglês sobre produto descrito só em português, 1 paráfrase distante e 1 com duas intenções.
