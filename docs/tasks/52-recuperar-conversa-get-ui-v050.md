# Tarefa: apresentar resposta persistida após recuperação GET manual da conversa v0.5.0

## Objetivo

Fazer a UI reconhecer e exibir a resposta do assistente quando a consulta manual retorna a resposta já persistida após falha de transporte, mantendo a pergunta pendente até haver correspondência correta e sem repetir a POST.

## Especificação relacionada

[História v1](../historias/base-versionada-v050.md), requisito de recuperar resposta; [tarefa 50](50-recuperacao-manual-chat-v050.md), em especial critério de conclusão sobre GET manual.

## Pré-condições

- API e interface locais isoladas, com dados de cliente e mensagem sintéticos.
- Payload GET sanitizado como referência; não usa token nem dado privado.

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

## Critérios de conclusão

- [x] GET com roles `merchant` e `assistant` recupera a resposta que segue a pergunta pendente.
- [x] GET ainda sem resposta mantém a pendência e mensagem útil.
- [x] GET/rerun não repetem a POST; navegação/rerun continuam sem ação de envio automática.
- [x] Teste focal consome fixture sintética com o formato observado, sem alterar o contrato público.

## Resultado

Corrigida na [tarefa 53](53-consumir-contrato-real-conversa-v050.md): o GET no formato real recupera a resposta e limpa a pendência sem repetir o POST, comprovado no navegador. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
