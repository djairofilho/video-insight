package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.domain.Stage;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;

public record ProcessingProgressed(
        @NotNull UUID jobId,
        @NotNull UUID videoId,
        @NotNull @Min(1) Integer attempt,
        @NotNull Stage stage,
        @NotNull @Min(0) @Max(100) Integer progressPercent,
        String message) implements ProcessingEventData {
}
