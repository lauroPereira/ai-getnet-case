# 0008. Registro versionado de configuração com snapshot por execução

## Título

Guardar perfis de modelos por agente, prompts e rubricas como versões imutáveis com ativação explícita, e congelar um snapshot no início de cada execução.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

Os incrementos pedem perfis de modelos por agente, comparação entre perfis, avaliação com rubricas versionadas e um ciclo de melhoria que propõe mudanças em prompts e configurações. Hoje prompts são arquivos e o modelo é único por configuração de ambiente.

## Decisão

- Tabelas de versões para perfis, prompts e rubricas; uma versão publicada nunca muda; a ativa é um ponteiro.
- Os arquivos em `prompts/` continuam sendo a semente versionada no Git; edições pela interface criam versões candidatas no banco.
- Cada execução grava o snapshot (perfil, versões de prompts, versão da base) e o usa do início ao fim.
- Catálogo de modelos com capacidades (ferramentas, saída estruturada, busca web) validado contra a API dos provedores; combinações incompatíveis são recusadas.
- Provedores por agente: OpenAI, DeepSeek e TypeSafe (JEV, só no Router). Isto complementa a decisão 0005, em que a DeepSeek era apenas experimento opcional; o padrão continua OpenAI e nenhum fallback pago é automático.
- Orçamento, permissões, guardrails e regras financeiras não fazem parte do registro editável.

## Alternativas consideradas

- **Só arquivos e Git:** simples, mas não permite candidatas e ativação pela interface.
- **Variáveis de ambiente por agente:** exigem reinício e não permitem comparação por requisição.

## Consequências

Comparações reproduzíveis e retorno imediato a uma versão anterior. Aumenta o modelo de dados e exige migrar os prompts atuais como versão inicial.

## Data

2026-10-26
