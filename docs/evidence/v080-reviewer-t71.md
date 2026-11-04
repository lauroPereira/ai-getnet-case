# Revisão independente da T71 (e P3 da T70, rodada 2) — rodada 1

- **Candidato:** `31aac33b3335ac193cf5cb35c9dbcc5e9ed58f61`, branch `codex/v0.8.0-avaliacao`, worktree destacado `review-a`; HEAD e status iguais antes e depois. Diff `69f2fca..31aac33` (P3 da 70 em `3598a48`; tarefa 71 em `31aac33`).
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu a tarefa até "Validação"; não leu a passagem do Developer; não abriu o holdout (lacre conferido). Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **apto para QA** — nenhum P1 nem P2; 9 P3.

## Comprovado por execução

- **Amostra:** campanha programada com juiz (40 respostas, 12 estratos rota × split); `--sample 24` cobre todos os estratos antes de repetir; reprodutível pela semente (mesmo SHA-256 com as linhas embaralhadas; outra semente, outro arquivo); UTF-8 com BOM, `;`, CRLF; instruções com a rubrica e linha de procedência; colunas do avaliador vazias.
- **Nenhum dado do juiz na planilha:** busca de todas as strings do juiz em várias codificações sem acerto; teste diferencial — trocando todos os campos do juiz no relatório de origem por sentinelas, o CSV sai byte a byte igual. Máscara de CPF, CNPJ, e-mail, cartão e chave; células iniciadas por `+`/`@` protegidas contra fórmula.
- **Importação:** `;`, `,` e tabulação; arquivo regravado (linhas vazias, CRLF/LF, com e sem BOM) aceito; não UTF-8 recusado sem gravar; validação linha a linha (faixa, meio preenchida, booleano, duplicatas, `request_id` vazio ou inexistente, colunas a mais ou faltando), nada gravado em erro; ligação ao julgamento correto por `request_id`; reimportação atualiza no lugar; atomicidade com falha injetada.
- **Estatística:** kappa ponderado quadrático reimplementado em frações, igual em 11 séries fixas e 2 000 aleatórias; categorias na escala 1–5 inteira (correto); veredito binário igual ao Cohen; Wilson igual à fórmula independente; bootstrap reprodutível pela semente e próximo de um bootstrap independente de 20 000 reamostras; ressalva D19 em destaque com intervalos.
- **P3 da T70:** ajuda do juiz com `JUDGE_*` e `DEEPSEEK_API_KEY`; nome do relatório de `--judge-repeat` pelo split de origem (quatro arquivos coexistem); juiz programado marca dado da conta sem ferramenta sob a nota de web e não marca valor público; contagem das respostas sob a nota confere; passo `web` reconhecido.
- **D18 e lacre:** diff só em arquivos do Time B (`cli.py` com remoções apenas nos pontos dos P3 da 70); lacre do holdout `91aa5158…` intacto.
- **Mutação:** 52 mutantes, 43 mortos, 3 equivalentes, 6 sobreviventes (lacunas de teste). Suíte estrita (Supervisor, neste candidato): **790 passed**, código 0.

## P3

1. A amostra não filtra split nem recusa `holdout_v080`: a decisão do Supervisor (amostra só de desenvolvimento) depende de escolher o relatório certo.
2. A chave da reimportação é (campanha, amostra, avaliador): uma segunda amostra com o mesmo nome de campanha sobrescreve em silêncio as notas humanas da primeira.
3. Linha esvaziada numa reimportação deixa a nota antiga no banco, mas o relatório sai com n menor.
4. Dois `sample_id` com o mesmo `request_id` são aceitos (só por edição manual).
5. O intervalo do kappa descarta reamostras indefinidas e pode sair enganoso em séries muito assimétricas (ex.: "1,00 a 1,00").
6. Lacunas de teste: embaralhamento final, vazamento do veredito na coluna de status, ordenação pela nota do juiz, rótulo "95%", atualização de veredito e nota, `ROLLBACK`.
7. "linha N" nos erros é a linha física do arquivo, não a da planilha (o `sample_id` ao lado resolve).
8. A amostra é balanceada, não proporcional; o relatório não diz "sem ponderação".
9. O heurístico de conta do juiz programado marca preço público junto de "sua conta" (dublê de teste).

**Ambiente:** o disco C: chegou a 0 MB livres durante a revisão (uma cópia de trabalho do Reviewer foi truncada, refeita e conferida por hash); o Supervisor liberou 3,2 GB de diretórios temporários das próprias suítes estritas. `eval --scripted` deixa diretórios `eval-*` em `%TEMP%` (98, 116 MB).

**Decisão do Supervisor:** os P3 1 a 6 e 8 vão ao Developer do Time B numa rodada curta antes do QA; a amostra da calibração do responsável sai só da campanha de desenvolvimento.
