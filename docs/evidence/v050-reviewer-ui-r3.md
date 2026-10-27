# Parecer independente — recuperação GET da conversa v0.5.0 (r3)

- Papel: Reviewer independente do Developer, com contexto separado; este parecer não substitui QA.
- Parecer: **apto para revalidação pelo mesmo QA**, restrito à correção da recuperação da conversa no r7.
- Candidato: `v0.5.0-local-r7`; fonte combinada `ad9cf469cd85e44210280df1949ecac766857688a6f1101bb61f8d0e9e9b8d8c`.
- Branches: `codex/v0.5.0-base-versionada`; HEAD-base backend `ea2355b5ba8fa8dcff66200f34461ae063183250`, web `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.

## Integridade e delta r6→r7

Recalculei os mapas após as verificações: backend **46/46** e web **85/85** arquivos coincidem com o manifesto r7, sem divergências. Fingerprints dos mapas backend e web: `cdcf9f3e8203ada5ec0823fc96cfce018c942af6b5a951467e1732efee2d1a20` e `0f37601c0bcf881f65956ac5b876a5369a881d6532e18a14fb25422baacebf4e`. Runtime backend (**128 arquivos**) permanece `22556665c215a837fa5d9cc1b7b8dacd52fa3b06b40ed46e8e1b86b9ef40ce0e`; entradas de build (**129**) permanecem `c74764b0d0932851a123ff8f5f13b11e96e266f8530b2a4ae5ee2e1016d1c3a5`, iguais a r3.

O delta r6→r7 identificado pelos mapas está limitado no web a `app.py`, `tests/test_interface.py` e à fixture `fixtures/conversation-recovery-r2.json`; no backend, somente documentação do plano e tarefas 52/53. Não houve alteração de runtime, build, API ou autenticação.

## Contrato e rederivação

Conferi o payload sanitizado preservado em `.pytest_cache/v050-qa-real-runtime/recovery-get-r2-sanitized.json` sem imprimir os textos das mensagens. O arquivo tem SHA-256 `c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`. O corpo em `response` tem os mesmos nomes de campos de nível superior da fixture. As duas mensagens também têm os mesmos campos e tipos: a pergunta com papel `merchant`, seguida pela resposta com papel `assistant`; ambas incluem `text`, `route`, `status` e `created_at`. A fixture usa IDs e textos sintéticos.

O backend existente confirma essa forma: `GET /v1/conversations/{conversation_id}` verifica o escopo do cliente e retorna `ConversationStore.get` ([v1.py](C:/workspace/ai-getnet-case/src/merchant_assistant/api/v1.py:887), [conversations.py](C:/workspace/ai-getnet-case/src/merchant_assistant/conversations.py:172)). O armazenamento seleciona as mensagens em ordem e inclui `role`, `text`, `route`, `status` e `created_at`. A UI agora localiza a mensagem nova `merchant` a partir do cursor `baseline_message_count`, exige correspondência exata da pergunta e aceita a primeira resposta `assistant` subsequente antes de outra pergunta ([app.py](C:/workspace/ai-getnet-case-web/app.py:60)). Na atualização manual, a resposta correta é anexada ao histórico, a pendência é limpa e `request_id` não é fabricado ([app.py](C:/workspace/ai-getnet-case-web/app.py:273), [app.py](C:/workspace/ai-getnet-case-web/app.py:280), [app.py](C:/workspace/ai-getnet-case-web/app.py:386)). O cliente usa a operação GET existente; seu timeout de 20 segundos não mudou.

## Verificações próprias

- Regressão focal com AppTest: `test_first_send_id_survives_transport_failure_and_manual_get_recovers`, `test_recovery_does_not_present_old_answer_for_pending_question` e `test_conversation_recovery_uses_existing_get_route_only` — **3 passaram**. Cobrem ausência de POST automática, 404, GET sem resposta, GET com timeout, histórico antigo, GET repetido, uso da rota existente e renderização da fixture sintética.
- Reprodução independente temporária em `.pytest_cache/reviewer_ui_r7_realshape.py`, com basetemp novo em `.pytest_cache/reviewer-ui-r7-realshape-20261027` — **1 passou**. Usei a resposta `response` do payload sanitizado real como corpo de GET em `httpx.MockTransport`; a POST simulada falhou com `ReadTimeout`. A UI preservou a pergunta pendente até o GET, então exibiu a resposta capturada, limpou a pendência, manteve `latest_run=None` e marcou recuperação sem request ID. O transporte observou exatamente uma POST original e um GET; rerun após a recuperação não fez chamada adicional.
- Ruff externo (`ruff check app.py tests/test_interface.py`) — **All checks passed**. O cache do Ruff foi direcionado a `.pytest_cache` após a tentativa inicial no cache padrão ser negada pelo sistema de arquivos.
- Não repeti a suíte web completa nem testes backend: o escopo é o delta de recuperação da UI e os mapas confirmam runtime/build backend sem alteração.

## Encaminhamento e limites

Não encontrei defeito restante neste delta. O mesmo QA pode repetir a recuperação com o cenário real/modelo já preparado, preservando a campanha existente; esta revisão não declara cobertura restante concluída, não autoriza release e não substitui QA. Nenhum serviço QA, endpoint histórico, provedor, API real, ledger ou guarda foi acessado nesta revisão. Não foram alterados produto, testes versionados, contrato ou política; temporários próprios permaneceram sob `.pytest_cache`.
