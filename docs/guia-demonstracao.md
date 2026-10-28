# Guia da demonstração v0.6.0

Guia único para subir o backend (Docker), a interface Streamlit (nativa) e conduzir a demonstração. Para a especificação, veja [fechamento-v060.md](specs/fechamento-v060.md); para o teste manual, [roteiro-teste-manual.md](roteiro-teste-manual.md); para o vídeo, [roteiro-video.md](roteiro-video.md).

Três modos de execução, que não se confundem:

| Modo | O que roda | Custo | Para quê |
| --- | --- | --- | --- |
| Docker (backend) | API + Qdrant + `mocks` empacotados (`docker compose`) | Chamadas reais, limitadas pela guarda de orçamento | Demonstração e smoke da versão empacotada |
| Nativo | API com `uvicorn` no `.venv` do backend; Streamlit no ambiente do projeto web | Chamadas reais quando há chave | Desenvolvimento e QA |
| Testes | `pytest` com modelo programado, embeddings falsos e Qdrant em memória | Zero | Regressão; não prova qualidade de modelo |

## 1. Pré-requisitos

- Docker com Compose v2; Python 3.12+ para o projeto web (`ai-getnet-case-web`).
- Chave OpenAI (obrigatória para chamadas reais). DeepSeek e TypeSafe são opcionais (perfis Híbrido/Ajustado e Router JEV).
- Duas chaves de acesso da API `/v1`, escolhidas por você: uma **demo** (baixo privilégio, para compartilhar) e uma **admin** (só sua).

## 2. Configurar o backend (`.env`)

```bash
cp .env.example .env
```

Preencha no `.env`: `OPENAI_API_KEY`, opcionalmente `DEEPSEEK_API_KEY` e `TYPESAFE_API_KEY`, `API_DEMO_ACCESS_KEY`, `API_ADMIN_ACCESS_KEY`. Controles relevantes:

- `BUDGET_LIMIT_USD` (padrão 1,00, máximo 5,00): teto persistente de todas as chamadas pagas; o primeiro valor gravado ao lado do ledger (`budget.sqlite3.limit`) nunca é aumentado por remontagem.
- `MAX_REQUEST_COST_USD` (0,05) e `MAX_REQUEST_SECONDS` (90): limites por atendimento.
- `DEMO_SESSION_MESSAGE_LIMIT` (20): ações pagas por sessão demo (mensagens, execuções novas de comparação, comparação de Routers e avaliação por IA), recusadas no backend com `429` quando excedidas; recusas sem inferência (por exemplo `409` de comparação obsoleta, orçamento negado antes da primeira chamada ou células de comparação puladas) não contam ou são devolvidas.
- `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL` (`openai`/`gpt-6-luna`): avaliador fixo da avaliação por IA sob demanda, independente do perfil avaliado.

## 3. Subir o backend (Docker)

```bash
docker compose up --build -d
docker compose ps                      # api "healthy"
curl -s http://127.0.0.1:8000/ready    # index_chunks > 0, budget_remaining_usd
```

A API fica publicada só em `127.0.0.1:8000`; Qdrant e `mocks` ficam internos à rede do Compose. No primeiro arranque o contêiner semeia os dados sintéticos e constrói o índice (≈ US$0,001). Dados, traces, ledger e coleções ficam nos volumes `runtime` e `qdrant_storage`.

## 4. Subir a interface (Streamlit nativo)

No projeto `ai-getnet-case-web`, com o ambiente dele:

```powershell
python -m pip install -e ".[test]"
$env:BACKEND_API_URL = "http://127.0.0.1:8000"
streamlit run app.py                                     # uso local: http://localhost:8501
```

Na barra lateral escolha **Real (API)** e entre com a chave demo ou admin. **Simulado** e **Gravado** funcionam sem backend e são rotulados como tal. Os timeouts do cliente: 20 s para leituras (`BACKEND_TIMEOUT_SECONDS`) e 105 s para operações que esperam trabalho pago (`BACKEND_MESSAGE_TIMEOUT_SECONDS` = 90 s do backend + margem).

## 5. Preparar a demonstração (admin)

1. Entre como admin. Em **Administração → Perfis**, confira Referência, Híbrido e Ajustado publicados. Bancos novos já nascem com os três publicados; num banco anterior à v0.6.0 o Ajustado pode estar como rascunho: selecione-o e use **Publicar versão de rascunho**.
2. Em **Administração → Base de conhecimento**, anote a versão ativa (normalmente `kb_initial`).
3. Se for demonstrar o efeito da documentação, tenha à mão o texto `data/scenarios/kb-demo-devices-v2.md` e a [diferença esperada](evidence/v060-qa-preparacao.md).

## 6. Conduzir a demonstração

1. **Atendimento.** Escolha um cenário do catálogo (ou mensagem livre), o perfil e o Router (LLM/JEV) e envie. A conversa mostra a resposta e o estado do caso (estado, status, rota, versão da base, protocolo). Uma falha de transporte deixa a pergunta pendente; use **Atualizar conversa** (GET) — nada é reenviado.
2. **Comparação só dos Routers** (dentro de Atendimento): compara LLM × JEV sem atender; a decisão escolhida é usada uma única vez. Não se soma à comparação de perfis.
3. **Resultados.** Selecione a execução: modo (real/simulada/gravada), rota, etapas, ferramentas, modelo efetivo, tokens e custo por agente, versões (perfil, prompts, base), fontes e trechos recuperados, verificações determinísticas com origem (rótulo do cenário ou independentes de rótulo), falhas críticas individuais e avaliações ("não avaliado" quando não houver).
4. **Avaliação por IA.** Em Resultados: **Estimar avaliação por IA** (sem custo) → conferir método, rubrica, avaliador e estimativa → confirmar → **Avaliar com IA**. Avalia a resposta persistida, não repete o atendimento, custo separado. Repetir com a mesma configuração devolve o registro existente, salvo marcar "Repetir mesmo assim".
5. **Comparar perfis.** Em Resultados: escolha 2–3 perfis, até 3 cenários e 1–2 repetições → **Estimar comparação** (sem custo; mostra células novas e reaproveitadas, base fixa e se é exploratória) → confirmar → **Executar comparação** → **Atualizar comparação** até o estado final. Veja o gráfico custo × qualidade (rótulo com amostra e duração), o gráfico de custo por agente/modelo (escolha a barra e abra as execuções) e a tabela de células. Nada é criado no atendimento original.
6. **Efeito da documentação (admin).** Siga o [roteiro do bloco D](evidence/v060-qa-preparacao.md#roteiro-do-qa-real-campanha-v060-qa): V1, editar, candidata, testar, ativar, V2 em nova conversa, retornar, V1 de novo.

## 7. Compartilhar pelo IP público (janela definida)

Só o Streamlit é exposto. Antes de abrir:

1. Backend no ar, API em `127.0.0.1:8000`, saldo do teto conferido em `/ready`; compartilhe **apenas** a chave demo.
2. Inicie a interface escutando externamente e com o endereço do backend travado:

   ```powershell
   $env:BACKEND_API_URL = "http://127.0.0.1:8000"
   $env:LOCK_BACKEND_URL = "true"            # visitantes não podem trocar a URL do backend
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```

   HTTPS próprio, quando possível: gere um certificado (por exemplo `openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 7 -subj "/CN=demo"`) e acrescente `--server.sslCertFile cert.pem --server.sslKeyFile key.pem`. Certificado autoassinado gera aviso no navegador; explique isso ao visitante.
3. **Ações do responsável** (fora do código): redirecionar a porta 8501 no roteador para esta máquina; criar a regra de entrada no firewall do Windows para essa porta; verificar se o provedor usa CGNAT (IP do roteador diferente do IP público visto na internet impede o acesso direto).
4. Teste de **outra rede** (por exemplo, celular sem Wi-Fi) no endereço `http(s)://<IP público>:8501`. Se não abrir, registre o impedimento concreto (CGNAT, roteador ou firewall).
5. **Alternativa**: um túnel (por exemplo Cloudflare Tunnel ou ngrok) apontando para `localhost:8501`. É documentado como alternativa, não como dependência.
6. **Fim da janela**: pare o Streamlit, remova o redirecionamento e a regra de firewall, e, se quiser, troque a chave demo no `.env` e reinicie a API.

## 8. Encerrar

```bash
docker compose down        # mantém volumes (dados, ledger, coleções)
```

Não use `docker compose down -v` se quiser preservar o ledger de orçamento e as versões da base.

## Limitações conhecidas

- Comparações rodam em thread do processo da API: reiniciar a API no meio as deixa `failed` (`interrupted`) na próxima leitura; execuções concluídas antes ficam registradas.
- A estimativa de uma comparação usa o teto por atendimento (`MAX_REQUEST_COST_USD`) por célula nova: é um limite superior, não uma previsão.
- A qualidade do gráfico é a taxa de verificações determinísticas sob os mesmos rótulos; a nota do avaliador por IA só aparece quando todas as execuções do perfil foram avaliadas com a mesma configuração.
- Resultados lista as execuções desta sessão do navegador (não há listagem geral de execuções).
- O limite por sessão demo é por sessão: encerrar e entrar de novo abre outra sessão; o limite efetivo de gasto continua sendo o teto persistente do ledger.
