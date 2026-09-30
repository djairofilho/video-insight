package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.domain.ModelReference;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;

public record ProcessingCompleted(
        @NotNull UUID jobId,
        @NotNull UUID videoId,
        @NotNull @Min(1) Integer attempt,
        @NotNull @Valid Artifacts artifacts,
        @NotNull List<@Valid ModelReference> models) implements ProcessingEventData {

    public record Artifacts(
            @NotBlank String transcriptJsonKey,
            String transcriptTxtKey,
            String transcriptSrtKey,
            String summaryJsonKey,
            String chaptersJsonKey) {
    }
}
