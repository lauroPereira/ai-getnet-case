# Preparação do QA v0.6.0: efeito da documentação (bloco D) e roteiro operacional

Preparado pelo Developer em 2026-10-27, antes de qualquer edição real da base. Nenhuma chamada paga foi feita para este documento. Fontes: [spec v0.6.0, bloco D](../specs/fechamento-v060.md#d-efeito-da-documentação-no-comportamento), [tarefa 57](../tasks/57-efeito-documentacao-v060.md) e [história v1](../historias/fechamento-v060.md).

## Diferença esperada (fixada antes da edição)

| Item | V1 (documento atual `KB-DEMO-DEVICES-001`) | V2 (rascunho preparado) |
| --- | --- | --- |
| Procedimento | Diagnóstico de conectividade com `get_device_status`; alternativa de venda citada de forma genérica ("depende dos produtos habilitados") | Acrescenta a seção "Alternativa de venda com a maquininha sem conexão": consultar `get_contract_snapshot` **antes** de oferecer o Link de Pagamento e só oferecer se `link_de_pagamento` constar nos produtos contratados |
| Ferramenta observável | `get_contract_snapshot` **não** aparece nas etapas | `get_contract_snapshot` aparece nas etapas depois de `get_device_status` |
| Fato e resposta | Resposta não condiciona o Link de Pagamento aos produtos do contrato | Resposta só oferece o Link de Pagamento quando o fato do contrato o lista (o lojista sintético `cliente1988` tem `link_de_pagamento`) |
| Evidência no trace | Versão `kb_initial` (ou a ativa no início) | Versão candidata ativada; trecho da nova seção nos `hits` da etapa Knowledge |

Redação diferente ou um marcador isolado não contam como mudança: o critério é a ferramenta chamada, o fato do contrato e a condição da oferta, com trecho e versão no trace.

Limites da edição: a V2 só acrescenta texto (sem remoção), não cria prazo, valor, taxa ou percentual, não altera regra financeira e não concede ferramenta. `get_contract_snapshot` já pertence à lista autorizada do Customer Support (`tools/registry.py`). Esses limites são verificados por `tests/integration/test_v060_doc_effect.py::test_v2_text_adds_no_deadline_amount_or_new_tool`.

## Artefatos

- Pergunta (catálogo, `data/scenarios/catalog.json`): `SC-DOC-EFFECT` — "Minha maquininha não conecta na internet. Posso vender por Link de Pagamento enquanto isso?" Rota esperada `knowledge_and_support`; rótulos independentes da versão (`get_device_status`, `answered`, fontes).
- Texto completo da V2 para colar no editor da Administração: `data/scenarios/kb-demo-devices-v2.md` (corpo do documento, sem front matter, idêntico ao publicado mais a seção nova).
- Teste sem custo: `tests/integration/test_v060_doc_effect.py` (política programada que aplica o procedimento recuperado, embeddings falsos, Qdrant em memória). Prova o caminho dos dados (documento → trecho recuperado → procedimento → ferramenta → fato → resposta, com versão no trace) e o retorno; **não** prova o comportamento do modelo real.

## Roteiro do QA real (campanha `v060-qa`)

Pré-condições: candidato fixado por hashes; campanha `FixedBudgetGuard` `v060-qa` com teto de US$0,50 montada uma única vez e combinada com o ledger primário (`FixedBudgetGuard` aceita até US$0,50 a partir desta versão); perfil Referência v1 publicado; Router LLM; sessão admin com cliente sintético `cliente1988`.

1. **V1 primeiro.** Em Atendimento, escolher o cenário "Maquininha sem conexão e alternativa de venda", perfil Referência, Router LLM, e enviar. Em Resultados, conferir rota `knowledge_and_support`, versão da base ativa, etapas, ferramentas e trechos.
   - Se a rota não for `knowledge_and_support`, ajustar a **pergunta** (não o critério) num novo cenário, registrar e repetir antes de editar.
   - Se `get_contract_snapshot` **já** aparecer na V1, a diferença prevista já ocorre: redefinir e registrar outra diferença verificável antes de qualquer edição (por exemplo, condicionar a oferta a um fato de outra ferramenta já autorizada), e só então seguir.
2. **Editar.** Administração → Base de conhecimento → documento "Dispositivos e conectividade" → colar o texto de `kb-demo-devices-v2.md` → Salvar rascunho → conferir que o diff só acrescenta linhas.
3. **Candidata.** Estimar candidata → conferir estimativa → confirmar → Construir candidata → Testar candidata (teto informado) → Ativar versão.
4. **V2.** Nova conversa (recarregar a página ou encerrar/entrar), mesmo cenário, perfil, Router e prompts. Conferir em Resultados: versão da base = candidata; trecho da seção nova nos `hits`; `get_contract_snapshot` nas etapas; fonte "Contracted products (your account)"; resposta oferece o Link de Pagamento condicionado ao contrato.
5. **Retorno.** Administração → Retornar à versão anterior (confirmar). Nova conversa, mesmo cenário: versão anterior no trace, sem `get_contract_snapshot`, comportamento da V1.
6. **Repetição pequena.** Uma repetição por versão (V1, V2, V1 restaurada) se o saldo permitir; registrar cada `request_id`, versão da base, ferramentas e custo. Variação do modelo não muda o critério: a diferença é decidida pela ferramenta e pelo fato.
7. **Registro.** Anotar no QA v0.6.0 os `request_id`, as versões, as ferramentas, os trechos e os custos; uma sonda inconclusiva não converte o aceite da v0.5.0 em reprovação.

Estimativa de custo do bloco D (plano): ≈ US$0,02, dentro da campanha.

## Outros pontos para o QA

- `docker compose config` não foi executado pelo Developer (o arquivo `.env` local não podia ser lido); conferir que a API publica somente `127.0.0.1:8000`.
- Comparação de perfis roda em thread do processo da API: atualizar por "Atualizar comparação" (GET). Reinício da API durante a comparação a marca como `failed` (`interrupted`) na próxima leitura.
- Limite por sessão demo (`DEMO_SESSION_MESSAGE_LIMIT`, padrão 20) conta toda ação paga (mensagens, execuções novas de comparação, comparação de Routers e avaliação por IA), sem contar recusas sem inferência; recusa com `429 demo_message_limit_reached`.
- R2-04 (I/O do Qdrant dentro de `BEGIN IMMEDIATE` na ativação) segue como risco aceito: observar latência de mensagens e `/ready` durante ativação/retorno.
