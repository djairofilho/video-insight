# Contexto de produto: processamento de vídeos com IA

Documento de produto para orientar o escopo, a arquitetura e os critérios de
aceite do projeto de processamento de vídeos com IA.

> **Decisão:** projeto escolhido pelo grupo em 7 de setembro de 2026. Consulte
> o [ADR 001](decisoes/adr-001-processamento-videos-ia.md) para a justificativa,
> as consequências e as restrições aprovadas.

## Sumário

- [Visão do produto](#visão-do-produto)
- [Problema](#problema)
- [Público](#público)
- [Proposta de valor](#proposta-de-valor)
- [Hipóteses do produto](#hipóteses-do-produto)
- [Jornada principal](#jornada-principal)
- [Escopo do MVP](#escopo-do-mvp)
- [Requisitos funcionais](#requisitos-funcionais)
- [Regras de negócio](#regras-de-negócio)
- [Serviços e responsabilidades](#serviços-e-responsabilidades)
- [Fluxos do sistema](#fluxos-do-sistema)
- [Critérios de aceite](#critérios-de-aceite)
- [Métricas de produto](#métricas-de-produto)
- [Decisões em aberto](#decisões-em-aberto)

## Visão do produto

O produto transforma vídeos informativos em conteúdo pesquisável e
reutilizável. O usuário envia um vídeo e recebe transcrição com timestamps,
resumo e capítulos automáticos. Como evolução, a plataforma também pode
sugerir e gerar cortes curtos.

Nome provisório: **Video Insight**.

O produto não pretende ser uma plataforma de streaming ou um editor de vídeo
completo. Seu foco é reduzir o tempo gasto para entender, localizar e
reaproveitar informações presentes em vídeos.

## Problema

Aulas, entrevistas, reuniões e apresentações acumulam informações úteis, mas
são difíceis de consultar. Para encontrar um assunto específico, uma pessoa
precisa assistir ao vídeo inteiro ou navegar manualmente pela linha do tempo.

Transcrever, resumir, separar capítulos e localizar trechos relevantes também
consome tempo e exige ferramentas diferentes. O produto concentra esse fluxo
em um processamento assíncrono e apresenta os resultados em uma única tela.

## Público

### Persona principal

Estudantes, professores e pesquisadores que trabalham com aulas gravadas,
seminários ou entrevistas e precisam revisar o conteúdo com rapidez.

Necessidades principais:

- Localizar em que momento um assunto foi mencionado.
- Revisar os pontos mais importantes sem assistir novamente ao vídeo inteiro.
- Exportar uma transcrição para estudo ou documentação.

### Persona secundária

Produtores de conteúdo e equipes que gravam entrevistas, apresentações ou
reuniões e querem reutilizar o material.

Necessidades principais:

- Criar uma descrição ou um resumo inicial.
- Separar o vídeo em capítulos.
- Encontrar trechos que podem virar cortes curtos.

## Proposta de valor

Para pessoas que precisam extrair informação de vídeos longos, o Video Insight
processa o arquivo em segundo plano e entrega uma visão estruturada do
conteúdo. O usuário acompanha o andamento, consulta a transcrição por tempo e
exporta o resultado sem montar manualmente uma cadeia de ferramentas.

### Resultado esperado para o usuário

Ao final do fluxo, o usuário deve conseguir responder:

- Sobre o que é o vídeo?
- Quais são os principais tópicos?
- Em que momento cada assunto aparece?
- Como posso exportar ou reutilizar esse conteúdo?

## Hipóteses do produto

- Transcrição, resumo e capítulos resolvem o problema central do MVP.
- A visualização com timestamps tem mais valor do que entregar apenas um bloco
  de texto.
- O usuário aceita esperar alguns minutos se o progresso estiver visível.
- Limitar duração, tamanho e formato é aceitável na primeira versão.
- Cortes automáticos aumentam o impacto da demonstração, mas não são
  necessários para provar o valor principal.

## Jornada principal

1. O usuário entra na aplicação e faz login.
2. O usuário cadastra um vídeo e recebe uma URL assinada.
3. O navegador envia o arquivo diretamente ao armazenamento de objetos.
4. O usuário escolhe transcrição, resumo e capítulos.
5. O sistema cria um job e o coloca na fila.
6. O worker extrai o áudio, transcreve e executa as operações solicitadas.
7. A interface mostra o estado e o progresso do processamento.
8. O usuário acessa os resultados e navega pela transcrição com timestamps.
9. O usuário copia ou baixa a transcrição.

## Escopo do MVP

### Incluído

- Autenticação com OAuth2.
- Upload de arquivos MP4 por URL assinada.
- Vídeos de até 10 minutos e 100 MB.
- Processamento assíncrono.
- Transcrição em português com timestamps.
- Resumo do conteúdo.
- Capítulos com título, início e fim.
- Acompanhamento do estado e do progresso.
- Consulta dos resultados pelo proprietário do vídeo.
- Exportação da transcrição em TXT, JSON e SRT.
- Nova tentativa para processamentos que falharam.
- Métricas e logs do fluxo completo.

### Fora do MVP

- Streaming público ou transmissão ao vivo.
- Edição de vídeo com linha do tempo completa.
- Colaboração simultânea.
- Treinamento de modelos próprios.
- Tradução e dublagem.
- Processamento ilimitado de duração ou tamanho.
- Suporte a todos os codecs e formatos.
- Garantia de precisão para uso jurídico, médico ou acessibilidade oficial.
- Geração automática de vários cortes para redes sociais.

### Funcionalidade bônus

O sistema pode sugerir um trecho relevante e gerar um corte curto a partir do
vídeo original. Essa funcionalidade entra somente depois que o caminho
principal estiver estável.

## Requisitos funcionais

### Autenticação e autorização

- **RF01:** O sistema deve permitir autenticação por OAuth2.
- **RF02:** O sistema deve associar cada vídeo e job ao usuário autenticado.
- **RF03:** O usuário deve acessar apenas os próprios vídeos, jobs e artefatos.
- **RF04:** URLs de upload, reprodução e download devem ser temporárias.

### Gestão de vídeos

- **RF05:** O usuário deve cadastrar um vídeo antes de iniciar o upload.
- **RF06:** O sistema deve gerar uma URL assinada para upload direto.
- **RF07:** O sistema deve aceitar inicialmente arquivos MP4 dentro dos
  limites do MVP.
- **RF08:** O sistema deve registrar nome, tamanho, formato, duração e estado
  do upload.
- **RF09:** O usuário deve listar e consultar seus vídeos.
- **RF10:** O usuário deve excluir um vídeo e seus artefatos derivados.

### Processamento

- **RF11:** O usuário deve solicitar uma ou mais operações para um vídeo
  enviado com sucesso.
- **RF12:** O sistema deve criar um job assíncrono para a solicitação.
- **RF13:** O sistema deve publicar a tarefa na fila sem bloquear a requisição
  HTTP.
- **RF14:** O usuário deve consultar estado, etapa atual e percentual estimado.
- **RF15:** O sistema deve registrar tentativas e causas de falha.
- **RF16:** O usuário deve solicitar uma nova tentativa para um job com falha.
- **RF17:** O usuário deve cancelar um job que ainda não terminou.
- **RF18:** O sistema deve evitar processamentos duplicados causados por
  reentrega de mensagens ou repetição acidental da requisição.

### Resultados

- **RF19:** O sistema deve gerar uma transcrição com timestamps.
- **RF20:** O sistema deve gerar um resumo do conteúdo.
- **RF21:** O sistema deve gerar capítulos com título, instante inicial e
  instante final.
- **RF22:** O usuário deve consultar os resultados de um job concluído.
- **RF23:** O usuário deve navegar do trecho transcrito para o instante
  correspondente no vídeo.
- **RF24:** O usuário deve exportar a transcrição em TXT, JSON ou SRT.

### Funcionalidade bônus

- **RF25:** O sistema pode sugerir um trecho relevante com justificativa.
- **RF26:** O usuário pode solicitar a geração do corte sugerido.
- **RF27:** O usuário pode reproduzir e baixar o corte sem alterar o original.

## Regras de negócio

- **RN01:** Apenas o proprietário pode consultar, processar ou excluir um
  vídeo.
- **RN02:** Um job só pode ser criado depois que o upload for confirmado.
- **RN03:** Um job concluído ou cancelado não pode voltar para processamento.
- **RN04:** Uma nova tentativa cria uma tentativa rastreável e preserva o
  histórico da falha anterior.
- **RN05:** Operações idênticas para o mesmo vídeo devem usar uma chave de
  idempotência.
- **RN06:** A exclusão do vídeo deve remover ou agendar a remoção dos artefatos
  derivados.
- **RN07:** Arquivos temporários do worker devem ser removidos depois do
  processamento.
- **RN08:** O progresso representa etapas técnicas e não precisa indicar tempo
  restante exato.
- **RN09:** Uma falha em resumo ou capítulos não deve apagar uma transcrição já
  produzida.
- **RN10:** O sistema deve guardar qual modelo e versão geraram cada resultado.

## Serviços e responsabilidades

### Video Service

Gerencia o vídeo como recurso do sistema.

Responsabilidades:

- Metadados e propriedade.
- Validação de formato e limites.
- URLs assinadas de upload, reprodução e download.
- Confirmação do upload.
- Listagem, consulta e exclusão.

Não executa transcrição nem controla o andamento dos jobs.

### Job Service

Gerencia o trabalho assíncrono.

Responsabilidades:

- Criação e consulta de jobs.
- Estados, progresso, tentativas e erros.
- Publicação da solicitação na fila.
- Cancelamento e reprocessamento.
- Registro e consulta dos resultados estruturados.

Não manipula arquivos de mídia diretamente.

### Processing Service

Executa o pipeline de mídia e IA.

Responsabilidades:

- Consumo idempotente das mensagens.
- Download temporário do vídeo.
- Extração e normalização do áudio com FFmpeg.
- Transcrição com timestamps.
- Resumo e geração de capítulos.
- Armazenamento dos artefatos.
- Publicação de progresso, conclusão e falha.

Pode usar C++, Python, Rust ou outra linguagem adequada. A arquitetura não
exige que todos os serviços usem a mesma tecnologia.

### Fronteira resumida

```text
Video Service      gerencia o arquivo
Job Service        gerencia o trabalho
Processing Service executa o trabalho
```

## Fluxos do sistema

### Comunicação síncrona

REST é usado para:

- Cadastrar e consultar vídeos.
- Gerar URLs assinadas.
- Criar e consultar jobs.
- Consultar e exportar resultados.

### Comunicação assíncrona

RabbitMQ ou outro message broker é usado para:

```text
video.uploaded
processing.requested
processing.started
processing.progressed
processing.completed
processing.failed
```

O Processing Service nunca mantém uma requisição HTTP aberta durante o
processamento completo.

## Critérios de aceite

O MVP está funcional quando:

1. Um usuário autenticado envia um MP4 válido.
2. O upload não atravessa o backend da aplicação.
3. A solicitação retorna um `job_id` sem esperar o processamento.
4. O job passa por `queued`, `processing` e `completed`.
5. A tela mostra progresso e falhas de forma compreensível.
6. O resultado contém transcrição com timestamps, resumo e capítulos.
7. Um timestamp leva o usuário ao instante correspondente do vídeo.
8. A transcrição pode ser exportada em pelo menos TXT e SRT.
9. Outro usuário não consegue acessar o vídeo nem os resultados.
10. A reentrega da mesma mensagem não duplica o resultado.
11. Uma falha fica registrada e permite nova tentativa.
12. Logs e métricas permitem acompanhar o job entre os serviços.

## Métricas de produto

| Métrica | O que mostra |
|---|---|
| Taxa de uploads concluídos | Se o início da jornada funciona |
| Taxa de jobs concluídos | Confiabilidade do processamento |
| Tempo até o primeiro resultado | Tempo percebido pelo usuário |
| Duração total por minuto de vídeo | Eficiência do pipeline |
| Taxa de exportação | Utilidade prática da transcrição |
| Abertura de capítulos | Uso da navegação estruturada |
| Reprocessamentos por job | Instabilidade ou baixa qualidade |

Para o trabalho da disciplina, as métricas mais importantes são taxa de jobs
concluídos, duração do processamento e quantidade de falhas por etapa.

## Decisões em aberto

- Qual será o limite final de duração e tamanho?
- A transcrição será local, externa ou terá duas implementações?
- O resumo será gerado a partir do áudio ou da transcrição?
- O cancelamento interromperá o processo imediatamente ou apenas impedirá a
  próxima etapa?
- Os resultados parciais serão exibidos quando uma etapa posterior falhar?
- O corte automático entra como bônus ou fica para uma versão futura?
- Quanto tempo os vídeos e arquivos temporários ficarão armazenados?

## Arquiteturas relacionadas

- [Arquitetura cloud-agnostic](arquiteturas/videos-ia-agnostica.html)
- [Arquitetura AWS](arquiteturas/videos-ia-aws.html)
