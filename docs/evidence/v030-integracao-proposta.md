# Integração proposta — v0.3.0

## Candidato disponível para decisão

Branch `codex/v0.3.0-jornadas`, base `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
[Manifesto final](v030-candidato-r6-docs1.json), fingerprint
`5957a94d44675be57acad3310ece77c574e7edd4aed19d39116bd97068a1fd07`.
[Resultado, pareceres e limitações](v030-resultado.md).

## Operações que dependem de autorização

1. Conferir o candidato e a identidade local `lauroPereira <lauro.s.pereira@gmail.com>`.
2. Criar commit com código, dados sintéticos, testes, documentação SDD e evidências desta entrega.
3. Usar rede para conferir o remoto privado `lauroPereira/ai-getnet-case`, enviar a branch e abrir PR para `main`.
4. Conferir os checks e a base remota; se houver alteração material, revalidar antes de integrar. Integrar por merge local usando a identidade do projeto e enviar `main`.
5. Criar e enviar a tag `v0.3.0`, após confirmar que `main` contém o PR da entrega. Não substituir tag existente.
6. Atualizar `main` e criar a branch da próxima versão antes de preparar a v0.4.0, conforme SDD e permissões próprias de contratos/autenticação/migrações.

O repositório permanece privado. Esta proposta não autoriza publicação da
demonstração, novas chamadas pagas, alterações de credenciais ou conteúdo protegido.
Alternativa: manter o candidato local, ou enviar somente commit/PR para decisão
posterior de integração. Retorno por commit de reversão; migração 0005→0004
validada apenas em bancos sintéticos isolados. Não executar descida sobre dados
existentes do responsável por inferência.

## Texto proposto para o PR

**Title:** `Add merchant pricing, enablement and cancellation journeys (v0.3.0)`

Merchant fee questions now compare independent pricing and charge records in
integer cents, distinguish matching fees, different conditions, discrepancies
and missing evidence, and escalate discrepancies without promising refunds.
Read-only tools expose existing card enablement requests and sale cancellation
context through HTTP and MCP. Internal mock services and reversible migration
0005 provide synthetic data while preserving the POST /messages contract.

Validation: 191 tests and strict checks passed; independent technical review
and functional QA passed. Docker HTTP/MCP checks cover ownership isolation and
controlled dependency failures. Forty preserved real HTTP responses pass the
corrected deterministic rubric; four conversations were rerun with the real
model on the final runtime. These are separate measurements. Additional API
spend was US$0.14123583 under the authorized US$0.15 ceiling. See
`docs/evidence/v030-resultado.md` for candidate hashes, original reports,
replay provenance and QA limitations.

## Estado

O responsável respondeu **“Autorizar integração completa e tag v0.3.0”** em
2026-10-27. O ciclo completo acima está autorizado; execução e conferência em
[v030-integracao.md](v030-integracao.md). Esta proposta preserva o escopo aprovado.
