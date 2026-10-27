# Tarefa: alinhar seleção posterior da decisão na comparação LLM/JEV

## Objetivo

Garantir que a decisão escolhida na comparação seja a mesma que o atendimento reutiliza e que o resumo da tela reflita a escolha vigente.

## Especificação relacionada

docs/specs/perfis-interface-v040-plano.md; docs/specs/incrementos-pos-nucleo.md; docs/historias/perfis-interface-v040.md; RF-47, RF-49, RF-51 e CA-34–36.

## Pré-condições

Reproduzir a divergência documentada em docs/evidence/v040-qa-r5.md com um perfil sintético publicado cujo Router LLM possua max_output_tokens configurado. Não chamar provedores reais.

O contrato aprovado vincula o método ao `comparison_id` no ato da comparação.
Esta correção não torna esse vínculo mutável. A interface pode invalidar a
comparação quando a escolha muda e exigir nova ação explícita de comparar,
ou impedir mudança enquanto o resultado está ativo e oferecer ação clara
para nova comparação. Nunca executar nova comparação automaticamente no rerun.

## Arquivos prováveis

Interface web da comparação, estado da seleção e testes funcionais de comparação/reuso.

## Passos

1. Escolher LLM no atendimento, comparar a mesma mensagem nos Routers e observar o resumo da seleção.
2. Após a comparação, marcar JEV no grupo “Decisão a usar depois da comparação”.
3. Confirmar a divergência e corrigir a coordenação do estado/resumo,
   preservando o vínculo imutável já aprovado do método ao ID.
4. Se for necessária nova comparação, exigir clique explícito e novo ID;
   até lá, a decisão antiga não pode ser usada com sinais de escolha oposta.
5. Usar a decisão válida uma vez e inspecionar método, parâmetros efetivos e
   ID; cobrir LLM/JEV antes e após resultados, sem chamadas externas.

## Critérios de conclusão

- [x] Opção, resumo e ação disponível são coerentes; mudança exige nova
      comparação explícita ou é bloqueada enquanto o resultado está ativo.
- [x] Não há chamada automática no rerun ou alteração silenciosa de método.
- [x] O atendimento reutiliza a decisão JEV de uma comparação válida, sem
      chamar novamente o Router no atendimento.
- [x] O snapshot registra router_mechanism=jev e não declara max_output_tokens efetivo para o Router.
- [x] A escolha LLM continua reutilizando a decisão única e registrando o parâmetro efetivamente enviado pelo Router.
- [x] Testes funcionais cobrem a seleção antes e após comparar, sem inferência paga.

## Validação

`ai-getnet-case-web/tests/test_interface.py::test_changing_comparison_selection_invalidates_result_until_explicit_recompare` cobre as sequências LLM→JEV e JEV→LLM. Após mudança da seleção, o ID anterior é descartado, o resumo informa que é preciso comparar novamente e o botão de uso desaparece. Os reruns seguintes não chamam `compare`; o ID novo nasce somente após clique explícito em comparar. O uso envia uma única mensagem com o método e o ID novos, sem comparação adicional. A integração backend r5 documentada em `v040-developer-r5.md` verifica a reutilização JEV/LLM e os mapas efetivos no snapshot. Suíte web r6: 14 testes passaram; Ruff check e format passaram. `tools/scripts/lint_and_tests.py` padrão validou estrutura e saiu 0; informou que lint não é executado no modo padrão. Nenhuma chamada paga.

## Status

Concluída: [Reviewer r6](../evidence/v040-reviewer-r6.md) e
[QA r6](../evidence/v040-qa-r6.md) aptos nos dois sentidos, com hashes
conferidos. O método permanece vinculado ao ID; troca exige nova comparação
explícita e atendimento consome a decisão válida uma vez.
