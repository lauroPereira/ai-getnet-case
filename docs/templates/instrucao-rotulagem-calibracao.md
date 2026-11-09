# Instrução de rotulagem: calibração por afirmação

Instrução única para quem rotula a amostra de calibração: o rotulador humano e cada membro do painel de modelos recebem este texto, sem alteração, junto dos mesmos arquivos. Cada membro do painel trabalha em sessão separada.

As linhas `#` dos dois CSVs e a nota de cada pacote são resumos (as do `sample.csv` da amostra atual vêm da v0.8.0); onde diferirem desta instrução, vale esta instrução. A coluna `unsupported_claim` fica em branco: o veredito sai das marcas.

## O que você recebe

- `sample.csv`: uma linha por resposta, com as colunas de notas em branco.
- `sample-claims.csv`: uma linha por afirmação de cada resposta, com a coluna `verdict` em branco.
- `<sample_id>.md`, um por resposta: a mensagem do lojista, a resposta, a evidência completa item por item, com os cortes anotados, e as afirmações numeradas. O título de cada item traz o tipo: `passage` (trecho de página oficial ou de procedimento), `tool_result` (resultado de ferramenta sobre a conta do lojista), `trace` (protocolo de encaminhamento registrado pelo sistema), `web_page` (texto de uma página citada pela busca) ou `web_summary` (o resumo que a busca devolveu ao assistente).

## Marca de cada afirmação (`verdict`)

Leia o pacote e marque cada afirmação com uma destas quatro. As regras são as mesmas que o juiz recebe (`prompts/judge.v5.md`), caso a caso e com a mesma marca.

- `supported`: um trecho (`passage`), um resultado de ferramenta (`tool_result`), o protocolo registrado (`trace`), uma página citada (`web_page`) ou a mensagem do lojista diz isso. Também `supported`: afirmação que só repete um item ou tira dele uma consequência direta (um pedido com status pendente e sem data de ativação ainda não está ativo).
- `partial`: a evidência sustenta só parte, ou numa forma mais fraca, ou a afirmação pode estar num trecho cortado. Também `partial`: afirmação coerente com o resumo da busca (`web_summary`) e com as fontes listadas quando nenhuma página citada (`web_page`) a contém. `partial` não é para afirmação que só divide o tema com um item: regra que o item não diz fica `generic` ou `not_found`.
- `generic`: orientação ou generalização dita como fato, sem item que a sustente (por exemplo "as taxas variam conforme o contrato", "a aprovação depende de análise" ou "fale com o seu banco" quando nenhum item diz isso). Dizer que as condições, taxas ou termos do lojista dependem do contrato, do perfil ou de uma análise é `generic` quando nenhum item diz essa dependência, mesmo que um item trate da mesma taxa ou do mesmo produto. Mandar o lojista ao contrato ou à proposta "para ver as condições que se aplicam", sem item que diga isso, é `generic` pelo mesmo motivo: contrato e proposta não são canais (veja os próximos passos abaixo). Vale também em resposta vinda da busca: ser coerente com o resumo da busca ou com os títulos das fontes não torna essa frase `partial`.
- `not_found`: fato, valor, data, status ou promessa que a evidência não contém ou contradiz. Afirmação que o resumo da busca ou as fontes contradizem é `not_found`. Dado da conta do lojista (valor, data, status) que nenhum `tool_result` mostra é `not_found`. Afirmação de que não há mais nada (não há outras etapas, opções ou canais) quando um item lista outra é `not_found`.

Lacunas, próximos passos, cortesia, encaminhamento, ressalvas e a data da resposta recebem as marcas abaixo, e não `generic` nem `not_found`, salvo onde a regra diz outra coisa:

- **Lacuna.** Dizer que o assistente não encontrou, não leu ou não confirmou algo (a conta não foi encontrada, o dado não está disponível, não dá para consultar ou executar) é lacuna, não fato: `supported`, porque evidência sem item que mostre a coisa é o retrato dessa lacuna. Dizer que as fontes não informam o que o lojista perguntou (nenhuma taxa é informada para aquele produto) também é lacuna, mesmo quando dito como "a Getnet não informa". Só é `not_found` quando um item mostra que a coisa foi encontrada ou lida, ou a informa. Dizer que a Getnet ou um produto não oferece, não aceita, não cobra, não permite ou não tem algo é fato, não essa lacuna: segue a regra do `not_found` acima, como a afirmação de que não há mais nada (não há outras etapas, opções ou canais).
- **Próximo passo.** Mandar o lojista a um canal da Getnet (o app, o portal, o atendimento, uma pessoa) para ver o que a resposta não deu, ou para seguir depois de uma lacuna que a resposta diz, é próximo passo: `supported` quando um item cita esse canal, `partial` quando nenhum cita. Contrato e proposta não são canais: mandar o lojista ao contrato ou à proposta "para ver as condições que se aplicam", sem item que diga isso, é `generic`, como a dependência do contrato. Frase que manda o lojista a um canal da Getnet e também ao contrato ou à proposta para ver as condições é `generic`: a parte do contrato prevalece. Orientação que supõe um fato que a evidência não tem (que um banco ou outro terceiro precisa resolver, que esperar resolve) continua `generic`.
- **Cortesia.** Oferecer o que o assistente ainda pode fazer (responder dúvidas gerais, encaminhar o caso) é cortesia: `partial`.
- **Encaminhamento.** Com status `handoff`, dizer que o caso foi passado a uma pessoa que vai responder ou entrar em contato repete o status: `supported`. Promessa além disso (um prazo, um resultado, um cancelamento) continua precisando de um item que a diga: sem esse item, é `not_found`.
- **Ressalva.** Ressalva que só qualifica um número que a própria resposta dá, como aproximado ou como algo que muda com o tempo ou entre fornecedores (uma cotação que muda durante o dia, uma previsão que pode mudar), não acrescenta fato: `partial`. Dizer o que vale para o lojista ou para um produto, taxa ou contrato da Getnet não é essa ressalva.
- **Data da resposta.** Dizer a data do dia da resposta, ou a do dia anterior ou seguinte, só situa a resposta no tempo e não acrescenta fato: `partial`. É `not_found` quando um item ou a mensagem do lojista mostra outra data para esse dia. A data de um acontecimento (um pagamento, um prazo, um pedido) não é essa afirmação.

O resumo da busca (`web_summary`) não é página: mostra só o que a busca disse ao assistente. Afirmação encontrada só no resumo da busca nunca é `supported`.

Afirmação do tipo `standard` (encaminhamento, protocolo, pedido de esclarecimento, cortesia) também recebe marca, mas não conta contra a resposta. Recusar, pedir esclarecimento ou declarar o que não foi confirmado não é afirmação sem suporte. Faltou uma afirmação na lista? Acrescente uma linha com o mesmo `sample_id` e `request_id`, `n` vazio, o texto em `added_claim` e a marca em `verdict`.

## Notas de cada resposta (`sample.csv`)

Para cada resposta, um inteiro de 1 (ruim) a 5 (excelente) em cada critério:

- `groundedness`: o que a resposta afirma se apoia na evidência ou na mensagem do lojista.
- `factual_correctness`: o que a resposta afirma concorda com a evidência e não se contradiz.
- `relevance`: a resposta trata do que foi perguntado, ou recusa, pede esclarecimento ou encaminha quando esse é o desfecho certo.
- `usefulness`: o lojista consegue agir com a resposta; ela é clara e diz as lacunas em vez de escondê-las.

A coluna `unsupported_claim` fica em branco: o veredito é calculado das marcas (sim quando alguma afirmação que não é `standard` for `generic` ou `not_found`). A coluna `note` é opcional.

## O que não fazer

- Não use conhecimento externo: julgue só a resposta contra a evidência do pacote. Não busque nada na internet.
- Não veja notas, marcas ou rótulos de ninguém: nem do juiz, nem de outro rotulador, nem de outro membro do painel.
- Não altere `n`, `kind` nem `claim`, não apague linhas nem a linha `amostra:` (o SHA-256 dela é conferido na importação) e não renomeie colunas.

## Devolução

Devolva os dois CSVs preenchidos, `sample.csv` e `sample-claims.csv`, em UTF-8, com o mesmo separador e os mesmos nomes de coluna. Resposta que você não avaliou fica com todas as notas e marcas em branco; resposta avaliada pela metade é recusada na importação. Na importação, cada rotulador é declarado com o seu tipo: `--rater <nome>:human` ou `--rater <nome>:model:<modelo1>+<modelo2>`.

## Painel: junção dos dois membros

Feita pelo operador, depois da devolução, sem chamada a modelo. O rótulo do painel é a concordância dos dois membros:

```text
eval-calibrate --merge-panel <membro1>-claims.csv <membro2>-claims.csv --sample-csv <membro1>.csv <membro2>.csv --out <painel>.csv
```

Os dois CSV de notas (`--sample-csv`) são obrigatórios, e nenhum dos dois arquivos de saída pode existir. O comando confere que os dois membros são da mesma amostra (SHA-256 das afirmações e identidade das respostas) e grava `<painel>.csv` e `<painel>-claims.csv`: a marca onde os dois deram a mesma, vazia onde divergem; cada nota e o veredito onde coincidem, vazios onde não. Resposta em que não coincidem em nota nem veredito, ou que um membro não avaliou, fica em branco (o painel não a avaliou). Afirmações acrescentadas pelos membros não passam ao painel. O comando mostra quantas marcas cada membro deu e em quantas concorda com o outro. Importe o painel com `--rater painel:model:<modelo1>+<modelo2>` (exatamente dois modelos; a ordem não importa: eles são gravados em ordem alfabética). O veredito do painel é o da coluna `unsupported_claim`: em branco, o painel fica sem veredito, e as marcas servem só para conferi-lo. Nota ou veredito que o painel deixou em branco numa resposta que o humano avaliou exige adjudicação, como uma divergência. Toda resposta selada que o humano avaliou precisa de ouro em cada nota e no veredito: a que o painel deixou inteira em branco também exige adjudicação; fora da amostra selada, ela só fica sem ouro. Marca de afirmação em branco só fica sem ouro.
