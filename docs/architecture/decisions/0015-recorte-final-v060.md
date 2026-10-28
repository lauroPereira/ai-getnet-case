# 0015. Recorte final: v0.6.0 única, sem Evaluation Agent nem propostas

## Status

Aceita pelo responsável em 2026-10-27 com o recorte da v0.6.0. Complementa as decisões 0008 e 0012; não as substitui.

## Contexto

O plano 0.2 previa uma v0.6.0 com Evaluation Agent por etapa e ciclo de melhoria supervisionada e uma v0.7.0 com experimentos, quatro gráficos e compartilhamento. Depois da v0.5.0, o objetivo passou a ser fechar um case compreensível, confiável e demonstrável. O backend já tem traces por etapa, snapshot por execução, agregação de custo por agente, verificações determinísticas e um avaliador por modelo usados pelo CLI.

## Decisão

- Uma única v0.6.0 substitui as antigas 0.6.0 e 0.7.0; após seu aceite, a expansão funcional termina e pendências não originam uma v0.7.0.
- Sem Evaluation Agent e sem workflow de propostas, candidatas e aprovações de melhorias (escolha expressa do responsável). Ativação, autoria e retorno da base de conhecimento (decisão 0014) continuam.
- Avaliação sob demanda reutiliza as verificações determinísticas e o avaliador por modelo existentes sobre a resposta persistida, com configuração fixa do avaliador registrada em cada avaliação. Rubricas continuam versionadas como arquivos em `prompts/`; a tabela de versões de rubricas prevista na decisão 0008 não é criada. O campo `evaluation` dos perfis permanece no esquema, sem uso no atendimento.
- Comparação pequena (2–3 perfis, até 3 cenários, até 2 repetições), executada no processo da API fora da requisição, com efeitos de domínio isolados numa cópia do banco sintético e traces marcados.
- Persistência mínima: migração 0008 reversível com `run_evaluations` e `comparisons`, mais o contador por sessão demo. Nenhuma outra entidade de experimento.
- Catálogo curto de cenários rotulados em `data/scenarios/`, servido por `GET /v1/scenarios`.
- Exposição conforme 0012, com dois ajustes: a API do compose fica em `127.0.0.1:8000` e a sessão demo tem limite configurável de mensagens; o sublimite efetivo da demonstração é o saldo do teto persistente do ledger.

## Alternativas

- **Executar o plano 0.2 inteiro:** mais entidades, agentes e telas sem melhorar a clareza da entrega.
- **Avaliação e comparação só em relatórios JSON:** menos dados, mas sem rastreabilidade pela interface.
- **Fila ou serviço para a comparação:** operação nova desnecessária para poucas células.

## Consequências e retorno

Menos superfície para manter e demonstrar; requisitos retirados ficam como adiados, com IDs preservados. Retorno pela tag `v0.5.0` e pela migração 0008 → 0007 em banco sintético. Comparações longas dependem do processo da API ativo; uma comparação interrompida fica parcial ou com falha registrada.

## Data

2026-10-27
