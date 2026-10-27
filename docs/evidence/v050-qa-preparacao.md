# Preparação da rodada real de QA v0.5

Roteiro operacional proposto pelo Supervisor, sem execução ou parecer QA.
Não altera a história v1 nem os critérios do plano aprovado. A rodada só
começa depois de Reviewer apto, fonte/ambiente fixados e conferência do QA.

## Autorização e controle

QA real autorizado pelo responsável; cap adicional US$0,25 sob teto global
US$5, incluindo todas as tentativas/embeddings/avaliações da rodada. O acumulado
anterior registrado é US$0,59283583; o ledger nativo tem leitura de referência
de850 entradas/US$0,34298961. São registros de escopos diferentes, não somar
o ledger novamente ao acumulado. Reconciliar o estado vivo antes do primeiro envio.

Usar a guarda existente com cap fixado uma vez e controle persistente entre
reinícios/candidatos; não criar saldo novo em cada retry nem alterar `.env`.
Preservar o limite configurado e o ledger, sem apagar/zerar/copiar histórico.
Custo desconhecido e falta de saldo impedem envio; uso desconhecido conserva
a reserva. Não comprar créditos nem trocar credencial. A autorização já dada
dispensa nova pergunta dentro desse escopo, mas não permite ultrapassar o cap.
Retries internos do SDK também são tentativas: desabilitar retry opaco ou
reservar cada tentativa. Erro não renova cap e não apaga gasto anterior.
Se a implementação usar ledger primário e ledger de campanha em conjunto,
eles controlam a mesma chamada: não somar os dois como duas despesas. Registrar
baseline/delta do primário e gasto da campanha, explicando a reconciliação com
o acumulado histórico. Os dois limites devem ser respeitados simultaneamente.

## Ordem econômica de execução

1. Conferir candidato, dados sintéticos, fontes públicas, preços/capacidades
   oficiais atuais e efetividade da guarda. Presença de chave não prova acesso.
2. Fazer primeiro smoke real pequeno dos provedores/métodos necessários,
   capturando IDs reportados, modo real, custo/uso e falhas. Se um contrato
   real falhar, registrar e interromper a expansão, antes da regressão em lote.
3. Percorrer a história KB por UI/HTTP: edição fictícia verificável, diff,
   estimativa/confirmar, build/teste, ativação, versão no run e retorno.
   Fonte oficial/demo/revisão/custo negados devem manter a ativa.
4. Executar regressão real pertinente do núcleo/jornadas, reutilizando os
   cenários sintéticos existentes. Separar custos do atendimento e julgamento.
   Não implementar o Evaluation Agent de produto v0.6 por inferência.
5. Se surgir defeito, devolver ao mesmo Developer e revalidar o escopo afetado
   depois da revisão/candidato novo. Não repetir lotes já válidos sem mudança
   ou dúvida que o justifique; replay deve ser rotulado como histórico.
6. Fechar ledger agregado/custo da rodada, fonte/ambiente, resultados/limites
   e ausência de automação paga em rerun. Não declarar CA real por mock.

## Evidência de edição

Pode usar frase/marcador inequívoco apenas no documento operacional fictício,
consultando antes/depois em conversas independentes, com fonte/hash/versão no
snapshot. Não alterar preço, regras de cobrança, autoridade ou fonte oficial.
O QA escolhe o exemplo realista; este roteiro não fixa resposta do modelo.

## Separação de atores

Developer/Reviewer validam com transportes falsos. Supervisor prepara manifesto
e montagem sintética, sem iniciar inferência real. O novo QA autorizado é o
executor dos caminhos pagos, mantendo os mesmos limites em todas as tentativas.
