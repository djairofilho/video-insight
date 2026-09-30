package br.edu.insper.videoinsight.job.api;

import br.edu.insper.videoinsight.job.domain.Job;
import br.edu.insper.videoinsight.job.domain.JobStatus;
import br.edu.insper.videoinsight.job.domain.Operation;
import br.edu.insper.videoinsight.job.domain.Stage;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Corresponde ao schema {@code Job} do contrato. */
public record JobResponse(
        UUID id,
        UUID videoId,
        List<Operation> operations,
        JobStatus status,
        Stage stage,
        int progressPercent,
        int attempt,
        JobError error,
        Instant createdAt,
        Instant updatedAt) {

    public record JobError(String code, String message, boolean retryable) {
    }

    public static JobResponse from(Job job) {
        var error = job.getErrorCode() == null
                ? null
                : new JobError(job.getErrorCode(), job.getErrorMessage(), Boolean.TRUE.equals(job.getErrorRetryable()));
        return new JobResponse(
                job.getId(),
                job.getVideoId(),
                job.getOperations(),
                job.getStatus(),
                job.getStage(),
                job.getProgressPercent(),
                job.getAttempt(),
                error,
                job.getCreatedAt(),
                job.getUpdatedAt());
    }
}
