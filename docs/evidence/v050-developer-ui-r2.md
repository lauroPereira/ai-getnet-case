# Passagem Developer — recuperação manual do chat v0.5 (UI r2)

**Estado:** implementação local concluída; revisão independente e QA no candidato r5 pendentes. Não é aceite de QA nem decisão de release.

## Identificação e escopo

- Tarefa: `docs/tasks/50-recuperacao-manual-chat-v050.md`, continuação do defeito48.
- Candidato base: r4, `docs/evidence/v050-candidato-r4.json`; fonte web de referência `ddabeba4620776c37a93460c983c702c7522e10c234cd5230744e83e7ac08432`.
- Web: branch `codex/v0.5.0-base-versionada`, HEAD base `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Código alterado nesta tarefa: `app.py`, `src/getnet_web/api.py` e `tests/test_interface.py`. Os bytes r4 foram preservados em `.pytest_cache/v050-r5-recovery-originals/`.
- Backend, contrato/OpenAPI, timeout de 20 s, autenticação, permissões, credenciais, runtime e guardas não foram alterados. Backend não foi retestado.
- Candidato r5 não foi fixado pelo Developer.

## Comportamento implementado

- Antes de um POST real, a UI cria um ID `conv_<20 hex>` que satisfaz o padrão aceito existente `^conv_[A-Za-z0-9]{8,40}$`, inclui-o no campo já aceito `conversation_id` e guarda pergunta, ID e contagem-base das mensagens persistidas no backend.
- Se o transporte falhar, a tela mantém pergunta e conversa pendentes, apresenta estado recuperável sem traceback e desabilita novos envios enquanto a pendência existir. O fluxo de envio por comparação usa o mesmo helper.
- “Atualizar conversa” só aparece como ação no modo Real (API) e chama `APIClient.conversation()`, o GET existente `/v1/conversations/{conversation_id}`. Não chama POST, modelo ou embedding. GET 404, erro de transporte, conversa sem mensagens novas ou conversa ainda sem resposta mantêm a pendência e mostram estado útil.
- A recuperação considera apenas mensagens após a contagem-base, exige a pergunta pendente e uma mensagem `assistant` subsequente antes de outra mensagem de usuário. Histórico antigo permanece no chat e não é apresentado como resposta nova. A contagem-base acompanha apenas mensagens confirmadas pelo backend, separada do histórico local de modos Simulado/Gravado.
- Ao recuperar a resposta, a UI acrescenta a pergunta e resposta ao histórico. Como a conversa não retorna `request_id` por mensagem, `latest_run` não é inventado nem sobrescrito; a tela informa que o ID de execução não está disponível. A inspeção normal continua quando a resposta original inclui um request ID.
- Em falhas de transporte, o cliente registra somente nome da operação, duração em ms e classe da exceção. Não registra URL, query, corpo, pergunta, token ou credencial. Timeout e política de retry não mudaram.

## Validação observada

Todos os testes usaram `AppTest`, `httpx.MockTransport` ou cliente falso. Nenhum serviço local real foi acessado; não houve inferência, embedding, bootstrap, POST pago ou leitura de ledger.

- Regressões focadas — `pytest tests/test_interface.py -k 'transport_failure_logs or first_send_id_survives or recovery_does_not_present or conversation_recovery_uses_existing_get_route_only' --basetemp=.pytest_cache/v050-r5-target5 -q`: **4 passaram, 16 filtrados**. Cobrem ID antes do primeiro POST, POST único, transporte interrompido, GET 404/timeout, conversa ainda sem resposta, recuperação posterior, preservação de histórico antigo, troca para modo Simulado sem GET e endpoint de recuperação GET-only.
- `tools/scripts/lint_and_tests.py --strict`, `.venv-v040`: **20/20 testes passaram**; estrutura e skills passaram. O script retornou **código 2** porque Ruff não está instalado nesse venv.
- Ruff externo, usando runtime já instalado: `python -m ruff check app.py src tests tools` — **All checks passed!** Nenhum pacote foi instalado.
- `git diff --check -- app.py src/getnet_web/api.py tests/test_interface.py` — sem erros.

## Relação com diagnóstico48 e limites

A causa temporal histórica do `ReadTimeout` continua indeterminada. O trace r3 reporta `duration_ms=11551` para processamento do backend, não duração HTTP. A nova medição HTTP sanitizada pode informar a duração e a classe de futuras falhas, mas não reconstrói a latência da rodada antiga.

A recuperação depende de a conversa GET expor, depois da contagem-base, uma mensagem de usuário igual ao texto pendente e uma resposta assistant subsequente. Se o backend alterar o texto armazenado por sanitização ou a conversa permanecer inacessível, a UI preserva a pendência e não associa resposta por aproximação. O revisor deve avaliar esse limite; o QA deve exercitar falha/recuperação no r5 dentro da mesma campanha aprovada.

## Próxima passagem

- Supervisor fixa r5 após esta passagem; o mesmo Reviewer revisa controles r1 e recuperação juntos; o mesmo QA revalida a jornada sem renovar campanha.
- Revisão visual em navegador real ainda pendente; testes AppTest comprovam transporte e estado, não substituem a interação QA.
- Sem commits, pushes, merges, publicações ou alterações em dados/ledgers.
