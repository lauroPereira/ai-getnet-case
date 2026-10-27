# Tarefa: apresentar resposta persistida após recuperação GET manual da conversa v0.5.0

## Objetivo

Fazer a UI reconhecer e exibir a resposta do assistente quando a consulta manual retorna a resposta já persistida após falha de transporte, mantendo a pergunta pendente até haver correspondência correta e sem repetir a POST.

## Especificação relacionada

[História v1](../historias/base-versionada-v050.md), requisito de recuperar resposta; [tarefa50](50-recuperacao-manual-chat-v050.md), em especial critério de conclusão sobre GET manual.

## Pré-condições

- Candidato de QA: r6, source fingerprint `45073733de04247748d583f5a57af01bfa3180979d8915616bd7db0af971aaa3`.
- API isolada `127.0.0.1:18853`, UI `127.0.0.1:18553`, dados de cliente e mensagem sintéticos.
- Payload GET preservado em `.pytest_cache/v050-qa-real-runtime/recovery-get-r2-sanitized.json`; não usa token nem dado privado.

## Arquivos prováveis

Web `app.py` e `tests/test_interface.py`; somente outros arquivos após avaliação de escopo. Backend permaneceu imutável nesta reprodução.

## Passos de reprodução

1. Na UI real, iniciar uma conversa sintética e enviar `Meu comprovante mostra o código 91. Quanto tempo devo aguardar antes de tentar novamente?` através de proxy que descarta somente a resposta da POST após o upstream concluir.
2. Confirmar que UI mantém a pergunta e oferece atualização manual sem repetir envio.
3. Acionar `Atualizar conversa` para o ID preservado.
4. Conferir GET 200 e a estrutura de resposta sanitizada: `messages` tem duas mensagens ordenadas, primeira `role=merchant` com a pergunta; segunda `role=assistant` com a resposta persistida; cada item inclui `text`, `route`, `status` e `created_at`.
5. Comparar o estado visual após o GET.

## Esperado

A pergunta ainda pendente corresponde à mensagem `merchant` recuperada; resposta `assistant` subsequente aparece na conversa, limpa pendência e habilita novo envio. Não repetir a POST, não inferir que GET vazio ocorreu quando backend retornou resposta, não exibir resposta antiga sem par da pergunta.

## Observado no r6

Proxy registrou uma única POST `/v1/messages` upstream200, com resposta descartada; API finalizou `answered`, request `req_199899ac93a24a7facd5`, conversation `conv_dcd0ec53dc9244ab8dd2`, custo trace `$0.00095223`, snapshot R2. GET manual `/v1/conversations/conv_dcd0ec53dc9244ab8dd2` retornou200 e payload com as duas mensagens acima. A UI continuou exibindo pergunta pendente e `Ainda não há resposta nova para esta pergunta. Atualize novamente mais tarde.` Nenhuma nova POST foi feita. A captura visual foi inspecionada por CUA e o payload JSON sintético está preservado no harness de QA.

## Critérios de conclusão

- [x] GET com roles `merchant` e `assistant` recupera a resposta que segue a pergunta pendente.
- [x] GET ainda sem resposta mantém a pendência e mensagem útil.
- [x] GET/rerun não repetem a POST; navegação/rerun continuam sem ação de envio automática.
- [x] Teste focal consome fixture sintética com o formato observado, sem alterar o contrato público.

## Validação

Reprodução de QA r2 no candidato r6: POST original caiu apenas no transporte após conclusão do upstream; GET manual 200; estado UI não recuperou. Ver payload `.pytest_cache/v050-qa-real-runtime/recovery-get-r2-sanitized.json`, eventos `.pytest_cache/v050-qa-real-runtime/proxy-r2-events.jsonl` e relatório [v050-qa-r2.md](../evidence/v050-qa-r2.md). Correção e regressões sintéticas estão registradas em [passagem Developer UI r4](../evidence/v050-developer-ui-r4.md); QA real ainda deve revalidar no candidato r7.

## Status

```text
implementada; aguardando revisão independente e revalidação QA no candidato r7
```
