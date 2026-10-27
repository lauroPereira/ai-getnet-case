# Resultado da v0.5.0

**Estado: apto nos critérios obrigatórios publicados da v0.5.0, candidato local r7.**

## Candidato

[R7](v050-candidato-r7.json), dois projetos em
`codex/v0.5.0-base-versionada`, alterações locais sobre as mains v0.4 integradas.
Fonte `ad9cf469cd85e44210280df1949ecac766857688a6f1101bb61f8d0e9e9b8d8c`,
46arquivos backend/85web. Runtime/build backend idênticos aos do r3,
confirmados na [evidência Docker r7](v050-docker-r7.json).

## Validação e correções

- Backend: [revisão r2](v050-reviewer-r2.md) apta com293 testes; código de
  runtime preservado durante as correções web.
- [QA r1](v050-qa-r1.md) reprovou confirmações UI e apresentação da resposta
  após falha de transporte. Build/teste/ativação backend, inferências OpenAI
  e comparação DeepSeek/JEV tiveram evidências conforme o relatório.
- Correções49/50/51 implementadas por Developer gpt-6-luna/high autorizado.
  Suíte web20/Ruff externo passaram; script estrito retornou2 por Ruff ausente
  no venv web, com pytest/estrutura/skills aprovados.
- [Reviewer UI r1](v050-reviewer-ui-r1.md) encontrou confirmação de teto
  desatualizada; [Reviewer UI r2](v050-reviewer-ui-r2.md) confirmou sua correção
  no r6. Revisão independente reutilizou o mesmo agente gpt-6-luna/high.
- Mesmo QA gpt-6-luna/high reativado para jornada no navegador, recuperação
  manual GET, concorrência/retorno/rerun e regressão pertinente restante.
  Não foram repetidos bootstrap ou smokes pagos já válidos.
- [QA r2](v050-qa-r2.md) comprovou confirmações, build/teste/ativação/retorno
  pela UI e captura consistente durante troca de versão. GET200 encontrou
  resposta persistida, mas a UI permaneceu pendente; [defeito52](../tasks/52-recuperar-conversa-get-ui-v050.md)
  e [correção53](../tasks/53-consumir-contrato-real-conversa-v050.md) usam o
  payload sintético real como referência. Efeito da nota fictícia na resposta
  ficou inconclusivo; recusa de afirmar prazo oficial não foi tratada como defeito.
- [Reviewer UI r3](v050-reviewer-ui-r3.md) conferiu o formato real do GET,
  fixture e reprodução independente, aprovando r7 para retornar ao mesmo QA.
  [QA r3](v050-qa-r3.md) comprovou no navegador a recuperação da resposta
  persistida, limpando pendência com GET e sem POST repetido. Navegação não
  gerou nova inferência.

O QA auditou o veredito contra CA-41, RF63–66, spec derivada e história v1,
sem mudar essas fontes: os critérios obrigatórios têm evidência nas rodadas
r1/r2/r3. A consulta opcional sobre o texto fictício não chegou a Knowledge;
permanece inconclusiva e não prova consumo desse trecho. Reproduzir marcador
não é critério publicado, portanto não é usado para bloquear nem para alegar
um comportamento não demonstrado. A tentativa adicional de navegador ficou
indisponível; a limitação consta do relatório.

## Custos e limites

Baseline da campanha ao fim de QA r1:17linhas, US$0,00282289, zero reservas
abertas. Primário867linhas/US$0,34581250; delta da campanha representa as
mesmas chamadas e não é somado duas vezes. Acumulado histórico reconciliado
nesse ponto:US$0,59565872.

QA r2 manteve o MESMO arquivo/ID e cap adicionalUS$0,25. Ao encerramento:
campanha33linhas/US$0,00532161, delta r2US$0,00249872; primário883linhas/
US$0,34831122, mesmo delta; zero reservas abertas. Acumulado reconciliado
US$0,59815744. PrimárioUS$1 e teto globalUS$5 preservados.

Encerramento r3: campanha35entradas, **US$0,00553883**; delta r3US$0,00021722.
Primário885entradas/US$0,34852844, mesmo delta acumulado da campanha desde o
baseline. Acumulado reconciliado do projeto: **US$0,59837466 de US$5**.
Zero reservas abertas e saldo de campanhaUS$0,24446117; nenhum cap renovado.

[Auditoria final do Supervisor](v050-auditoria-final-supervisor.json) conferiu
46/85arquivos de fonte,128runtime/129build sem divergências, os dois ledgers
em somente leitura e ausência de listeners nas quatro portas próprias de QA.
Serviços encerrados; dados, logs, fixture e controles persistentes preservados.

## Pendências

Candidato local pronto para decisão de integração. O plano aprovado exclui
integração Git v0.5; ela continua dependendo de autorização específica.
Tarefa46 registra P3 conhecidos para tratamento posterior. Nenhum commit,
push, PR, merge, tag ou publicação v0.5 foi executado neste conjunto.
