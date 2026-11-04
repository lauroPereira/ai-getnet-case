# Revisão independente do teto de QA da v0.8.0

**Candidato** `27add608d611fd2b8459cac83547d67714bf44a7`, base `d66dff3`.

**Parecer** correção necessária. O Reviewer usou `gpt-6-luna/xhigh` em contexto independente, com pacote que continha apenas as fontes da regra, o procedimento operacional e os arquivos do diff. A retomada após o limite de uso manteve o mesmo pacote. O Reviewer conferiu hashes e fez inspeção estática. O Supervisor executou a suíte estrita no SHA fixado, com 1.031 testes aprovados, Ruff limpo e skills válidas.

## Achado P2

Com o ledger de campanha ausente e um arquivo `.limit` de campanha contendo US$1,15, saldo primário suficiente e estimativa revalidada acima de US$1,00 e até US$1,10, a CLI pode criar o SQLite e fixar o cap em US$1,10. A reabertura então recusa o par, pois exige US$1,10 no registro e no arquivo. A guarda precisa recusar arquivo de teto órfão antes da montagem. O teste de ledger legado existente usava saldo primário insuficiente e parava antes de alcançar essa condição.

O Reviewer confirmou por inspeção os demais critérios. A CLI exige estimativa recalculada, preserva as faixas anteriores, confere saldo antes da primeira montagem excepcional, reabre o par persistido exato após consumo e continua reservando cada chamada nos dois ledgers. O teto absoluto é US$5,00.

## Procedimento operacional

A extensão local r3, SHA-256 `62ad04a7694b840519b33b71ba6698a8ae5bf59a6d2158af8784fb15cbe5e6c1`, foi considerada apta sob a condição de quiescência operacional. O Supervisor verificará processos e contêineres antes e depois, e o procedimento confere ausência de cap nos dois lados da troca. O SQLite primário não serializa a montagem do SQLite separado de campanha. Uma falha após o registro `prepared` suspende o QA e encerra a tentativa. A recuperação exige quiescência e preserva a auditoria. Outra aplicação, se necessária, exige diretório novo e nova revisão.

O ensaio sintético conduzido pelo Supervisor confirmou a preservação do histórico, a recusa de campanha preexistente, a recuperação após publicação e a nova tentativa após falha anterior ao registro `prepared`. A revisão não abriu o holdout, nem executou o procedimento no ledger real.
