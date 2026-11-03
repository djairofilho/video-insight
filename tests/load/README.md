# Testes de carga

Resultados medidos: [carga com k6 de 2 de novembro de 2026](../../docs/carga-k6-2026-11-02.md).

## Vídeos reais com IA

`real_video_load.py` executa cadastro, upload direto por HTTPS, confirmação,
transcrição, resumo e capítulos. Cada repetição cria um vídeo e um job novos.
O cliente registra eventos JSONL, valida os três resultados preenchidos e
interrompe novas admissões na primeira falha. Não repete jobs automaticamente.

Antes de executar, confirme as contas Free, faturamento, saldo e limites dos
provedores. O orçamento persistente do worker e um coletor externo de CPU,
memória, disco, OOM e reinicializações devem estar ativos. O cliente não
confirma faturamento nem configura essas proteções no servidor.

Prepare uma pasta de mídia fora do Git, com `manifest.json` contendo `cases`.
Cada caso precisa de `filename`, `duration_seconds`, `size_bytes` e `sha256`.
O arquivo deve corresponder ao hash revisado, ter até 100 MiB e dez minutos.
Registre fonte, licença e recortes; não substitua fala real por áudio sintético
para afirmar capacidade de processamento de vídeos reais.

```powershell
# Alvo e bearer devem estar no ambiente; nunca na linha de comando.
python tests/load/real_video_load.py --base-url $env:E2E_BASE_URL `
  --media-dir CAMINHO_DA_MIDIA --output CAMINHO_DA_EVIDENCIA.jsonl `
  --stop-file CAMINHO_DA_PARADA_PREVENTIVA
```

O padrão observa 3.600 segundos com dois clientes em ciclo fechado e limita a
admissão a 18 jobs ou 5.400 segundos de mídia. Para de admitir nos últimos cinco
minutos e permite mais dez minutos de drenagem. Esses limites são do ensaio,
não uma declaração de capacidade. O coletor deve criar `--stop-file` se perder
telemetria ou atingir um limite de recursos; um arquivo já existente impede o
primeiro upload. O bearer pertence somente à API, não ao storage.

Separe piloto, mudanças de configuração e recuperação. Reconcilie IDs distintos,
tentativas, histórico do banco e métricas com baselines próprios para cada
processo. Uma nova tentativa do mesmo job não representa um vídeo adicional.
Não extrapole uma rajada para vídeos por hora nem multiplique a vazão de uma
hora por 24 sem considerar as cotas diárias. Apague somente os vídeos e
artefatos identificados como pertencentes ao ensaio, após guardar as evidências.

```powershell
python -m pytest tests/load/test_real_video_load.py -q --no-cov
```

## k6: consultas e uploads

Os cenários k6 recebem o alvo e o token pelo ambiente. Não colocar tokens,
endereços de infraestrutura, URLs assinadas ou arquivos de mídia no Git.
Executar o gerador fora das VMs que estão sendo medidas.

- `api.k6.js`: consultas autenticadas com taxa de chegada constante. No modo
  `mixed`, distribui consultas entre listagem de vídeos (40%), detalhes de vídeo
  (20%), listagem de jobs (20%) e detalhes de job (20%). O modo `list` mede somente
  a listagem. Todas as respostas devem ser HTTP 200 e JSON.
- `upload.k6.js`: cadastro, assinatura, PUT do conteúdo, confirmação e exclusão do
  vídeo de teste. O bearer é enviado somente à API; o storage recebe apenas os
  headers da assinatura. A mídia deve ser um MP4 sintético com dois segundos.
- `k6-config.mjs`: valida limites, oculta URLs das métricas e gera resumo JSON sem
  copiar variáveis de ambiente.
- `k6-config.test.mjs`: valida limites, resumo e preservação da assinatura.

Instalar o k6 a partir da [distribuição oficial](https://grafana.com/docs/k6/latest/set-up/install-k6/).
Definir `E2E_BASE_URL` e `E2E_ACCESS_TOKEN` no ambiente, usando um access token
Auth0 válido para a API. Não obter um token novo por requisição de carga.

Para o modo misto, definir `E2E_LOAD_FIXTURE` como um JSON com `video_id` e
`job_id` pertencentes ao usuário do token. Usar exclusivamente recursos de teste.

```powershell
$env:TARGET_LABEL = 'public-mixed'
$env:MODE = 'mixed'
$env:RATE = '5'
$env:DURATION_SECONDS = '30'
k6 run --quiet --log-output=none --no-usage-report tests/load/api.k6.js
```

Executar etapas separadas, por exemplo 1, 5, 10, 25, 50, 100, 200, 400, 800 e
1.000 requisições por segundo. O script limita a taxa a 1.000, a duração de uma
etapa a dez minutos e os VUs a 1.000, com padrão de 500. Esses são limites do experimento, não uma
declaração de capacidade da aplicação. Parar de aumentar a carga na primeira
falha dos critérios e medir a recuperação com uma taxa baixa.
Todos os VUs configurados são pré-alocados para evitar descartes durante a
alocação dinâmica do gerador.

Os critérios iniciais são menos de 1% de erros, p95 abaixo de dois segundos e
nenhuma iteração descartada. Há interrupção automática acima de 5% de erros ou
p99 de oito segundos, após quinze segundos de avaliação, e ao exceder 128 MiB
recebidos por etapa. As métricas são agregadas por execução, não janelas móveis.
Os limites de erro e latência são critérios experimentais; não são um SLA.

O resumo inclui latências, erros, vazão, contadores por classe de status,
`dropped_iterations` e duração real. Uma taxa solicitada não equivale à vazão
atingida. Iterações descartadas podem indicar falta de VUs no gerador ou
lentidão do sistema: verificar ambos antes de atribuir o gargalo ao backend.

Para uploads:

```powershell
$env:LOAD_RUN_ID = 'loadtest-identificador-unico'
$env:VIDEO_FILE = 'CAMINHO_DO_MP4_SINTETICO'
$env:UPLOAD_VUS = '2'
$env:UPLOAD_ITERATIONS = '2'
k6 run --quiet --log-output=none --no-usage-report tests/load/upload.k6.js
```

O cenário limita uploads a 100 MiB, 16 VUs e 32 iterações. Escolher o total de
bytes antes de iniciar: muitos arquivos grandes podem esgotar o storage ou
consumir franquias. Após uma interrupção abrupta, listar os vídeos do usuário e
remover somente aqueles com o prefixo exato de `LOAD_RUN_ID`; o `finally` da
iteração pode não executar após encerrar o processo.

Durante o teste, acompanhar CPU, memória disponível e disco dos hosts, memória
e eventos OOM dos contêineres, reinícios, filas e recursos do gerador. Interromper
se faltar monitoramento, houver OOM/reinício, disco livre abaixo de 1 GiB,
memória disponível abaixo de 200 MiB ou contêiner acima de 90% do limite de
memória. Essa proteção externa depende do executor que coordena os cenários;
rodar o comando k6 isoladamente não verifica as máquinas.

Os scripts não criam jobs de processamento. Para exercitar a fila sem consumo
de IA, usar separadamente um vídeo sintético sem áudio: o resultado esperado é
`failed` com `no_audio_track`, antes de chamar o provedor. Isso não mede a vazão
de transcrição, resumo ou geração de capítulos. Carga real de IA exige verificar
plano, saldo, quotas e limite de gasto dos provedores.

Validação local das configurações:

```bash
node --test tests/load/k6-config.test.mjs
```

## Script Python original

`run_load.py` mede consultas autenticadas sem criar jobs ou consumir cota de IA.
Use um access token de teste na variável `E2E_ACCESS_TOKEN`, nunca em argumentos.

```bash
python -m pip install -r tests/end-to-end/requirements.txt
python tests/load/run_load.py https://video-insight-ruby.vercel.app/api/v1/videos --requests 50 --workers 5
```

O relatório JSON inclui códigos HTTP, erros, p50, p95, máximo e requisições por
segundo. Respostas 401/403 contam como falhas, não como sucesso de carga.
Os limites são 1.000 requisições e 20 clientes; aumentos exigem outro experimento.
Este teste não mede a capacidade máxima de processamento dos provedores de IA.
