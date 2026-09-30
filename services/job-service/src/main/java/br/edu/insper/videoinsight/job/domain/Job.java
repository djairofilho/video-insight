package br.edu.insper.videoinsight.job.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "jobs")
public class Job {
    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID videoId;

    @Convert(converter = OperationsConverter.class)
    @Column(nullable = false)
    private List<Operation> operations;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private JobStatus status;

    @Enumerated(EnumType.STRING)
    private Stage stage;

    private int progressPercent;

    private int attempt;

    private String errorCode;

    private String errorMessage;

    private Boolean errorRetryable;

    @Column(nullable = false)
    private String idempotencyKey;

    @Column(nullable = false)
    private String storageKey;

    @Column(nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @Version
    private long version;

    protected Job() {
    }

    public static Job create(
            UUID videoId, List<Operation> operations, String idempotencyKey, String storageKey, Instant now) {
        var job = new Job();
        job.id = UUID.randomUUID();
        job.videoId = videoId;
        job.operations = List.copyOf(operations);
        job.idempotencyKey = idempotencyKey;
        job.storageKey = storageKey;
        job.status = JobStatus.QUEUED;
        job.progressPercent = 0;
        job.attempt = 1;
        job.createdAt = now;
        job.updatedAt = now;
        return job;
    }

    /** Eventos de tentativas antigas ou de jobs finalizados são ignorados (RN03). */
    public boolean acceptsEventsFor(int eventAttempt) {
        return !status.isTerminal() && attempt == eventAttempt;
    }

    public void start(Instant now) {
        status = JobStatus.PROCESSING;
        updatedAt = now;
    }

    public void progress(Stage newStage, int percent, Instant now) {
        status = JobStatus.PROCESSING;
        stage = newStage;
        progressPercent = Math.max(progressPercent, Math.min(percent, 100));
        updatedAt = now;
    }

    public void complete(Instant now) {
        status = JobStatus.COMPLETED;
        stage = null;
        progressPercent = 100;
        updatedAt = now;
    }

    public void fail(Stage failedStage, String code, String message, boolean retryable, Instant now) {
        status = JobStatus.FAILED;
        stage = failedStage;
        errorCode = code;
        errorMessage = message;
        errorRetryable = retryable;
        updatedAt = now;
    }

    public void cancel(Instant now) {
        if (status.isTerminal()) {
            throw new InvalidJobStateException("Somente jobs não finalizados podem ser cancelados.");
        }
        status = JobStatus.CANCELLED;
        updatedAt = now;
    }

    /** Inicia uma nova tentativa; a falha anterior permanece em {@link JobAttempt} (RN04). */
    public void retry(Instant now) {
        if (status != JobStatus.FAILED) {
            throw new InvalidJobStateException("Somente jobs com falha podem ser reprocessados.");
        }
        attempt++;
        status = JobStatus.QUEUED;
        stage = null;
        progressPercent = 0;
        errorCode = null;
        errorMessage = null;
        errorRetryable = null;
        updatedAt = now;
    }

    public boolean hasSameRequest(UUID otherVideoId, List<Operation> otherOperations) {
        return videoId.equals(otherVideoId) && operations.equals(otherOperations);
    }

    public UUID getId() {
        return id;
    }

    public UUID getVideoId() {
        return videoId;
    }

    public List<Operation> getOperations() {
        return operations;
    }

    public JobStatus getStatus() {
        return status;
    }

    public Stage getStage() {
        return stage;
    }

    public int getProgressPercent() {
        return progressPercent;
    }

    public int getAttempt() {
        return attempt;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public Boolean getErrorRetryable() {
        return errorRetryable;
    }

    public String getStorageKey() {
        return storageKey;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
