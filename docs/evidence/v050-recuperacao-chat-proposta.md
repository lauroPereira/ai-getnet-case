# Proposta: recuperar atendimento após falha de transporte

**Aprovada pelo responsável em 2026-10-27**, com a resposta
“Aprovar recuperação manual da conversa”. Mesmos agentes e campanha.

## Problema comprovado e limite do diagnóstico

QA r1 viu ReadTimeout na interface e encontrou a resposta concluída no
backend. A tarefa48 registra os dados. O trace mede11,551segundos de grafo,
não o tempo HTTP total; a causa temporal não está comprovada. Não se propõe
aumentar o timeout ou repetir POST automaticamente.

Diagnóstico do Developer: o cliente já tem GET da conversa, mas a interface
não o usa. O ID da primeira conversa só é salvo após o POST responder; se
esse POST termina em timeout, a tela perde o caminho de consulta. A correção
de confirmações aprovada não alterou esse comportamento.

## Mudança concreta proposta

Somente web `app.py`, cliente HTTP se necessário e testes:

1. Fixar ID sintético da conversa no estado da UI antes do primeiro envio,
   usando o campo já aceito pela API. Preservar a identificação durante falha.
2. Tratar falha de transporte com mensagem útil e estado pendente, sem
   traceback na tela e sem reenviar automaticamente uma mensagem paga.
3. Oferecer ação manual somente GET para atualizar a conversa existente e
   apresentar a resposta persistida. Distinguir resposta nova de histórico
   anterior; ausência de resposta não deve mostrar uma resposta antiga como
   conclusão da pergunta pendente. Repetir GET não gera nova inferência.
4. Medir tempo HTTP do cliente com dados sanitizados para diagnóstico futuro,
   se necessário. Não registrar token, texto privado ou credencial.
5. Regressão com transporte controlado: POST único, falha, GET de recuperação,
   resposta correta e nenhum POST adicional em atualização/navegação. Depois,
   revisão focada e QA no mesmo runtime/campanha, reutilizando o que já passou.

Não muda API pública, autenticação, permissões, banco, migração, modelo,
guarda, teto ou timeout. A validação real adicional permanece dentro da MESMA
campanha US$0,25; acumulado atual US$0,00282289 não é renovado.

## Delegação, alternativa e retorno

Reutilizar os MESMOS Developer → Reviewer → QA, gpt-6-luna/high, sem agente
adicional. A autorização mais recente e a proposta anterior limitaram a
implementação aos controles de confirmação; este é o escopo adicional da
tarefa48 a ser decidido pelo responsável conforme RNF-12.

Alternativa: concluir a correção dos botões e manter tarefa48 aberta com a
limitação de recuperação, sem declarar a jornada inteira apta. Antes de editar,
preservar bytes dos arquivos; retorno ao candidato de confirmações não exige
apagar conversas, versões, coleções ou ledgers.
