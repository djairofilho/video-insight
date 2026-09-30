package br.edu.insper.videoinsight.job.application;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.Job;
import br.edu.insper.videoinsight.job.domain.JobAttempt;
import br.edu.insper.videoinsight.job.domain.JobAttemptRepository;
import br.edu.insper.videoinsight.job.domain.JobRepository;
import br.edu.insper.videoinsight.job.domain.JobResult;
import br.edu.insper.videoinsight.job.domain.JobResultRepository;
import br.edu.insper.videoinsight.job.domain.JobStatus;
import br.edu.insper.videoinsight.job.domain.ModelReference;
import br.edu.insper.videoinsight.job.domain.Operation;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import br.edu.insper.videoinsight.job.messaging.OutboxWriter;
import br.edu.insper.videoinsight.job.storage.ArtifactStorage;
import br.edu.insper.videoinsight.job.storage.PresignedUrl;
import br.edu.insper.videoinsight.job.video.VideoClient;
import java.time.Clock;
import java.util.HashSet;
import java.util.List;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

@Service
public class JobService {
    private static final int MIN_IDEMPOTENCY_KEY_LENGTH = 16;
    private static final int MAX_IDEMPOTENCY_KEY_LENGTH = 128;
    private static final TypeReference<List<TranscriptSegment>> SEGMENTS = new TypeReference<>() {
    };
    private static final TypeReference<List<Chapter>> CHAPTERS = new TypeReference<>() {
    };
    private static final TypeReference<List<ModelReference>> MODELS = new TypeReference<>() {
    };

    private final JobRepository jobs;
    private final JobAttemptRepository attempts;
    private final JobResultRepository results;
    private final OutboxWriter outbox;
    private final VideoClient videoClient;
    private final ArtifactStorage storage;
    private final TransactionTemplate transaction;
    private final JsonMapper mapper;
    private final Clock clock;
    private final String storageKeyTemplate;

    public JobService(
            JobRepository jobs,
            JobAttemptRepository attempts,
            JobResultRepository results,
            OutboxWriter outbox,
            VideoClient videoClient,
            ArtifactStorage storage,
            TransactionTemplate transaction,
            JsonMapper mapper,
            Clock clock,
            JobServiceProperties properties) {
        this.jobs = jobs;
        this.attempts = attempts;
        this.results = results;
        this.outbox = outbox;
        this.videoClient = videoClient;
        this.storage = storage;
        this.transaction = transaction;
        this.mapper = mapper;
        this.clock = clock;
        this.storageKeyTemplate = properties.videoService().storageKeyTemplate();
    }

    /**
     * Cria o job e grava {@code processing.requested} no outbox. Repetir a mesma chave de idempotência com o mesmo
     * pedido devolve o job existente (RF18/RN05).
     */
    public Job createJob(UUID videoId, String idempotencyKey, List<Operation> operations) {
        validateIdempotencyKey(idempotencyKey);
        var normalizedOperations = normalize(operations);

        var existing = jobs.findByIdempotencyKey(idempotencyKey);
        if (existing.isPresent()) {
            return sameRequestOrConflict(existing.get(), videoId, normalizedOperations);
        }

        // A consulta ao Video Service fica fora da transação para não segurar conexões do banco.
        var video = videoClient.findVideo(videoId)
                .orElseThrow(() -> ApiException.notFound("VIDEO_NOT_FOUND", "Vídeo não encontrado."));
        if (!video.isReady()) {
            throw ApiException.conflict("VIDEO_NOT_READY", "O upload do vídeo ainda não foi confirmado.");
        }

        try {
            return transaction.execute(status -> {
                var created = Job.create(
                        videoId, normalizedOperations, idempotencyKey, storageKey(videoId), clock.instant());
                jobs.saveAndFlush(created);
                attempts.save(JobAttempt.queued(created.getId(), created.getAttempt(), clock.instant()));
                outbox.enqueueProcessingRequested(created);
                return created;
            });
        } catch (DataIntegrityViolationException exception) {
            // Duas requisições simultâneas com a mesma chave: a segunda devolve o job da primeira.
            var concurrent = jobs.findByIdempotencyKey(idempotencyKey).orElseThrow(() -> exception);
            return sameRequestOrConflict(concurrent, videoId, normalizedOperations);
        }
    }

    @Transactional(readOnly = true)
    public Job getJob(UUID jobId) {
        return findJob(jobId);
    }

    @Transactional
    public Job cancelJob(UUID jobId) {
        var job = findJob(jobId);
        job.cancel(clock.instant());
        attempts.findByJobIdAndAttempt(job.getId(), job.getAttempt())
                .ifPresent(attempt -> attempt.cancelled(clock.instant()));
        return job;
    }

    @Transactional
    public Job retryJob(UUID jobId) {
        var job = findJob(jobId);
        job.retry(clock.instant());
        attempts.save(JobAttempt.queued(job.getId(), job.getAttempt(), clock.instant()));
        outbox.enqueueProcessingRequested(job);
        return job;
    }

    @Transactional(readOnly = true)
    public JobResultView getResult(UUID jobId) {
        var job = findJob(jobId);
        var result = completedResult(job);
        var chapters = result.getChapters() == null ? null : readList(result.getChapters(), CHAPTERS);
        return new JobResultView(
                job.getId(),
                job.getVideoId(),
                readList(result.getTranscript(), SEGMENTS),
                result.getSummary(),
                chapters,
                readList(result.getModels(), MODELS),
                result.getCompletedAt());
    }

    @Transactional(readOnly = true)
    public PresignedUrl exportTranscript(UUID jobId, String format) {
        var transcriptFormat = TranscriptFormat.from(format)
                .orElseThrow(() -> ApiException.badRequest("Formato inválido; use txt, json ou srt."));
        var result = completedResult(findJob(jobId));
        var key = transcriptFormat.artifactKey(result)
                .orElseThrow(() -> ApiException.conflict("ARTIFACT_NOT_AVAILABLE",
                        "A transcrição não está disponível no formato " + transcriptFormat.extension() + "."));
        return storage.presignDownload(key, "transcricao-" + jobId + "." + transcriptFormat.extension());
    }

    private JobResult completedResult(Job job) {
        if (job.getStatus() != JobStatus.COMPLETED) {
            throw ApiException.conflict("JOB_NOT_COMPLETED", "O job ainda não foi concluído.");
        }
        return results.findById(job.getId())
                .orElseThrow(() -> ApiException.conflict("JOB_NOT_COMPLETED", "O resultado ainda não está disponível."));
    }

    private Job findJob(UUID jobId) {
        return jobs.findById(jobId)
                .orElseThrow(() -> ApiException.notFound("JOB_NOT_FOUND", "Job não encontrado."));
    }

    private static Job sameRequestOrConflict(Job job, UUID videoId, List<Operation> operations) {
        if (!job.hasSameRequest(videoId, operations)) {
            throw ApiException.conflict("IDEMPOTENCY_KEY_REUSED",
                    "A chave de idempotência já foi usada em outra solicitação.");
        }
        return job;
    }

    private static void validateIdempotencyKey(String idempotencyKey) {
        var length = idempotencyKey == null ? 0 : idempotencyKey.length();
        if (length < MIN_IDEMPOTENCY_KEY_LENGTH || length > MAX_IDEMPOTENCY_KEY_LENGTH) {
            throw ApiException.badRequest("O header Idempotency-Key deve ter entre 16 e 128 caracteres.");
        }
    }

    private static List<Operation> normalize(List<Operation> operations) {
        if (new HashSet<>(operations).size() != operations.size()) {
            throw ApiException.badRequest("As operações não podem se repetir.");
        }
        return operations.stream().sorted().toList();
    }

    private String storageKey(UUID videoId) {
        return storageKeyTemplate.replace("{videoId}", videoId.toString());
    }

    private <T> List<T> readList(String json, TypeReference<List<T>> type) {
        return mapper.readValue(json, type);
    }
}
