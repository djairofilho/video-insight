package br.edu.insper.videoinsight.job.messaging;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import br.edu.insper.videoinsight.job.IntegrationTest;
import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.Job;
import br.edu.insper.videoinsight.job.domain.JobStatus;
import br.edu.insper.videoinsight.job.domain.Stage;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.beans.factory.annotation.Autowired;

class ProcessingEventsTest extends IntegrationTest {
    @Autowired
    private ProcessingEventListener listener;

    private UUID jobId;
    private UUID videoId;

    @BeforeEach
    void createQueuedJob() throws Exception {
        jobId = createJob();
        videoId = job().getVideoId();
    }

    @Test
    void startedAndProgressedEventsUpdateStageAndProgress() {
        deliver("""
                {"event_id":"%s","event_type":"processing.started","event_version":1,
                 "occurred_at":"2026-09-30T12:00:00Z","correlation_id":"%s",
                 "data":{"job_id":"%s","video_id":"%s","attempt":1,"worker_id":"worker-1"}}
                """.formatted(UUID.randomUUID(), UUID.randomUUID(), jobId, videoId));
        assertThat(job().getStatus()).isEqualTo(JobStatus.PROCESSING);
        assertThat(attempts.findByJobIdAndAttempt(jobId, 1).orElseThrow().getStartedAt()).isNotNull();

        deliver(progressed(UUID.randomUUID(), 1, "transcribing", 60));
        deliver(progressed(UUID.randomUUID(), 1, "summarizing", 40));

        assertThat(job().getStage()).isEqualTo(Stage.SUMMARIZING);
        assertThat(job().getProgressPercent()).isEqualTo(60);
    }

    @Test
    void completedEventStoresStructuredResult() {
        when(artifactStorage.readTranscript("artifacts/t.json"))
                .thenReturn(List.of(new TranscriptSegment(0, 3, "Bom dia.")));
        when(artifactStorage.readSummary("artifacts/s.json")).thenReturn("Resumo.");
        when(artifactStorage.readChapters("artifacts/c.json")).thenReturn(List.of(new Chapter("Abertura", 0, 3)));

        deliver("""
                {"event_id":"%s","event_type":"processing.completed","event_version":1,
                 "occurred_at":"2026-09-30T12:00:00Z","correlation_id":"%s",
                 "data":{"job_id":"%s","video_id":"%s","attempt":1,
                  "artifacts":{"transcript_json_key":"artifacts/t.json","transcript_srt_key":"artifacts/t.srt",
                               "summary_json_key":"artifacts/s.json","chapters_json_key":"artifacts/c.json"},
                  "models":[{"purpose":"transcription","provider":"openai","model":"whisper-1","version":"2024"}]}}
                """.formatted(UUID.randomUUID(), UUID.randomUUID(), jobId, videoId));

        var job = job();
        assertThat(job.getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(job.getProgressPercent()).isEqualTo(100);
        var result = results.findById(jobId).orElseThrow();
        assertThat(result.getSummary()).isEqualTo("Resumo.");
        assertThat(result.getTranscriptSrtKey()).isEqualTo("artifacts/t.srt");
        assertThat(result.getModels()).contains("whisper-1");
        assertThat(attempts.findByJobIdAndAttempt(jobId, 1).orElseThrow().getFinishedAt()).isNotNull();
    }

    @Test
    void completedEventWithoutOptionalArtifacts() {
        when(artifactStorage.readTranscript("t.json")).thenReturn(List.of());

        completeJob(jobId, new ProcessingCompleted.Artifacts("t.json", null, null, null, null));

        var result = results.findById(jobId).orElseThrow();
        assertThat(result.getSummary()).isNull();
        assertThat(result.getChapters()).isNull();
    }

    @Test
    void failedEventRecordsTheCause() {
        failJob(jobId);

        var job = job();
        assertThat(job.getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(job.getErrorCode()).isEqualTo("STT_TIMEOUT");
        assertThat(job.getErrorRetryable()).isTrue();
        var attempt = attempts.findByJobIdAndAttempt(jobId, 1).orElseThrow();
        assertThat(attempt.getStage()).isEqualTo(Stage.TRANSCRIBING);
        assertThat(attempt.getErrorMessage()).isEqualTo("Tempo esgotado");
    }

    @Test
    void redeliveredEventIsAppliedOnlyOnce() {
        var eventId = UUID.randomUUID();
        deliver(progressed(eventId, 1, "transcribing", 30));
        deliver(progressed(eventId, 1, "summarizing", 70));

        assertThat(processedEvents.count()).isEqualTo(1);
        assertThat(job().getProgressPercent()).isEqualTo(30);
    }

    @Test
    void ignoresEventsFromOldAttemptsFinishedJobsAndUnknownJobs() {
        deliver(progressed(UUID.randomUUID(), 2, "transcribing", 50));
        assertThat(job().getProgressPercent()).isZero();

        cancelJobDirectly();
        deliver(progressed(UUID.randomUUID(), 1, "transcribing", 50));
        assertThat(job().getStatus()).isEqualTo(JobStatus.CANCELLED);

        eventHandler.handle(event(EventTypes.PROCESSING_PROGRESSED,
                new ProcessingProgressed(UUID.randomUUID(), videoId, 1, Stage.DOWNLOADING, 10, null)));
        assertThat(processedEvents.count()).isEqualTo(3);
    }

    @Test
    void invalidMessagesAreSentToTheDeadLetterQueue() {
        assertRejected("{not json");
        assertRejected("{\"event_type\":\"processing.started\",\"data\":{}}");
        assertRejected("""
                {"event_id":"%s","event_type":"processing.exploded","data":{}}
                """.formatted(UUID.randomUUID()));
        assertRejected("""
                {"event_id":"%s","event_type":"processing.progressed",
                 "data":{"job_id":"%s","video_id":"%s","attempt":0,"stage":"transcribing","progress_percent":150}}
                """.formatted(UUID.randomUUID(), jobId, videoId));
        assertRejected("""
                {"event_id":"%s","event_type":"processing.progressed",
                 "data":{"job_id":"%s","video_id":"%s","attempt":1,"stage":"dancing","progress_percent":10}}
                """.formatted(UUID.randomUUID(), jobId, videoId));
        assertThat(processedEvents.count()).isZero();
    }

    private void assertRejected(String body) {
        assertThatThrownBy(() -> deliver(body)).isInstanceOf(AmqpRejectAndDontRequeueException.class);
    }

    private String progressed(UUID eventId, int attempt, String stage, int percent) {
        // Sem correlation_id: o listener gera um novo.
        return """
                {"event_id":"%s","event_type":"processing.progressed",
                 "data":{"job_id":"%s","video_id":"%s","attempt":%d,"stage":"%s","progress_percent":%d,
                         "message":"ok"}}
                """.formatted(eventId, jobId, videoId, attempt, stage, percent);
    }

    private void deliver(String body) {
        listener.onMessage(new Message(body.getBytes(StandardCharsets.UTF_8), new MessageProperties()));
    }

    private void cancelJobDirectly() {
        var job = job();
        job.cancel(java.time.Instant.now());
        jobs.save(job);
    }

    private Job job() {
        return jobs.findById(jobId).orElseThrow();
    }
}
