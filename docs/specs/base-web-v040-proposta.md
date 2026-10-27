# Base proposta para ai-getnet-case-web

Proposta aprovada no plano completo em 2026-10-27. Base criada e validada:
[manifesto inicial](../evidence/v040-base-web.json), tarefa 30. A criação do
projeto separado e o template foram decididos na especificação/decisão 0007;
o texto abaixo preserva o conjunto apresentado antes da execução.

## Destino e fonte

- Destino: `C:\workspace\ai-getnet-case-web`, ausente na conferência inicial.
  Reconferir ausência/vazio e resolução absoluta antes de qualquer escrita.
- Fonte: snapshot local `ai-dev-template`, versão **0.2.0** no manifesto.
  O acesso Git da fonte não foi obtido na execução restrita; origem deve
  registrar hashes de todos os componentes efetivamente copiados, sem
  presumir fonte limpa ou um commit não conferido.
- Projeto independente, sem submodule/subtree ou dependência do template.
  A fonte e os arquivos protegidos do backend permanecem inalterados.

## Conjunto de arquivos

Copiar somente os componentes reutilizáveis do manifesto: instruções
canônicas, `skills/`, `docs/templates/`, `docs/wiki/agents/`, READMEs
estruturais, `evals/tasks/`, `evals/expected/` e scripts pertinentes em
`tools/scripts/`. Gerar `.agents/skills/` e `.claude/skills/` pelo script de
sincronização do destino e verificar equivalência.

Criar README próprio em inglês, `.gitignore`, `.agent-template.json` e
`docs/wiki/origem-template.md` com versão/hashes/omissões/adaptações. SDD
ativo, com especificação/tarefas/história próprias da interface, vinculadas
ao contrato backend. Produto será implementado depois pelo Developer:
`pyproject.toml`, pacote Streamlit, cliente HTTP, fixtures sintéticas,
testes e execução local/Docker apropriada.

Não copiar `.git`, `.env`, configurações locais/globais, dados, segredos,
`docs/raw/`, aplicação, specs, tarefas, histórias, decisões ou evidências
reais de qualquer repositório. Não copiar o README humano do template.
Não criar remoto ou efetuar commit/push nesta preparação.

## Texto novo proposto para AGENTS.md

Inserir após o título, preservando as regras canônicas do template:

```markdown
## Sobre este projeto

- **Nome:** ai-getnet-case-web.
- **Objetivo:** interface Streamlit para o assistente multiagente de lojistas;
  conversa, perfis, comparação LLM/JEV e inspeção de resultados via API HTTP.
- **Stack:** Python, Streamlit, cliente HTTP e pytest; backend separado.
- **Contratos:** consumir somente API /v1 documentada pelo backend. Não acessar
  SQLite, Qdrant, arquivos ou credenciais de provedores do backend.
- **Idioma:** documentação de trabalho em português; código, prompts e README
  em inglês. Textos da interface coerentes com o idioma da pessoa usuária.
- **Fluxo:** SDD ativo e papéis Supervisor, Developer, Reviewer e QA. Revisão
  independente e história de uso antes da integração.
- **Git:** enquanto não inicializado, identificar candidatos por hashes.
  Depois, main é a base; criar repositório/commit/push exige autorização.
- **Privacidade:** somente dados sintéticos e fontes públicas; não copiar
  discovery, documentos privados, credenciais ou dados de clientes reais.
- **Custos:** chamadas pagas passam exclusivamente pelo backend e por sua
  guarda persistente global de US$5. Reruns/navegação não iniciam chamadas.
- **Delegação:** somente com autorização explícita de escopo, quantidade,
  modelo e esforço; não herdar nem trocar por modelo mais caro.
```

Na seção canônica de branches, acrescentar a condição explícita antes do
fluxo: **“O fluxo abaixo se aplica quando o Git estiver inicializado; antes
disso, preservar candidatos por hashes e solicitar autorização para a
integração inicial.”** Demais aprovações e proteções são preservadas; o
snapshot não importa autorizações do backend ou do template.

## Adaptação proposta de CLAUDE.md

Preservar o conteúdo canônico e acrescentar seção `Sobre este projeto` com
nome, finalidade Streamlit, SDD ativo, consumo exclusivo de `/v1`, dados
sintéticos e proibição de chaves de provedores na interface. Aplicar a mesma
condição para Git ainda não inicializado. Não instalar configuração global.

## Validação e recuperação

Supervisor prepara somente a base e registra a origem; Developer implementa
o produto. Validar estrutura, skills sincronizadas, caminhos/links e ausência
de conteúdo de origem proibido; depois testes do cliente e AppTest sem APIs.
Manifesto final identifica backend por SHA e frontend por hashes até Git.
Identidade sugerida para futura inicialização Git é
`lauroPereira <lauro.s.pereira@gmail.com>`, a confirmar na autorização dessa
integração; nenhuma identidade é configurada silenciosamente.

Se destino estiver ocupado, interromper sem sobrescrever. Recuperação segura:
manter a nova pasta local sem executar a interface; eventual remoção exige
confirmação específica. Backend continua executável pela tag v0.3.0.

## Aprovação submetida

Criar somente arquivos novos nesse destino, incluindo o AGENTS/CLAUDE com as
adaptações acima e as cópias de skills geradas. Nenhuma alteração de governança
no backend. A skill [project-create](../../skills/project-create/SKILL.md)
determina: “Destino fora do workspace exige a autorização operacional
correspondente.” Essa escrita e os arquivos protegidos novos compõem a
aprovação da v0.4.0; publicação/Git remoto ficam para decisão posterior.
