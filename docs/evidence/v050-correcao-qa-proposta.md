# Proposta concreta: desbloquear confirmações da base na interface

**Estado: aprovada pelo responsável em 2026-10-27**, com a resposta
“Autorizar correção e revisão com gpt-6-luna/high”. A execução começa após
a passagem do QA sobre r3, sem mudar a fonte durante essa rodada.

## Evidência atual

QA independente gpt-6-luna/high, candidato r3, reproduziu na interface real:
marcar a confirmação deixa o checkbox selecionado, mas “Construir candidata”
continua desabilitado. Clique e o atalho indicado não submetem. O rascunho,
diff e estimativa funcionaram. CA-41 pela UI permanece reprovado.

Inspeção somente leitura do Supervisor localizou checkbox e submit dependente
do checkbox dentro do mesmo `st.form` em `app.py`: build393–402,
teste428–433, ativação444–448 e retorno463–465. Os últimos três ainda são
alcance potencial do mesmo padrão, não reprodução funcional declarada.

## Correção proposta

Developer vigente corrige somente os controles de confirmação e regressões
necessárias no projeto web. A confirmação deve atualizar o estado da tela e
habilitar a ação correspondente; sem confirmação não há requisição. Preservar
validação no backend, teto informado, exigência de teste aprovado, revisão
esperada e ação explícita. Rerun/troca de abas não repete build, teste ou troca
de versão. Não ampliar API, migração, autenticação ou permissões.

Revisão técnica focada no delta sobre r3, novo manifesto e retorno ao mesmo
QA para revalidar os quatro controles e a história pela interface. Evidência
de backend real desta rodada pode ser reutilizada quando não afetada; nenhuma
repetição paga sem necessidade. O cap permanece no MESMO arquivo/ID US$0,25,
incluindo tentativas anteriores, sem novo saldo.

## Delegação aprovada

O plano vigente registra Developer/Reviewer Sonnet5.5, indisponível nesta
sessão. O responsável autorizou gpt-6-luna/high inicialmente para QA e,
após a reprodução do defeito, também para a correção e revisão propostas:
reutilizar os dois subagentes Developer e Reviewer desta sessão, também
gpt-6-luna/high, em sequência, e depois o QA já ativo. Nenhum agente novo
adicional, commit, push, merge ou publicação.

RNF-12 do AGENTS.md exige autorização explícita de escopo, quantidade,
modelo e esforço; por isso a substituição desses dois papéis não é presumida.
Nenhuma correção de produto foi aplicada pelo Supervisor ou QA.

## Impacto, alternativa e retorno

Impacto limitado aos controles da interface. Alternativa: encerrar somente
o parecer QA como reprovado, preservando o candidato r3. Antes da correção,
preservar os bytes dos arquivos afetados; retorno restaura o código r3 sem
apagar versões, coleções, registros de teste ou controles financeiros.
Aceite exige a jornada no navegador e a conferência do novo candidato.
