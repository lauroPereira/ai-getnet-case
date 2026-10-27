# Candidato: v0.3.0 local — rodada 4

## Resultado e critérios

Mesmo produto e história do [candidato r3](v030-candidato-r3.md), com correção das verificações de negação/evidência insuficiente dos cenários. Tarefas 21 a 25; RF-08, RF-15, RF-16, RF-32 a RF-34 e RF-46; CA-21 a CA-23, CA-28 e CA-31.

## Identificação

- Branch `codex/v0.3.0-jornadas`; base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- [Manifesto JSON](v030-candidato-r4.json): **46 arquivos locais**, fingerprint `d626b894b143a496a8f9d67db7d50f5088d4fc84d10e39b51fbd958d90cfef94`.
- Runtime preservado: `f0c8d937187e8929a214634cafd3416a8f912314ada5c462be5184c77d983d12`.
- API `sha256:af1334f5eb9a1e935747411f1e4696b26c5a9d11a13bb0f237ba67870e1e633c`.
- Mocks `sha256:025584d7927b745f645b15a67e1ec79c581fe7bbd932cd305dc0c60cb6005002`.

Desde r3, somente `tests/scenarios/business_journeys.jsonl` e `tests/integration/test_evaluation_runner.py` mudaram. Os 125 insumos das imagens foram reconferidos; reutilização das mesmas imagens justificada por identidade dos insumos e do runtime. Algoritmo de fingerprint, hashes e scripts temporários no JSON.

## Ambiente e dados

Stack completo Compose isolado, API em `127.0.0.1:18030`, Qdrant e mocks internos. [Prontidão r3](v030-ready-r3.json) confirma 145 trechos, app 0.3.0, esquema 5 e prompts Router 4/Support 7. O override de teste e o script da revalidação HTTP têm hashes no manifesto. Credencial somente em ambiente; dados sintéticos; runtime anterior do responsável preservado.

## História e verificações

- História versão 1 e critérios preservados, com hashes no manifesto.
- [Developer r4](v030-developer-r4.md): 173 testes e validação estrita aprovados; oito regressões específicas e 13/13 cenários programados. São afirmações a verificar pela revisão independente.
- Nova rodada real aguarda parecer técnico apto. O orçamento persistente compartilha o teto adicional US$0,15 com a rodada anterior e a preparação do índice do Compose; não reinicializar o ledger.

## Pareceres e validade

Revisão r4 e QA pendentes. Reviewer e QA usam contexto independente do Developer e parâmetros explícitos `gpt-6-luna`/`high`. Relatórios anteriores preservados; parecer r3 de correções necessárias continua aplicável até a nova revisão comprovar a correção.

## Decisão e recuperação

Próximo: parecer técnico, revalidação real HTTP e QA. Nenhum commit, push, PR, merge, tag ou publicação autorizado nesta sessão. Recuperação por código v0.2.0 e esquema 0005 → 0004 em ambiente sintético isolado.
