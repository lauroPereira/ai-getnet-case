# Passagem Developer — correção das confirmações v0.5 (UI r1)

**Estado:** implementação local concluída; revisão independente e revalidação QA pendentes. Não é aceite de QA nem decisão de release.

## Escopo e estado

- Tarefa: `docs/tasks/49-correcao-confirmacoes-qa-v050.md`, relacionada ao defeito47.
- Web: `C:\workspace\ai-getnet-case-web`, branch `codex/v0.5.0-base-versionada`, HEAD base `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Backend: sem mudanças de código. Supervisor confirmou runtime idêntico a r3; hash de `budget.py`: `fd0e927d603dd497395ee038a0ddc65b8489397f334f73bead5a4db98acfe8c8`.
- Arquivos de produto alterados: `app.py` e `tests/test_interface.py`. Bytes anteriores foram preservados em `.pytest_cache/v050-r4-confirmation-originals/`.
- Candidato r3, manifesto, história e artefatos QA foram preservados. Este papel não fixou candidato r4.

## Correção

Os checkboxes de build, teste, ativação e retorno saíram dos `st.form`; cada ação agora usa um botão explícito fora de formulário. Marcar uma confirmação causa o rerun normal do Streamlit e atualiza a habilitação do botão. Renderização, reruns e navegação não enviam essas ações.

A confirmação reinicia quando muda seu contexto: estimativa/digest/revisões para build; candidata e versão ativa para teste/ativação; versão anterior e ativa para retorno. Os tetos de build e teste têm chaves persistentes, mantendo os valores digitados durante o rerun. Os payloads preservam confirmação explícita, tetos, candidata e versão ativa esperada; a validação do backend continua autoritativa.

## Validação observada

Com cliente falso, sem acessar serviços da rodada, backend real ou provedores:

- Regressão focada: `python -m pytest tests/test_interface.py -k kb_confirmation_controls_enable_once_without_form_submission --basetemp=.pytest_cache/v050-r4-target4 -q` — **1 passou, 15 filtrados**.
- A regressão marca cada confirmação e executa o rerun normal do Streamlit, confirma habilitação do botão e preservação dos tetos de build (`0.125`) e teste (`0.11`). Reruns adicionais não alteram contadores; somente o clique envia uma chamada falsa por ação (build, teste, ativação e retorno).
- `tools/scripts/lint_and_tests.py --strict`, `.venv-v040`: pytest **16/16 passou**; estrutura e skills passaram; o script retornou **código 2** pois Ruff não está instalado nesse ambiente.
- Ruff externo com runtime já existente do backend: `python -m ruff check app.py src tests tools` — **All checks passed!** Nenhum pacote foi instalado.
- Nenhum teste ou comando chamou API real, OpenAI ou outro provedor. Nenhuma chave foi lida ou exibida.

## Diagnóstico somente leitura da tarefa48

O log web registra `ReadTimeout` em `2026-10-27 16:28:35.387 America/Sao_Paulo`, equivalente a `19:28:35.387 UTC`. O trace para `req_ec2e2747dfbb4dda8b86` registra `at=2026-10-27T19:28:36+00:00`, `status=answered` e `duration_ms=11551`. Os steps começam às `19:28:25.726 UTC`; o último começa às `19:28:36.297 UTC` e dura 4 ms. O cliente web configura timeout de 20 segundos. A duração do trace mede o processamento registrado no backend, não a latência HTTP ponta a ponta; os registros disponíveis não indicam quando a requisição saiu do navegador. A causa temporal permanece indeterminada. Timeout não foi alterado e nenhum retry ocorreu.

A UI atual **não oferece** consulta de recuperação por `conversation_id`. O cliente tem `GET conversation(conversation_id)` e a API retorna mensagens da conversa, mas `app.py` não chama esse método. “Atualizar execução” só existe quando `latest_run` já contém um `request_id` recebido com sucesso e consulta `GET run(request_id)`. Se o POST termina em timeout antes da resposta chegar à UI, o request ID não é salvo; a rota de conversa também não retorna request ID por mensagem.

Proposta mínima futura, fora desta tarefa: após erro de transporte, oferecer uma ação manual somente GET para consultar a conversa já conhecida e exibir a última resposta persistida. Detalhes do run só podem ser atualizados quando seu request ID estiver disponível. Nunca repetir automaticamente o POST. A causa temporal ainda requer medição HTTP ponta a ponta; o trace existente não basta.

Um log separado às `16:29:15.599` registra `UnsupportedProtocol` por URL sem esquema durante abertura de sessão. Ele não corresponde ao request rastreado e não identifica a causa do timeout anterior.

## Próxima passagem

- Revisão independente do delta, seguida de candidato r4 fixado pelo Supervisor e revalidação dos quatro controles no navegador pelo mesmo QA.
- A confirmação visual em navegador real ainda não foi executada pelo Developer; não declarar CA-41 ou release apta.
- Sem commits, pushes, merges ou publicação. Branches e HEADs não foram trocados.
