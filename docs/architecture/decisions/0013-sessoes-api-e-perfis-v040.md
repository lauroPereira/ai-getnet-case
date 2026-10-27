# 0013. Sessões opacas e escopo da API da interface

## Status

Aceita pelo responsável em 2026-10-27 na aprovação completa do plano v0.4.0.
Implementação/validação registradas nas tarefas e evidências correspondentes.

## Contexto

A interface separada precisa acessar perfis e execuções, permitir demonstração
e reservar publicação de configurações ao administrador. Papel/lojista enviado
pela interface não pode determinar autoridade no backend.

## Decisão proposta

- Chaves de acesso demo/admin configuradas só no servidor, distintas de chaves
  de provedores, sem valores reais versionados ou senha de produção padrão.
- `POST /v1/sessions` valida a chave e emite token opaco aleatório; o backend
  persiste somente digest com principal, expiração de 60 minutos e revogação.
  Comparação de credencial em tempo constante; nunca registrar chave/token.
- Principal determina papel e escopo sintético; demo não escolhe outro lojista
  pelo corpo. Escrita de perfil/publicação exige admin em cada rota backend.
- Perfis publicados são imutáveis; execução congela versão e modelos efetivos.
  Comparação fica vinculada ao dono/estado/snapshot e é consumida uma vez.
- Não alterar o contrato legado para autenticação implícita. A exposição
  pública futura é só da interface; rotas legadas e infraestrutura ficam internas.

## Alternativas

JWT adicionaria assinatura/rotação sem eliminar a necessidade de revogação e
escopo persistidos nesta demonstração. Papel em cookie/interface sem validação
backend não atende RF-73. Token opaco mantém o contrato simples e revogável.

## Consequências e retorno

Novas tabelas de principal/sessão e testes de expiração, revogação e autorização.
Não é um provedor de identidade de produção. Custos/permissões/guardrails não
viram campos editáveis de perfil. Retorno pela v0.3.0 e descida 0006→0005 apenas
em banco sintético; não alterar credenciais existentes nem reiniciar ledger.

## Data

2026-10-27.
