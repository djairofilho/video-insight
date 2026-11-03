# Carga com vídeos reais: 3 de novembro de 2026

## Resultado e escopo

Na janela exata de **03h24min53s a 04h24min53s de Brasília**, foram entregues
**19 vídeos**, somando **96,6926 minutos de mídia**. Foram 17 conclusões na
primeira tentativa e duas recuperações, em 21 tentativas no total.
O piloto de 59 segundos está excluído desses denominadores.

Cada entrega foi validada pela presença de transcrição, resumo e capítulos.
Isso verifica geração e estrutura; não mede precisão linguística, qualidade
pedagógica, alucinação nem satisfação de usuários.

## Método

- Python/HTTPX executou cadastro, URL assinada, PUT direto por HTTPS,
  confirmação, criação de job e consulta do resultado. Não foi usado k6.
- Dois clientes em ciclo fechado; um novo envio dependia de uma vaga livre.
  Polling do gerador a cada cinco segundos, diferente do polling da interface.
- Três trechos reais de uma palestra em português: 59,025 s, 299,032 s e
  599,031 s; 400 × 224; aproximadamente 0,69, 3,98 e 7,51 MiB.
- Repetições criaram uploads e jobs distintos, sem cache global entre vídeos.
- Prometheus foi amostrado a cada 15 s: 240 amostras na janela, com maior
  intervalo de 15,72 s. Grafana consultou o mesmo datasource.
- Histórico PostgreSQL, eventos do cliente, contadores do worker e reservas
  SQLite foram reconciliados. Não houve jobs externos à amostra nessa janela.
- Contas alternativas Free foram usadas com faturamento Google desativado.
  Houve duas intervenções planejadas; não é uma configuração estável por 1 h.

| Fase | Novos uploads | Tentativas concluídas | Falhas |
| --- | ---: | ---: | ---: |
| Inicial | 9 | 8 | 1 |
| Calibrada | 8 | 7 | 1 |
| Recuperação | 0 | 2 | 0 |
| Validação final | 2 | 2 | 0 |

As duas tentativas de recuperação pertencem aos mesmos jobs que falharam.
Não devem ser somadas como dois vídeos novos.

## Latência, upload e denominadores

Tempos em segundos. p50 é a mediana, com média dos centrais para n par.
p90/p95/p99 usam o posto mais próximo `x[ceil(p × n)]`, sem interpolação.
Com n até 19, p95 e p99 são o máximo; não representam um SLA validado.

| População / operação | n | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| Primeira tentativa concluída, mistura de fases | 17 | 111,219 | 355,500 | 355,500 |
| Entrega final desde o primeiro envio | 19 | 122,173 | 1.984,190 | 1.984,190 |
| PUT do arquivo, mistura dos três tamanhos | 19 | 1,859 | 12,797 | 12,797 |
| Cadastro até job submetido | 19 | 2,703 | 13,578 | 13,578 |

A entrega final inclui pausas de diagnóstico, mudança de configuração e
recuperação. Os dois maiores tempos foram aproximadamente 33,07 min e
17,09 min; somente a retomada de cada job levou cerca de 3,12 min.
Polling e consulta/validação de resultado entram no tempo do cliente.

O maior tempo de fila nas tentativas concluídas foi 1,100 s. Uma tentativa
que falhou registrou 102,647 s de fila e 313,615 s de serviço. A falha aparece
separada dos sucessos; os registros disponíveis não isolam sua causa de fila.

Não houve erros HTTP/rede registrados pelo cliente. O gerador não persistiu
todas as consultas de polling nem tempos individuais por endpoint; por isso
não há RPS total ou p95 HTTP por rota reconstruídos retrospectivamente.

## Gargalo e correção

Capítulos consumiram **2.459,304 segundos acumulados dos workers**, ou 80,1%
do tempo das etapas, incluindo espera por orçamento e chamadas externas.
Na recuperação instrumentada, 333,771 s foram espera local, correspondentes
a 90,5% do tempo de capítulos daquela fase. Esse detalhamento não existia nas
duas primeiras fases e não foi imputado a elas.

As falhas foram `provider_budget_exhausted`. Na primeira ainda restavam
35 chamadas no teto diário local; a instrumentação antiga não distinguia
qual limite curto ou prazo de espera causou o bloqueio.

Elevar apenas os tetos também deixou uma falha. Um teste concorrente local
reproduziu uma chamada nova ultrapassando a que já aguardava. A correção
ordena a admissão por provedor dentro do processo, preservando as transações
SQLite e os limites. A proteção não é uma fila distribuída entre réplicas.

As duas recuperações reutilizaram dois checkpoints de transcrição e dois de
resumo, sem nova chamada ao Groq. Depois da correção, dois uploads novos
também concluíram: 13,437 s para o curto e 143,359 s para o de dez minutos.
Cada duração teve n=1 nessa validação; os tempos não são garantia de serviço.

## Consumo e retorno à configuração original

Na carga principal houve 19 chamadas Groq e 163 Gemini, sem erro externo.
Incluindo o piloto: 20 Groq e 168 Gemini, total de 188 reservas preservadas.
O saldo de 32 chamadas refere-se ao teto **local** calibrado de 200/dia,
não ao limite Free de 500/dia nem à conta original restaurada.

O limite Gemini foi de 6 RPM / 100 RPD / 120 mil tokens estimados por minuto
na fase inicial e 10 / 200 / 200 mil nas fases calibradas. A reserva conta
bytes UTF-8 do pedido e teto de saída; não equivale ao TPM de entrada do
provedor. O Groq reservou 5.880 s de áudio com o piloto, abaixo do teto local
de 6.000 s/h e do limite Free verificado de 7.200 s/h.

Ao terminar, credenciais e configuração originais foram restauradas,
mantendo a correção de admissão. O histórico foi separado por conta, sem
descartar reservas. As duas chaves temporárias foram revogadas.
Foram removidos 20 vídeos de teste e 184 objetos, incluindo o piloto;
o histórico de jobs e tentativas foi preservado.

## Infraestrutura e limites das conclusões

Não houve violação das proteções de recursos, OOM ou reinício inesperado
observado. As duas recriações planejadas do worker foram tratadas por
baselines separados. A auditoria final encontrou 39 painéis sem erro de
consulta e nenhuma fila pendente.

As máquinas tiveram folga no ensaio. Isso não estabelece capacidade máxima:
admissão limitada, três clipes, arquivos pequenos e intervenções impedem
generalizar para muitos usuários, arquivos maiores ou vários dias.
Não multiplique 19 vídeos/h por 24: a cota diária pode limitar antes.

O [teste k6 anterior](carga-k6-2026-11-02.md) mediu outra carga e outro caminho
de upload, antes das melhorias. Os dois ensaios não são um comparativo
controlado de desempenho antes/depois.

## Reprodução e mídia

O gerador e seus limites estão em [tests/load](../tests/load/README.md).
As evidências brutas e os reprodutores dos cálculos foram preservados fora
do Git, sem credenciais ou endereços de infraestrutura. Não há uma nova
execução de carga implícita ao rodar os testes unitários desse diretório.

Mídia: [Raphael Amorim: 500 days of open source](https://wordpress.tv/2016/06/21/raphael-amorim-palestra-500-days-of-open-source-com-raphael-amorim/),
produção emanweb / WordPress.tv, licença
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Trechos sem sobreposição foram recodificados em H.264/AAC, preservando a fala.
