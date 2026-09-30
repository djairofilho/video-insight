package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.domain.Stage;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;

public record ProcessingFailed(
        @NotNull UUID jobId,
        @NotNull UUID videoId,
        @NotNull @Min(1) Integer attempt,
        @NotNull Stage stage,
        @NotBlank String errorCode,
        @NotBlank String errorMessage,
        @NotNull Boolean retryable) implements ProcessingEventData {
}
