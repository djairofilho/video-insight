package br.edu.insper.videoinsight.video.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class VideoTest {
    private static final Instant NOW = Instant.parse("2026-09-30T12:00:00.123456789Z");

    @Test
    void startsPendingWithTheAgreedStorageKey() {
        var video = Video.create("aula.mp4", "video/mp4", 10, NOW);

        assertThat(video.getUploadStatus()).isEqualTo(UploadStatus.PENDING);
        assertThat(video.storageKey()).isEqualTo(video.getId() + "/original.mp4");
        assertThat(video.getCreatedAt()).isEqualTo(Instant.parse("2026-09-30T12:00:00.123456Z"));
        assertThat(video.getUpdatedAt()).isEqualTo(video.getCreatedAt());
        assertThat(video.isReady()).isFalse();
    }

    @Test
    void followsTheUploadLifecycle() {
        var video = Video.create("aula.mp4", "video/mp4", 10, NOW);

        video.startUpload(NOW.plusSeconds(1));
        assertThat(video.getUploadStatus()).isEqualTo(UploadStatus.UPLOADING);
        video.markReady(90.0, NOW.plusSeconds(2));

        assertThat(video.isReady()).isTrue();
        assertThat(video.getDurationSeconds()).isEqualTo(90.0);
        assertThat(video.getUpdatedAt()).isEqualTo(NOW.plusSeconds(2));
        assertThat(UploadStatus.READY.value()).isEqualTo("ready");
    }

    @Test
    void finishedUploadsCannotChange() {
        var ready = Video.create("aula.mp4", "video/mp4", 10, NOW);
        ready.markReady(90.0, NOW);
        var failed = Video.create("aula.mp4", "video/mp4", 10, NOW);
        failed.markFailed(NOW);

        assertThatThrownBy(() -> ready.startUpload(NOW)).isInstanceOf(InvalidVideoStateException.class);
        assertThatThrownBy(() -> ready.markFailed(NOW)).isInstanceOf(InvalidVideoStateException.class);
        assertThatThrownBy(() -> failed.startUpload(NOW)).isInstanceOf(InvalidVideoStateException.class);
        assertThatThrownBy(() -> failed.markReady(1.0, NOW)).isInstanceOf(InvalidVideoStateException.class);
    }
}
