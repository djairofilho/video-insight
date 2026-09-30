package br.edu.insper.videoinsight.job.domain;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/** Modelo e versão que geraram cada resultado (RN10). */
public record ModelReference(
        @NotNull Operation purpose,
        @NotBlank String provider,
        @NotBlank String model,
        @NotBlank String version) {
}
