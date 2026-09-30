package br.edu.insper.videoinsight.job.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class JobTest {
    private static final Instant NOW = Instant.parse("2026-09-30T12:00:00Z");
    private final UUID videoId = UUID.randomUUID();

    @Test
    void startsQueuedAtFirstAttempt() {
        var job = newJob();

        assertThat(job.getStatus()).isEqualTo(JobStatus.QUEUED);
        assertThat(job.getAttempt()).isEqualTo(1);
        assertThat(job.getProgressPercent()).isZero();
        assertThat(job.getStorageKey()).isEqualTo("videos/key.mp4");
        assertThat(job.getCreatedAt()).isEqualTo(NOW);
        assertThat(job.acceptsEventsFor(1)).isTrue();
        assertThat(job.acceptsEventsFor(2)).isFalse();
    }

    @Test
    void progressNeverMovesBackwardsOrPastOneHundred() {
        var job = newJob();

        job.progress(Stage.TRANSCRIBING, 60, NOW);
        job.progress(Stage.SUMMARIZING, 20, NOW);
        assertThat(job.getProgressPercent()).isEqualTo(60);

        job.progress(Stage.UPLOADING_ARTIFACTS, 150, NOW);
        assertThat(job.getProgressPercent()).isEqualTo(100);
        assertThat(job.getStatus()).isEqualTo(JobStatus.PROCESSING);
    }

    @Test
    void completedAndCancelledJobsCannotChangeAgain() {
        var completed = newJob();
        completed.complete(NOW);
        assertThat(completed.acceptsEventsFor(1)).isFalse();
        assertThatThrownBy(() -> completed.cancel(NOW)).isInstanceOf(InvalidJobStateException.class);
        assertThatThrownBy(() -> completed.retry(NOW)).isInstanceOf(InvalidJobStateException.class);

        var cancelled = newJob();
        cancelled.cancel(NOW);
        assertThat(cancelled.getStatus()).isEqualTo(JobStatus.CANCELLED);
        assertThatThrownBy(() -> cancelled.retry(NOW)).isInstanceOf(InvalidJobStateException.class);
    }

    @Test
    void retryStartsANewCleanAttempt() {
        var job = newJob();
        job.progress(Stage.TRANSCRIBING, 40, NOW);
        job.fail(Stage.TRANSCRIBING, "STT_ERROR", "Falhou", false, NOW);
        assertThat(job.getErrorRetryable()).isFalse();

        job.retry(NOW);

        assertThat(job.getAttempt()).isEqualTo(2);
        assertThat(job.getStatus()).isEqualTo(JobStatus.QUEUED);
        assertThat(job.getStage()).isNull();
        assertThat(job.getProgressPercent()).isZero();
        assertThat(job.getErrorCode()).isNull();
        assertThat(job.getErrorMessage()).isNull();
        assertThat(job.acceptsEventsFor(1)).isFalse();
        assertThat(job.acceptsEventsFor(2)).isTrue();
    }

    @Test
    void comparesIdempotentRequests() {
        var job = newJob();

        assertThat(job.hasSameRequest(videoId, List.of(Operation.TRANSCRIPTION))).isTrue();
        assertThat(job.hasSameRequest(videoId, List.of(Operation.SUMMARY))).isFalse();
        assertThat(job.hasSameRequest(UUID.randomUUID(), List.of(Operation.TRANSCRIPTION))).isFalse();
    }

    @Test
    void convertsOperationsAndEnumValues() {
        var converter = new OperationsConverter();
        var operations = List.of(Operation.TRANSCRIPTION, Operation.CHAPTERS);

        assertThat(converter.convertToDatabaseColumn(operations)).isEqualTo("transcription,chapters");
        assertThat(converter.convertToEntityAttribute("transcription,chapters")).isEqualTo(operations);
        assertThat(Stage.from("creating_chapters")).isEqualTo(Stage.CREATING_CHAPTERS);
        assertThatThrownBy(() -> Stage.from("dancing")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Operation.from("translation")).isInstanceOf(IllegalArgumentException.class);
        assertThat(JobStatus.FAILED.isTerminal()).isTrue();
        assertThat(JobStatus.PROCESSING.isTerminal()).isFalse();
    }

    private Job newJob() {
        return Job.create(videoId, List.of(Operation.TRANSCRIPTION), "key", "videos/key.mp4", NOW);
    }
}
