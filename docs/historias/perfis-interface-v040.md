# História de uso: perfis, Router e interface v0.4.0

## Objetivo e pessoa usuária

Versão 1, 2026-10-27. Lojista/avaliador sintético conversa por Streamlit,
compara mecanismos de roteamento e inspeciona o resultado; administrador
publica perfis compatíveis sem expor segredos ou alterar execução em andamento.

## Critérios e candidato

RF-41–43, RF-47–53; CA-28 e CA-32–37. [Plano](../specs/perfis-interface-v040-plano.md),
tarefas 27–32. Candidato ainda não implementado; será fixado por SHA backend
e hashes/SHA frontend, contratos, dados, catálogo e ambiente antes de QA.

## Condições iniciais

Dois projetos, backend v0.3.0 como referência, dados sintéticos, credenciais
de teste sem valor real. Caminho sem custo usa API/adaptadores simulados;
caminho real exige catálogo verificado e autorização monetária própria.
Nenhuma porta pública ou alteração de roteador nesta rodada.

## Momentos da história

| Momento | Ação normal | Resultado esperado | Critério | Evidência | Retorno |
| --- | --- | --- | --- | --- | --- |
| Entrada | Abrir Streamlit em modo simulado e entrar como demo | Identificação do modo, sessão/escopo corretos, nenhum segredo | RF-53, CA-35 | Pendente | Encerrar sessão |
| Conversa | Escolher Referência e enviar cenário sintético; continuar | Resposta/estado/histórico preservados; perfil/versionamento efetivo visível | RF-43, RF-51 | Pendente | v0.3.0 legado |
| Híbrido | Selecionar JEV real e enviar após confirmar custo | Decisão real JEV com versão/tempo/custo; especialistas conforme perfil | CA-32 | Pendente real | Escolha explícita de outro mecanismo |
| Falha JEV | Provedor indisponível ou decisão inválida | Erro claro, sem trocar mecanismo silenciosamente | CA-33 | Pendente | Nova ação explícita |
| Comparação | Comparar LLM/JEV e usar a decisão escolhida | Só dois Routers na comparação; atendimento uma vez; custos separados | CA-34 | Pendente | Registro expirado/conflito claro |
| Inspeção | Abrir execução e atualizar a tela | Snapshot/fontes/ferramentas/versões; real/simulado/gravado distintos; sem nova chamada | CA-35–36 | Pendente | Reabrir registro |
| Administração | Demo tenta publicar; admin publica perfil compatível | Demo 403; versão publicada imutável; execução corrente não muda | CA-36–37 | Pendente | Perfil anterior publicado |
| Limites | Selecionar capacidade incompatível ou custo desconhecido | Opção indisponível e rejeição backend antes da chamada | CA-37 | Pendente | Perfil compatível |
| Isolamento | Acessar conversa/execução/comparação de outro dono | Recusa sem revelar dados; comparação não pode ser reutilizada | RF-53, RNF-10 | Pendente | Própria sessão |
| Compatibilidade | Usar HTTP legado e MCP sem interface | Núcleo e jornadas v0.3.0 preservados | CA-28, RF-43 | Pendente | tag v0.3.0 |

## Experiência e exceções

Loading, vazio, expiração de sessão, backend indisponível e conflito de versão
devem permitir recuperação explícita. Testes AppTest não substituem integração
real JEV nem evidência funcional por HTTP. Rerun não reenvia mensagem/publicação.
Valores financeiros continuam derivados das ferramentas em centavos.

## Resultado da rodada

Não executada. Nenhum CA da v0.4.0 está declarado concluído por esta história.
Defeito reproduzível vira tarefa; credencial/provedor indisponível é dependência.

## Como terminou

A pessoa deverá conseguir conversar, identificar exatamente o perfil/mecanismo
usado e comparar decisões sem duplicar atendimento. O QA relatará o resultado
efetivamente observado e as limitações do candidato, sem presumir publicação.
