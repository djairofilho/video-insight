package br.edu.insper.videoinsight.video.api;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Limites do MVP: MP4 de até 100 MB (RF07). */
public record CreateVideoRequest(
        @NotBlank @Size(max = 255) String fileName,
        @NotNull @Pattern(regexp = "video/mp4", message = "deve ser video/mp4") String contentType,
        @NotNull @Min(1) @Max(104_857_600) Long sizeBytes) {
}
