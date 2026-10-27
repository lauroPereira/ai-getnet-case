# Resultado da v0.4.0 — candidato local

## Estado atual

**Verificação sem custo do candidato r6 concluída; revisão e revalidação funcional aptas.**
Não é uma release. A autorização humana abrange implementação e validação sem
chamadas pagas; CA-32/JEV real, consulta autenticada de modelos sem gratuidade
comprovada, integração Git e publicação permanecem pendentes.

[Manifesto r6](v040-candidato-r6.json): backend na branch
`codex/v0.4.0-perfis-interface`, base/HEAD `bd549cc921ccffb37bd304a0959b8a4b690d6421`,
51 arquivos fixados, incluindo três referências de catálogo/parâmetros;
frontend independente sem Git, 84 arquivos. Fingerprint
`d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`.
História versão 1 e critérios aprovados preservados.

## Evidências por escopo

| Escopo | Evidência | Resultado e limite |
| --- | --- | --- |
| Base web independente | [Manifesto inicial](v040-base-web.json) | Template 0.2.0, 47 fontes identificadas, nove skills sincronizadas; governança adaptada sob aprovação |
| Implementação/regressão backend | [Developer r5](v040-developer-r5.md) | 216 testes estritos, Ruff/skills; separa reserva de parâmetro aplicado, sem inferência paga |
| Contrato e interface | [Developer r6](v040-developer-r6.md) | 14 testes web, Ruff/estrutura; corrige seleção sem mudar backend/contrato OpenAPI |
| Revisão técnica independente | [Reviewer r6](v040-reviewer-r6.md) | Apto para QA; dois sentidos da troca, contadores próprios e hashes conferidos |
| Build e execução instalados | [Docker r6](v040-docker-r6.json) | Reutiliza imagem r5 por igualdade completa de runtime/build; 124 arquivos instalados coincidem com r6 |
| História funcional | [QA r6](v040-qa-r6.md) e [positivos r5](v040-qa-r5.md) | R6 apto na tarefa 38 nos dois sentidos; Gravado, publicação/parâmetro, snapshot e rejeição já comprovados em r5 |
| Conferência final do Supervisor | [Auditoria r6](v040-verificacao-final-r6.json) | Mapas 51/84/127/128, 29 protegidos web e 124 instalados, sem divergências; API/interface200 |

O backend completo tem fingerprint de runtime
`b8d3a1845ac4ea16c50272bb800248bc7c4df4dbd172e40c47ae220fb063c4a5` e
build `ed67d7ff81f6ed49042e9f3aa332ac145fdd004fa38d6b99e7a05072155d816d`.
A imagem r5 instalada é
`sha256:3dc18d777ae79407363fddd4f5ca65c862b2cbb059f5af61a08e2d9e362d5c85`.
Receita/dependências/dados/prompts não mudaram desde r2; por limitação de disco,
o wheel do código corrigido foi instalado incrementalmente sobre a imagem r2
fixada, sem rede no build e sem reinstalar dependências. Os 124 arquivos
instalados foram comparados ao manifesto. Isso não declara rebuild completo
do Dockerfile canônico. R6 reutiliza essa imagem por igualdade completa dos
mapas de runtime/build; somente a interface, seus testes e README mudaram,
além da tarefa 38. O frontend r6 usa seu venv próprio.

O [ambiente r6](v040-qa-environment-r6.json) usa API `127.0.0.1:18841` e
Streamlit `127.0.0.1:18540`, ambos prontos com HTTP 200.
O transporte HTTP é real; modelos/embeddings são programados e fontes são
sintéticas/públicas. A seleção Real(API) não transforma essa montagem em
inferência real. Nenhuma credencial de provedor foi configurada no harness.

## Processo e correções

Exatamente três novos agentes autorizados e acionados em sequência,
explicitamente `gpt-6-luna/high`, com contextos novos: Developer
`/root/developer_v040`, Reviewer `/root/reviewer_v040`, QA `/root/qa_v040`.
Supervisor coordena a sessão principal. Correções voltaram ao mesmo Developer.

R1 identificou erro genérico quando a reserva de comparação era negada. R2
corrigiu o handler e preservou o ledger, mas exigiu atualizar o snapshot da
interface. R3 sincronizou o OpenAPI/gerador/cliente e recebeu parecer apto.
Manifestos, relatórios e reproduções anteriores ficam preservados.

QA r3 reproduziu uma resposta Gravada rotulada como Simulada e a ausência de
parâmetros compatíveis configuráveis por agente. Tarefas 35/36 voltaram ao mesmo
Developer; o candidato r3 permanece como referência histórica. R4 implementa
rótulo Gravado consistente e `max_output_tokens` configurável por agente,
limitado antes da reserva, com publicação/snapshot e rejeições estritas.
Reviewer r4 confirmou os demais pontos em testes focados, mas encontrou
`max_output_tokens: 80` no snapshot JEV, embora esse campo não seja enviado ao
provedor. Tarefa 37 volta ao mesmo Developer para distinguir reserva interna
de parâmetro aplicado, preservando a guarda. R5 implementa essa separação e
regressões para comparação e snapshots JEV/LLM, sem alterar a interface ou
schema. Reviewer r5 apto; mesmo QA retomado para o escopo afetado.

QA r5 confirmou esses pontos e encontrou divergência ao mudar a seleção após
comparar. R6 invalida o resultado anterior e exige novo clique explícito para
comparar, mantendo o vínculo imutável de método/ID. Sem chamada automática no
rerun. Reviewer r6 e QA r6 aptos no escopo corrigido: ambos os sentidos da
troca foram exercitados na interface/HTTP, com novo ID apenas por comparação
explícita, uso único e snapshot coerente. Não surgiu novo defeito nesse escopo.

## Critérios comprovados e pendências

| Critério | Evidência desta rodada sem custo | Limite |
| --- | --- | --- |
| CA-28 | Regressão automatizada backend216; web14; execução instalada pronta | Não é nova avaliação de qualidade com modelo real |
| CA-33 | Adaptador/erros JEV e ausência de fallback cobertos por testes/revisão | Indisponibilidade real de provedor não foi exercitada |
| CA-34–35 | Comparação só dos Routers, atendimento uma vez, rerun sem nova comparação; modos Simulado/Gravado coerentes | Transporte HTTP real com inferência programada |
| CA-36 / RF-49/51 | Perfil publicado com Support256, versão/digest/snapshot; Router LLM300 e JEV sem parâmetro não enviado | Evaluation reservado à v0.6; provedores reais não invocados |
| CA-37 | Catálogo compatível local, UI limitada e API422 preservando versão/digest | IDs disponíveis na conta do provedor não foram verificados via API autenticada |
| CA-32 | Pendente | JEV real exige autorização de validação própria |

A auditoria pós-QA confirmou também branch/HEAD e os fingerprints completos.
As três funções foram realizadas pelos mesmos três agentes distintos
`gpt-6-luna/high`, em sequência; os relatórios mantêm a independência em
relação ao implementador. A validade r5 do backend é preservada pela igualdade
integral de runtime/build em r6. Nenhuma nova suíte completa foi repetida
depois disso sem mudança que a justificasse.

## Orçamento e limites

**Nenhuma chamada paga de aplicação nesta versão.** Total registrado do projeto
permanece US$0,59283583 de US$5; saldo da validação v0.3.0 não autoriza gasto
na v0.4.0. Valores de liquidação usados pelos testes de orçamento são simulados,
não despesa do provedor. Testes programados não concluem CA-32 nem qualidade
das respostas dos modelos reais. [Fontes do catálogo](v040-catalogo-fontes.md).

Uma tentativa adicional de [metadados públicos sem credenciais](v040-metadados-publicos.json)
recebeu 401/401/403; nenhum ID foi obtido. Não foi feita consulta autenticada
nem inferência; o resultado não fecha a lacuna de verificação via API.

Nenhum commit/push, remoto web, tag ou publicação da v0.4.0 foi autorizado ou
executado. A v0.3.0 permanece integrada e tagueada. Retorno previsto pela tag
v0.3.0 e pela migração 0006→0005, validada somente em bancos sintéticos isolados.

## Próximo passo

O trabalho de implementação/verificação autorizado sem chamadas pagas está
fechado nas evidências acima. Permanecem validação real/identificação de
modelos na conta e aceite da entrega, seguidos de eventual integração Git
autorizada. Não avançar à v0.5.0 ou
declarar v0.4.0 completa enquanto requisitos reais e aceite aplicável estiverem
pendentes. Arquivos de tarefas/README refletem a passagem congelada; este
registro central acompanha o estado posterior sem alterar o candidato validado.
