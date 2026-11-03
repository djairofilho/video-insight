# Operação da infraestrutura

## Acesso e rede

O frontend principal está em <https://video-insight.alyvera.pro>. O domínio foi
vinculado ao projeto Vercel existente; o código de autenticação já usa a origem
atual do navegador. Callback, logout e origens web do Auth0 aceitam o domínio novo
e o endereço anterior da Vercel. O login com retorno à lista de vídeos foi validado.

A variável GitHub `FRONTEND_ORIGIN` define a origem principal. `FRONTEND_ORIGINS`
contém a lista explícita, separada por vírgulas, das origens HTTPS permitidas no
gateway e no MinIO. Ela inclui ambos os endereços durante a transição. O renderer
recusa curingas e origens inseguras. Nenhum nameserver foi alterado.

A administração disponível é SSH. A credencial AWS não permite alterar os
Security Groups. As portas públicas `443` e `3000` e as portas de coleta entre
máquinas estão bloqueadas pela rede, mesmo quando o serviço local responde.

O armazenamento usa `https://video-storage.alyvera.pro:8081`, com certificado
público e renovação automática pelo desafio HTTP em `80`. Caddy aceita somente
operações de objetos necessárias ao navegador, com limite de 100 MiB por envio.
O MinIO continua privado, sem acesso anônimo aos objetos. Os três serviços usam
túneis SSH para acessar MinIO em `9000`; a porta `8081` não serve mais HTTP S3.

Os nameservers e registros existentes, incluindo `agenda.alyvera.pro`, foram
preservados. Os subdomínios usam o projeto Vercel existente:

- Grafana: <https://grafana.alyvera.pro>.
- Operação: <https://grafana.alyvera.pro/d/video-insight>.
- Máquinas e alertas: <https://grafana.alyvera.pro/d/video-insight-infra>.
- Prometheus: <https://prometheus.alyvera.pro>.

Ambos usam o usuário `admin` e a senha administrativa existente do Grafana.
Grafana mantém seu login próprio e cookies Secure/HttpOnly. Prometheus exige
HTTP Basic Auth no proxy, com hash bcrypt guardado no secret GitHub
`PROMETHEUS_AUTH_HASH`, nunca em texto aberto no Git. Requisições sem credenciais
retornam `401`; rotas administrativas do Prometheus são bloqueadas.

A Vercel aplica rewrites por hostname para o proxy HTTPS do Core na porta `8081`.
O Core encaminha as requisições por conexões SSH mantidas pelo systemd até a VM
de monitoramento. Os encaminhamentos remotos aceitam somente loopback em
`13000` e `19090`, e a chave só pode abrir essas portas. A porta nativa do Grafana
continua em loopback; a do Prometheus continua privada.

As respostas do monitoramento usam `Cache-Control: private, no-store`. Os
painéis atualizam por consultas HTTP; Grafana Live está desativado neste caminho.
As portas AWS não precisaram ser abertas e não foi contratado serviço adicional.

O Core e o túnel são dependências do acesso público. O acesso SSH direto à VM de
monitoramento permanece como alternativa: porta local `13000` para a remota
`3000`, e local `19090` para a porta privada `9090`. Não exponha diretamente
Prometheus nem os exporters sem autenticação.

## Processamento e orçamento

O worker usa dois consumidores isolados, com prefetch individual e FFmpeg
limitado a uma thread por processo. Seu limite total de memória é 512 MiB.
Dois consumidores permitem sobrepor etapas, mas não duplicam a cota de IA.

O controle de consumo reserva cada tentativa antes da chamada externa. Usa
SQLite persistente no volume `video-insight-provider-budget`, com transações
compartilhadas pelos consumidores. Reservas de tentativas que falharam não são
devolvidas, para evitar subestimar o consumo. Falha no controle bloqueia a chamada.

| Provedor | Limite local de produção |
|---|---|
| Groq | 6.000 segundos de áudio/hora; 24.000/dia; 15 chamadas/minuto |
| Gemini | 6 chamadas/minuto; 100/dia; 120.000 tokens estimados/minuto |
| Gemini, saída | Até 4.096 tokens por resposta |

Os valores são limites desta aplicação, não o saldo oficial da conta. Outras
aplicações podem compartilhar a cota. O saldo exibido no Grafana corresponde às
reservas locais. Esgotamento por hora ou dia retorna erro que permite retentativa;
limites curtos podem aguardar até 65 segundos antes de falhar. Não há fallback pago.

Transcrição, resumo e capítulos têm checkpoints privados. Uma retentativa do
mesmo job reaproveita etapas válidas, sem repetir chamadas concluídas. O conteúdo
do vídeo e as opções participam da identificação do checkpoint. Mensagens
duplicadas do mesmo job são serializadas dentro do processo.

Essa proteção não coordena réplicas em máquinas diferentes. Antes de escalar
horizontalmente, implemente uma concessão distribuída de execução e compartilhe
o controle de consumo. Não apague o volume de orçamento para contornar limites.

## Upload e gateway

Novas URLs assinadas HTTPS são usadas diretamente pelo navegador, evitando o
trânsito do arquivo pela Vercel e pelo gateway. O caminho de compatibilidade
`/storage` continua funcional. Nginx valida o certificado e o hostname do storage;
a profundidade da cadeia é configurada conforme a documentação de
[TLS para upstreams do Nginx](https://docs.nginx.com/nginx/admin-guide/security-controls/securing-http-traffic-upstream/).

O gateway reutiliza conexões e exporta métricas privadas. Seus logs de acesso incluem
tempos de resposta e conexão, sem registrar IP do cliente nem query strings de
URLs assinadas. O frontend reduz o polling quando não há progresso, pausa a
consulta em abas ocultas e aplica espera progressiva a falhas transitórias.

## Painéis, alertas e retenção

Há dez alvos de coleta, 24 painéis de operação, 15 de infraestrutura e 14 regras.
As métricas cobrem fila, espera, conclusões na última hora, duração por etapa,
consumidores, provedores, reservas locais, CPU, memória, disco, contêineres,
reinícios e falta de memória. Os gráficos agregam por papel, sem IP nas legendas.

O painel de infraestrutura mostra alertas ativos calculados pelo Prometheus.
São regras do Prometheus, não regras gerenciadas pela tela Alerting do Grafana.
Nenhum canal externo de notificação foi configurado.

Alertas incluem serviço indisponível, disco abaixo de 20% ou de 1 GiB, pouca RAM,
CPU sustentada, memória do contêiner, OOM, reinícios, coleta atrasada, consumidor
desconectado, orçamento atingido, fila antiga e taxa de erros HTTP. Os períodos
de confirmação evitam alertar por uma oscilação breve. Os testes das regras
comprovam disparo e recuperação sem derrubar produção.

As máquinas são coletadas por chaves SSH sem shell, restritas às portas de
métricas e com host keys verificadas. Os encaminhamentos aceitam a rede local
do contêiner Prometheus. Falha de um túnel torna seu alvo indisponível e aciona
a regra correspondente.

Prometheus guarda até sete dias ou 512 MB. Prometheus e Grafana têm 256 MiB cada.
Os logs Docker usam o driver local, com rotação de 10 MB e três arquivos por
contêiner. O estado do Grafana, bancos, filas e objetos permanece em volumes.

## Validação e capacidade

Em 3 de novembro de 2026, a validação incluiu testes automatizados, coleta dos
dez alvos e envio de um objeto de 64 KiB. Foram conferidos CORS, integridade,
HEAD, resposta parcial `206`, recusa `403` sem assinatura e o proxy de
compatibilidade. Os objetos temporários foram removidos pelo endpoint interno.

Essa primeira validação de infraestrutura não fez chamadas de IA. Depois dela,
o [ensaio com vídeos reais](carga-videos-reais-2026-11-03.md) observou uma hora:
19 vídeos concluídos, 96,7 minutos de conteúdo, 17 conclusões na primeira
tentativa e duas recuperações após corrigir a admissão local por provedor.
As contas alternativas Free foram usadas somente no ensaio; as credenciais e
os tetos originais foram restaurados ao terminar. Os dois painéis adicionais
mostram espera por orçamento e os motivos de rejeição.
O resultado não estabelece capacidade máxima nem vazão contínua durante o dia.
O painel registra conclusões reais na última hora; o número de consumidores
não é uma estimativa de vídeos por hora. Não é possível prever uma data exata
de falha a partir de uma amostra de utilização.

Os deploys de aplicações preservam o contêiner anterior para rollback. As
configurações anteriores ficam em arquivos `.previous` protegidos na VM.
Antes de remover versões antigas, valide o funcionamento e mantenha um backup
restaurável dos dados. Não use `docker system prune --volumes`.
