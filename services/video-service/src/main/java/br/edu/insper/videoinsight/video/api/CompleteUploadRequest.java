package br.edu.insper.videoinsight.video.api;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** Vídeos de até 10 minutos (RF07). */
public record CompleteUploadRequest(@NotNull @Positive @DecimalMax("600") Double durationSeconds) {
}
