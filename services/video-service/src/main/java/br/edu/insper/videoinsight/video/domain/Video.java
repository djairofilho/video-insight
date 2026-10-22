package br.edu.insper.videoinsight.video.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

/**
 * Vídeo cadastrado pelo usuário. O arquivo fica no bucket de vídeos, na chave {@code {id}/original.mp4} combinada com
 * o Job Service e o Processing Service ({@code contracts/README.md}).
 */
@Entity
@Table(name = "videos")
public class Video {
    @Id
    private UUID id;

    private String ownerId = "local-development";

    @Column(nullable = false)
    private String fileName;

    @Column(nullable = false)
    private String contentType;

    private long sizeBytes;

    private Double durationSeconds;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private UploadStatus uploadStatus;

    @Column(nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    @Version
    private long version;

    protected Video() {
    }

    public static Video create(String fileName, String contentType, long sizeBytes, Instant now) {
        var video = new Video();
        video.id = UUID.randomUUID();
        video.fileName = fileName;
        video.contentType = contentType;
        video.sizeBytes = sizeBytes;
        video.uploadStatus = UploadStatus.PENDING;
        // O PostgreSQL guarda microssegundos; truncar mantém o cursor de paginação idêntico ao valor persistido.
        video.createdAt = now.truncatedTo(ChronoUnit.MICROS);
        video.updatedAt = video.createdAt;
        return video;
    }

    public String storageKey() {
        return id + "/original.mp4";
    }

    /** Uma nova URL de upload pode ser emitida enquanto o upload não foi confirmado. */
    public void startUpload(Instant now) {
        requireUploadInProgress();
        if (uploadStatus == UploadStatus.UPLOADING) {
            return;
        }
        uploadStatus = UploadStatus.UPLOADING;
        updatedAt = now;
    }

    public void markReady(double durationSeconds, Instant now) {
        requireUploadInProgress();
        this.durationSeconds = durationSeconds;
        uploadStatus = UploadStatus.READY;
        updatedAt = now;
    }

    public void markFailed(Instant now) {
        requireUploadInProgress();
        uploadStatus = UploadStatus.FAILED;
        updatedAt = now;
    }

    public boolean isReady() {
        return uploadStatus == UploadStatus.READY;
    }

    private void requireUploadInProgress() {
        if (uploadStatus == UploadStatus.READY || uploadStatus == UploadStatus.FAILED) {
            throw new InvalidVideoStateException("O upload deste vídeo já foi finalizado.");
        }
    }

    public String getOwnerId() { return ownerId; }

    public void assignOwner(String subject) { ownerId = subject; }

    public UUID getId() {
        return id;
    }

    public String getFileName() {
        return fileName;
    }

    public String getContentType() {
        return contentType;
    }

    public long getSizeBytes() {
        return sizeBytes;
    }

    public Double getDurationSeconds() {
        return durationSeconds;
    }

    public UploadStatus getUploadStatus() {
        return uploadStatus;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
