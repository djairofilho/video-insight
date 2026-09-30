package br.edu.insper.videoinsight.job.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "job_attempts")
public class JobAttempt {
    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID jobId;

    private int attempt;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private JobStatus status;

    @Enumerated(EnumType.STRING)
    private Stage stage;

    private String errorCode;

    private String errorMessage;

    private Boolean errorRetryable;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant startedAt;

    private Instant finishedAt;

    protected JobAttempt() {
    }

    public static JobAttempt queued(UUID jobId, int attempt, Instant now) {
        var jobAttempt = new JobAttempt();
        jobAttempt.id = UUID.randomUUID();
        jobAttempt.jobId = jobId;
        jobAttempt.attempt = attempt;
        jobAttempt.status = JobStatus.QUEUED;
        jobAttempt.createdAt = now;
        return jobAttempt;
    }

    public void started(Instant now) {
        status = JobStatus.PROCESSING;
        startedAt = now;
    }

    public void completed(Instant now) {
        status = JobStatus.COMPLETED;
        finishedAt = now;
    }

    public void failed(Stage failedStage, String code, String message, boolean retryable, Instant now) {
        status = JobStatus.FAILED;
        stage = failedStage;
        errorCode = code;
        errorMessage = message;
        errorRetryable = retryable;
        finishedAt = now;
    }

    public void cancelled(Instant now) {
        status = JobStatus.CANCELLED;
        finishedAt = now;
    }

    public int getAttempt() {
        return attempt;
    }

    public JobStatus getStatus() {
        return status;
    }

    public Stage getStage() {
        return stage;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getFinishedAt() {
        return finishedAt;
    }
}
