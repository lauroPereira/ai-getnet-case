# 0004. Dados sintéticos em SQLite e ferramentas como funções de domínio

## Título

Guardar os dados sintéticos em SQLite e implementar as ferramentas de suporte como funções de domínio, com MCP como adaptador posterior.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

O Customer Support precisa de pelo menos duas ferramentas sobre dados do usuário. Não há acesso a sistemas reais; os dados são sintéticos e precisam ser consistentes entre fontes (agenda, repasse, dispositivos, autorizações, contrato). O cliente deve ser vinculado pelo servidor, nunca pelo modelo. A vaga cita MCP, mas o desafio não o exige, e o prazo é desconhecido.

## Decisão

- SQLite com seed determinístico, recriado na inicialização, com datas relativas ao relógio injetado.
- Cada ferramenta é uma função de domínio tipada que recebe o contexto do cliente e argumentos validados, verifica o vínculo cliente-recurso e devolve resultado ou erro estruturado.
- O agente acessa as ferramentas por um registro com lista de permissões por agente.
- Na fatia 2, um servidor MCP local expõe as mesmas funções, sem duplicar regra de negócio.

## Alternativas consideradas

- **Servidor HTTP de mocks por domínio desde o início:** mais realista, mas acrescenta processos e contratos antes de validar o núcleo. Continua sendo opção para o pricing fictício da fatia 3.
- **MCP desde a fatia 1:** aproveita a experiência anterior, mas adiciona transporte e processo ao caminho crítico.
- **JSON estático:** sem consultas por período nem consistência entre tabelas.

## Consequências

Ferramentas testáveis diretamente, sem rede. Isolamento entre clientes verificado em um único ponto. O MCP entra sem reescrever o domínio, mas a demonstração de MCP fica para a fatia 2.

## Data

2026-10-26
