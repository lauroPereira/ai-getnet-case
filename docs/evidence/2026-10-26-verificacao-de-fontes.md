# Evidência: verificação de fontes oficiais e da imagem do enunciado

Tarefa: [01](../tasks/01-verificar-fontes-e-enunciado.md). Data: 2026-10-26. Verificação manual (navegador) e automatizada (cliente HTTP).

## Método

1. Páginas localizadas navegando a partir de `https://www.getnet.net/en/`, `https://site.getnet.com.br/` e da central `https://site.getnet.com.br/get-ajuda/`. Só entraram URLs visitadas.
2. `robots.txt` de cada host consultado com o user agent do projeto; todas as 32 URLs estão permitidas.
3. Cada página foi baixada por HTTP e extraída com trafilatura e BeautifulSoup. O texto foi comparado com o texto visível no navegador.
4. Resultado gravado em [data/sources/public-sources.json](../../data/sources/public-sources.json).

## Resultado por caso de uso

| Caso | Fontes verificadas | O que a fonte sustenta |
| --- | --- | --- |
| UC-01 Get Clássica vs Get Smart | `todas-as-maquininhas/`, `taxas/` | Ambas existem. Características e preços de aluguel de cada uma (ex.: Smart com 4G e bateria de até 12h; Clássica com reposição de bobina) |
| UC-03 Vendas de ontem | `get-ajuda-gestao-de-vendas/*`, `como-trocar-o-domicilio-bancario/` | Status de vendas e domicílio bancário; a data efetiva vem dos dados sintéticos |
| UC-04 Pix sem conta bancária | `duvidas/`, `pix/`, `get-ajuda-pix/*`, `get-ajuda-get-conta/*`, `todas-as-maquininhas/` | A chave Pix precisa estar ligada à conta de recebimento (domicílio bancário); a Get Conta pode ser usada como domicílio |
| UC-05 Maquininha sem internet | `como-configurar-o-wi-fi-na-sua-maquininha-getnet/`, `duvidas/` | Configuração de Wi-Fi, instalação de chip e teste de comunicação |
| UC-06 Antecipação | `get-ajuda-antecipacao-de-venda/*`, `plano-de-recebimento-reduzido/`, `antecipacao-reserva-financeira/`, `duvidas/` | O que é a antecipação, como antecipar e habilitar a automática |
| UC-08 Transação negada | `get-ajuda-erros-maquininha/*`, `como-fazer-uma-venda-na-maquininha-getnet/` | Só erros "ADQ" da maquininha. **Não há página sobre motivos de negativa**: o tratamento vem dos dados e da base fictícia |
| UC-09 Crediário | `crediario/` | Parcelamento em até 48x, com prazo e juros que variam conforme o emissor do cartão |
| UC-10 WhatsApp com Link de Pagamento | `link-de-pagamento/`, `descontinuacao-whatsapp-business/` | O pagamento pelo WhatsApp Business foi descontinuado em 15/01/2026; a venda pelo WhatsApp passa a ser feita enviando Link de Pagamento |

Nenhum produto citado nos exemplos ficou sem fonte. O caso de "sem evidência" do conjunto rotulado usará perguntas sobre produtos inexistentes.

## Extração

- 30 páginas têm texto suficiente por HTTP (`static`).
- 2 páginas são montadas por JavaScript (`dynamic`): `todas-as-maquininhas/` (as características das maquininhas não estão no HTML) e `taxas/` (tabela e comparativo). O texto renderizado foi capturado no navegador e salvo em `data/snapshots/public/rendered/`, com a origem registrada no manifesto. Para atualizar essas duas páginas é preciso capturar de novo pelo navegador.
- `link-de-pagamento/`: o elemento `main` tem pouco texto, mas o trafilatura recupera o conteúdo. A ingestão deve escolher o extrator por página e remover o rodapé comum da central de ajuda ("Respondeu à sua dúvida?", contatos).
- A tabela de `taxas/` reflete a seleção padrão da página e não representa condições individuais.

## Imagem do enunciado

A imagem mostra o "Agent Workflow": Input → Router → Knowledge Agent, Customer Support Agent e "Your Custom Agent" (seta tracejada, opcional), cada um com suas Tools → **Personality** → Output.

O nó **Personality** não estava no discovery nem na especificação 0.1. Ele foi incorporado como RF-37: toda resposta passa por uma etapa que aplica a voz do assistente antes da saída, sem alterar fatos. "Your Custom Agent" corresponde ao Escalation Agent.

## Limitações

- O conteúdo do site pode mudar; a cópia versionada fixa o estado de 2026-10-26.
- O `curl` do Git Bash local falhou (código 43); as requisições foram feitas pelo cliente HTTP do Python.
