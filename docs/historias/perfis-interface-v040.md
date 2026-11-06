# História de uso: perfis, Router e interface v0.4.0

## Objetivo e pessoa usuária

Versão 1, 2026-10-27. Lojista sintético conversa por Streamlit,
compara mecanismos de roteamento e inspeciona o resultado; administrador
publica perfis compatíveis sem expor segredos ou alterar execução em andamento.

## Critérios e candidato

RF-41–43, RF-47–53; CA-28 e CA-32–37. [Plano](../specs/perfis-interface-v040-plano.md),
tarefas 27–32. Candidato r6 fixado por SHA backend e hashes do frontend
([manifesto](../evidence/v040-candidato-r6.json)).

## Condições iniciais

Dois projetos, backend v0.3.0 como referência, dados sintéticos, credenciais
de teste sem valor real. Caminho sem custo usa API/adaptadores simulados;
caminho real exige catálogo verificado e autorização monetária própria.
Nenhuma porta pública ou alteração de roteador nesta rodada.

## Momentos da história

| Momento | Ação normal | Resultado esperado | Critério | Evidência | Retorno |
| --- | --- | --- | --- | --- | --- |
| Entrada | Abrir Streamlit em modo simulado e entrar como demo | Identificação do modo, sessão/escopo corretos, nenhum segredo | RF-53, CA-35 | QA r5 e r6, modelos programados | Encerrar sessão |
| Conversa | Escolher Referência e enviar cenário sintético; continuar | Resposta/estado/histórico preservados; perfil/versionamento efetivo visível | RF-43, RF-51 | QA r5 e r6, modelos programados | v0.3.0 legado |
| Híbrido | Selecionar JEV real e enviar após confirmar custo | Decisão real JEV com versão/tempo/custo; especialistas conforme perfil | CA-32 | JEV real na v0.5.0 | Escolha explícita de outro mecanismo |
| Falha JEV | Provedor indisponível ou decisão inválida | Erro claro, sem trocar mecanismo silenciosamente | CA-33 | Testes e revisão (falha real de provedor não exercitada) | Nova ação explícita |
| Comparação | Comparar LLM/JEV e usar a decisão escolhida | Só dois Routers na comparação; atendimento uma vez; custos separados | CA-34 | QA r5 e r6, modelos programados | Registro expirado/conflito claro |
| Inspeção | Abrir execução e atualizar a tela | Snapshot/fontes/ferramentas/versões; real/simulado/gravado distintos; sem nova chamada | CA-35–36 | QA r5 e r6, modelos programados | Reabrir registro |
| Administração | Demo tenta publicar; admin publica perfil compatível | Demo 403; versão publicada imutável; execução corrente não muda | CA-36–37 | QA r5 e r6, modelos programados | Perfil anterior publicado |
| Limites | Selecionar capacidade incompatível ou custo desconhecido | Opção indisponível e rejeição backend antes da chamada | CA-37 | QA r5 e r6, modelos programados | Perfil compatível |
| Isolamento | Acessar conversa/execução/comparação de outro dono | Recusa sem revelar dados; comparação não pode ser reutilizada | RF-53, RNF-10 | Regressão automatizada | Própria sessão |
| Compatibilidade | Usar HTTP legado e MCP sem interface | Núcleo e jornadas v0.3.0 preservados | CA-28, RF-43 | Regressão automatizada | tag v0.3.0 |

## Experiência e exceções

Loading, vazio, expiração de sessão, backend indisponível e conflito de versão
devem permitir recuperação explícita. Testes AppTest não substituem integração
real JEV nem evidência funcional por HTTP. Rerun não reenvia mensagem/publicação.
Valores financeiros continuam derivados das ferramentas em centavos.

## Resultado da rodada

Executada no QA r5 e r6 com inferência e embeddings programados ([QA r6](../evidence/v040-qa-r6.md),
[resultado](../evidence/v040-resultado.md)); a chamada real ao JEV (CA-32) foi feita na v0.5.0.

## Como terminou

A pessoa deverá conseguir conversar, identificar exatamente o perfil/mecanismo
usado e comparar decisões sem duplicar atendimento. O QA relatará o resultado
efetivamente observado e as limitações do candidato, sem presumir publicação.
