package br.edu.insper.videoinsight.job.messaging;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;

public record ProcessingStarted(
        @NotNull UUID jobId,
        @NotNull UUID videoId,
        @NotNull @Min(1) Integer attempt,
        @NotBlank String workerId) implements ProcessingEventData {
}
