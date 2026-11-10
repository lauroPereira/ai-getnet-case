# Resultado da v0.13.0

## Capacidades

- A interface entra por authorization code com PKCE S256 e refresh token rotativo; reuso de refresh revoga a família; o logout revoga acesso e família. A interface não tem campo de senha; o grant `password` continua na API para a CLI e o smoke.
- Tokens de emissores OIDC configurados (Dex no perfil `oidc`) são aceitos; principais externos ficam separados dos locais por `sub` e emissor; emissor desconhecido é recusado.
- Dois workers da API dividem as comparações por lease; as reservas pagas ficam cercadas pela lease, uma tentativa paga nunca é refeita sem `retry_failed`, custo desconhecido bloqueia a retomada até ser reconciliado, e uma recusa de orçamento nunca conta como célula concluída.
- Entregas de webhook esgotadas podem ser reenviadas; casos órfãos são completados na subida.
- Um adaptador opcional leva casos ao Telegram do operador e devolve a resposta ao lojista.
- Spans opcionais por OTLP e um painel Grafana sobre `/metrics`.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.944 testes aprovados, sem falhas nem testes pulados; Ruff, links e caminhos pessoais limpos |
| Interface | 158 testes aprovados (1 pulado sem o backend no caminho) e 5 de integração contra a API em processo |
| Dois workers | Dono de uma comparação suspenso antes e depois da reserva paga: nenhuma célula paga duas vezes; a lease perdida é registrada |
| Login pela interface | 10 logins num navegador real: 10 sessões abertas, nenhum login órfão; código emitido num worker e trocado no outro; renovação, reuso de refresh e logout com revogação |
| Sistema com Docker | Emissor externo (Dex), dois workers com 10 exemplos, reenvio e órfão, OTLP e painel, e o caso sintético levado ao Telegram, assumido e respondido pelo operador com a resposta no histórico do lojista |
| Migrações | 0015 e 0016 em sequência após a 0014, nos dois sentidos, sem perda de dados |

Gasto da campanha `v0130-qa`: US$0,064 (teto US$0,15). A validação final da interface e do candidato integrado não usou chamadas pagas.

A decisão está registrada na [ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md).
