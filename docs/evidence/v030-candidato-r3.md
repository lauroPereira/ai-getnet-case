# Candidato: v0.3.0 local — rodada 3

## Resultado e critérios

Jornadas de preço/contestação, bandeiras e consulta de cancelamento, com correção de isolamento e regressões da rodada real. Tarefas 21 a 25; critérios CA-21, CA-22, CA-23, CA-28 e CA-31. [História versão 1](../historias/jornadas-v030.md), [plano](../specs/jornadas-v030-plano.md) e [registro de validação](v030-resultado.md).

## Identificação

- Branch: `codex/v0.3.0-jornadas`; main/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- **45 arquivos locais** identificados no [manifesto JSON](v030-candidato-r3.json).
- Fingerprint completo: `052bc6ca8e10f053cf9f2612e27563e3367bef34e8adb493657869598f2bc660`.
- Fingerprint de código/configuração de execução: `f0c8d937187e8929a214634cafd3416a8f912314ada5c462be5184c77d983d12`.
- Imagem API: `sha256:af1334f5eb9a1e935747411f1e4696b26c5a9d11a13bb0f237ba67870e1e633c`.
- Imagem mocks: `sha256:025584d7927b745f645b15a67e1ec79c581fe7bbd932cd305dc0c60cb6005002`.
- Nenhum commit, push, PR, merge ou tag nesta sessão.

O manifesto documenta o algoritmo do agregado, os hashes individuais, os 125 insumos conferidos do build, os scripts temporários de validação e os oito caminhos que diferem do candidato r1. Agregado: SHA-256 dos bytes UTF-8 do mapa de arquivos serializado por `json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=True)`, sem quebra final. Hashes individuais usam bytes originais.

## Ambiente e dados

Windows e versões Python no JSON, imagem Python 3.13.13, Docker Engine 29.8.0. Projeto isolado `getnet-v030-validation`, mocks interno. Testes sem credenciais e runtimes novos. Rodada real usa somente OpenAI, fontes públicas, dados sintéticos, índice persistido de teste e guarda compartilhada com teto adicional US$0,15. Runtime anterior do responsável preservado.

## História e verificações

- História e testes identificados no manifesto; 165 testes, Ruff, estrutura e skills aprovados na passagem [Developer r3](v030-developer-r3.md).
- Build r3 aprovado; nenhum dos 125 insumos mudou durante o build.
- Novo smoke entre contêineres, revisão independente e revalidação real em preparação.
- Relatórios r1 e sua medição são históricos e preservados; não comprovar aceite deste candidato com os resultados anteriores no escopo alterado.

## Pareceres e validade

Reviewer deve reavaliar P2 e mudanças da tarefa 25 independentemente. QA aguarda parecer apto. Mudança de produto, critérios, dados relevantes ou história exige revalidação do escopo afetado. Relatórios de evidência são externos ao fingerprint do produto e não podem alterar os fatos registrados.

## Decisão e recuperação

Próximo: revisão, revalidação real dentro do mesmo teto e QA. Integração/publicação dependem de autorização do responsável. Recuperação prevista por v0.2.0 e esquema 0005 → 0004 em banco sintético isolado.
