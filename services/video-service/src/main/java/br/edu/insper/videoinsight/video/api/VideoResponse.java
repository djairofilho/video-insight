package br.edu.insper.videoinsight.video.api;

import br.edu.insper.videoinsight.video.domain.UploadStatus;
import br.edu.insper.videoinsight.video.domain.Video;
import java.time.Instant;
import java.util.UUID;

/** Corresponde ao schema {@code Video} do contrato. */
public record VideoResponse(
        UUID id,
        String fileName,
        String contentType,
        long sizeBytes,
        Double durationSeconds,
        UploadStatus uploadStatus,
        Instant createdAt,
        Instant updatedAt) {

    public static VideoResponse from(Video video) {
        return new VideoResponse(
                video.getId(),
                video.getFileName(),
                video.getContentType(),
                video.getSizeBytes(),
                video.getDurationSeconds(),
                video.getUploadStatus(),
                video.getCreatedAt(),
                video.getUpdatedAt());
    }
}
