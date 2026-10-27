# Revisão independente — v0.3.0 jornadas, rodada 1

## Parecer

**Correções necessárias.** O candidato não deve avançar para QA antes da correção do achado P2 e da fixação de novos hashes. O escopo revisado foi RF-32–34/CA-21–23, RF-46/CA-28/CA-31, tarefas 21–24, plano e história v0.3.0, e decisões 0006 e 0011.

## Independência e candidato

- Revisão em contexto separado, sem histórico ou conclusões do implementador: **independente**.
- Branch: `codex/v0.3.0-jornadas`.
- Base e HEAD: `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; as mudanças do candidato estão no working tree local.
- Manifesto: `docs/evidence/v030-candidato-r1.json`; 42 de 42 arquivos listados existem e seus SHA-256 individuais conferem com o conteúdo atual.
- O manifesto registra fingerprint agregado `ad1bfc9dc7c945453c0d3093cc1e8524a95f84185c8fecd50f79b4ff319c4284`; o formato de agregação não está descrito e, por isso, não foi recalculado.
- Imagens verificadas durante o smoke: API `sha256:4f05365ed614a52f04d3b77f6c4bad3bbf70110d28edca43f287aff0c14445db`; mocks `sha256:eba11f0d2f7206697342e89c58d17a915b3c727ed1acc0b8cd62e05096b901c3`.

## Achados

### P2 — consulta de cancelamento pode retornar venda de outro lojista se os registros estiverem inconsistentes

- **Condição:** existir em `sale_cancellations` uma linha cujo `customer_id` é o lojista da requisição, mas cujo `transaction_id` referencia uma venda pertencente a outro lojista. O esquema exige que `transaction_id` exista em `sales`, mas não exige que ambos compartilhem o mesmo `customer_id`.
- **Impacto:** `get_sale_cancellation_context` devolve a linha do cancelamento e o identificador da venda alheia, contrariando a garantia de vínculo por lojista do RF-15 e o isolamento exigido pela jornada. Uma linha incorreta pode surgir de fixture ou carga inconsistente; a API não fornece argumento livre para criar esse estado.
- **Local:** `src/merchant_assistant/tools/domain.py:479`, consulta sem condição `s.customer_id = c.customer_id`; `src/merchant_assistant/data/migrations.py:205`, FK valida apenas a existência da venda.
- **Reprodução própria:** em banco SQLite sintético em memória, sem alterar arquivos, inseri `sale_002_0002` (venda do cliente `cliente_demo_002`) em `sale_cancellations` com `customer_id='cliente1988'`. Consultando como `cliente1988`, a ferramenta retornou `('sale_002_0002', 'cliente1988', 'requested')` junto ao cancelamento legítimo desse lojista.
- **Critério:** RF-15; isolamento de recursos relacionado a RF-46/CA-31 e tarefa 23.
- **Correção sugerida:** restringir a junção à mesma propriedade (`s.customer_id = c.customer_id`) e adicionar teste com linha de cancelamento de vínculo cruzado, esperando que não retorne qualquer dado da venda alheia.

## Evidência executada

- `.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_cache/v030-review-r1`: **164 passed** em 124,88 s.
- `.\.venv\Scripts\python.exe -m ruff check src tests`: **All checks passed**.
- `COMPOSE_DISABLE_ENV_FILE=1 docker compose config --quiet`: passou, sem erro.
- Smoke local em contêiner: imagem de API fixada executou `MockServiceClient` contra `mocks` pela rede interna; pricing e cobrança retornaram 194 centavos para `sale_1988_0001`. A consulta da venda para outro lojista foi bloqueada pela API interna com HTTP 403 (`FORBIDDEN_RESOURCE`). A imagem do serviço `mocks` em execução corresponde ao digest registrado.
- Inspecionei o diff de `main` e os arquivos novos do manifesto, incluindo schemas, clientes, serviço, fixtures, migração, ferramentas, prompts, Compose e testes. A comparação em centavos, as quatro saídas de preço, o caminho de contrato sem ferramenta de venda, a migração reversível e as rotas HTTP foram rederivados por código e execução.

## Lacunas e passagem

- O smoke executado cobriu o cliente da imagem de API até o `mocks` em HTTP real entre contêineres e a checagem de isolamento da fonte. Não iniciei um novo stack completo da API com banco/índice próprios nesta revisão; o fluxo `POST /messages` foi coberto pelos testes locais.
- Não houve chamada paga, acesso a `.env` ou runtime anterior, acesso à rede externa, alteração do produto, commit ou publicação.
- Próximo responsável: **Developer**, para corrigir a junção e o teste de isolamento, produzir novo candidato com manifesto atualizado e devolver à revisão. Após parecer apto, encaminhar a QA pela história v0.3.0.
