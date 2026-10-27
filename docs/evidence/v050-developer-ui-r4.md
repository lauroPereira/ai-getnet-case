# Passagem Developer UI r4 — consumo do formato real de conversa

- Papel e responsável: Developer, sessão autorizada gpt-6-luna/high.
- Objetivo e critérios: corrigir tarefa53/defeito52 para a UI recuperar a resposta persistida no GET manual, sem reenviar a pergunta.
- Escopo: somente repositório web (`app.py`, `tests/test_interface.py`, fixture JSON sintética), além desta evidência e atualização das tarefas52/53 no repositório backend.
- Estado: implementação concluída; aguardando revisão independente. Não é parecer de aceite.
- Branch e PR: branch existente `codex/v0.5.0-base-versionada`; nenhum PR ou commit criado.
- Base e versão final: candidato anterior r6, source fingerprint `45073733de04247748d583f5a57af01bfa3180979d8915616bd7db0af971aaa3`. Os bytes r6 de `app.py` e `tests/test_interface.py` foram preservados em `.pytest_cache/v050-r7-r6-originals/` antes da edição: hashes SHA-256 `33bdb06688e59ca6a3cc7b8d4a96aa9c58f51647d04d946aa8e25a8bc16dc68a` e `73031d48ac3a2d44cf7609b2e5592fc35b537609175bc8f2107281f9cfb68862`. A versão com alterações locais será fixada pelo Supervisor no r7; hashes atuais dos arquivos web constam abaixo.
- Independência: não se aplica ao papel Developer; revisão deve ser independente.

## Implementação

A resposta GET real sanitizada foi conferida sem exibir/copiar textos. O hash do envelope preservado em `.pytest_cache/v050-qa-real-runtime/recovery-get-r2-sanitized.json` coincide com o SHA-256 aprovado `c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`. O corpo contém mensagens ordenadas `merchant` e `assistant`; cada mensagem tem `role`, `text`, `route`, `status` e `created_at`.

`find_pending_reply` agora compara a pergunta pendente com o primeiro `merchant` depois do cursor e procura a resposta `assistant` subsequente. Uma nova mensagem `merchant` antes da resposta interrompe a associação. A UI preserva o GET manual, o estado pendente em erro/resposta ausente e a ausência de `request_id`; nenhuma API ou dado do backend foi alterado.

A fixture versionada `fixtures/conversation-recovery-r2.json` contém somente valores sintéticos, mas conserva as chaves do corpo observado, incluindo as chaves e roles originais das mensagens. MockTransport fixa os nomes/roles do contrato; AppTest cobre resposta renderizada, cursor após histórico, histórico anterior sem resposta nova, erro/404, GET vazio, recuperação posterior e reruns. A sequência mantém exatamente uma POST simulada e nenhuma inferência, chamada de provedor ou acesso a serviços reais.

O diagnóstico de QA sobre o texto fictício de sete minutos não foi alterado: a evidência r2 não demonstrou quais chunks foram consumidos e não autoriza atribuir defeito ou mudar RAG/prompt.

## Evidência de validação

- Testes focais de `tests/test_interface.py`: **20 passed**.
- Suíte web por `tools/scripts/lint_and_tests.py --strict`: **20 passed**; validação de estrutura e skills passou. O script terminou com **código 2**, pois Ruff não está instalado no venv web.
- Ruff externo, sem instalação, via Python do venv backend: `ruff check app.py src tests tools` — **All checks passed!**
- `git diff --check` no repositório web: passou.
- Somente o arquivo de payload GET sanitizado autorizado foi lido. Nenhum endpoint live, serviço pago, ledger, guarda ou estado de runtime foi acessado/modificado; nenhuma fonte backend foi alterada. Nenhuma chamada paga foi feita.

Hashes SHA-256 dos arquivos web após a implementação:

| Arquivo | SHA-256 |
|---|---|
| `app.py` | `e7f88a5e928e4a739d8ce5c7abc910f9e784c3a23e878aa74b3acf80b431a936` |
| `tests/test_interface.py` | `9a109f0f47fbfeec2ca69bcfd99b5b23336baeaecb2630c918384a4debe29e1b5` |
| `fixtures/conversation-recovery-r2.json` | `6e6bcab48fd875152904c5ace359b85f535f062ad950bce359feb49688597ba8` |

## Critérios e limites

- GET com o formato observado recupera e renderiza a resposta pareada à pergunta após o cursor.
- Mensagens anteriores, resposta ausente, 404 e falhas de transporte mantêm a pergunta pendente; GETs/reruns não reenviam a pergunta.
- A validação é sintética. A jornada real de recuperação não foi repetida; QA posterior deve confirmar a correção no r7 sem repetir cenários pagos já aprovados.
- Candidato r7 ainda não fixado. A implementação não declara aptidão do Reviewer/QA nem aceite do produto.

## Próxima ação

Supervisor fixa o manifesto r7 com os arquivos web atualizados. Reviewer re-deriva a correção da recuperação e os controles já aprovados; QA revalida somente os critérios afetados, preservando cap e evitando repetir interações pagas válidas.
