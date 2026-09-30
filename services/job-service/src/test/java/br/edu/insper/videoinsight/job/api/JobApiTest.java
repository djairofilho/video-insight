package br.edu.insper.videoinsight.job.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.edu.insper.videoinsight.job.IntegrationTest;
import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.JobStatus;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import br.edu.insper.videoinsight.job.messaging.ProcessingCompleted;
import br.edu.insper.videoinsight.job.storage.PresignedUrl;
import br.edu.insper.videoinsight.job.video.VideoServiceUnavailableException;
import br.edu.insper.videoinsight.job.video.VideoSummary;
import java.net.URI;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class JobApiTest extends IntegrationTest {
    private static final String KEY = "idempotency-key-0001";
    private static final String ALL_OPERATIONS = "{\"operations\":[\"summary\",\"transcription\"]}";

    @Test
    void createsQueuedJobAndStoresRequestedEventInOutbox() throws Exception {
        var videoId = UUID.randomUUID();
        var correlationId = UUID.randomUUID().toString();
        videoIsReady(videoId);

        mockMvc.perform(post("/api/v1/videos/{videoId}/jobs", videoId)
                        .header("Idempotency-Key", KEY)
                        .header("X-Correlation-Id", correlationId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(ALL_OPERATIONS))
                .andExpect(status().isAccepted())
                .andExpect(header().string("X-Correlation-Id", correlationId))
                .andExpect(jsonPath("$.video_id").value(videoId.toString()))
                .andExpect(jsonPath("$.status").value("queued"))
                .andExpect(jsonPath("$.operations[0]").value("transcription"))
                .andExpect(jsonPath("$.operations[1]").value("summary"))
                .andExpect(jsonPath("$.progress_percent").value(0))
                .andExpect(jsonPath("$.attempt").value(1))
                .andExpect(jsonPath("$.stage").doesNotExist())
                .andExpect(jsonPath("$.error").doesNotExist());

        var events = outbox.findAll();
        assertThat(events).hasSize(1);
        var payload = mapper.readTree(events.getFirst().getPayload());
        assertThat(payload.get("event_type").stringValue()).isEqualTo("processing.requested");
        assertThat(payload.get("correlation_id").stringValue()).isEqualTo(correlationId);
        assertThat(payload.at("/data/storage_key").stringValue()).isEqualTo(videoId + "/original.mp4");
        assertThat(payload.at("/data/attempt").intValue()).isEqualTo(1);
        assertThat(attempts.findAll()).singleElement()
                .satisfies(attempt -> assertThat(attempt.getStatus()).isEqualTo(JobStatus.QUEUED));
    }

    @Test
    void repeatedIdempotencyKeyReturnsTheSameJob() throws Exception {
        var videoId = UUID.randomUUID();
        videoIsReady(videoId);

        var first = json(postJob(videoId, KEY, ALL_OPERATIONS).andExpect(status().isAccepted()));
        var second = json(postJob(videoId, KEY, "{\"operations\":[\"transcription\",\"summary\"]}")
                .andExpect(status().isAccepted()));

        assertThat(second.get("id")).isEqualTo(first.get("id"));
        assertThat(jobs.count()).isEqualTo(1);
        assertThat(outbox.count()).isEqualTo(1);
        verify(videoClient, times(1)).findVideo(videoId);
    }

    @Test
    void reusingIdempotencyKeyForAnotherRequestIsAConflict() throws Exception {
        var videoId = UUID.randomUUID();
        videoIsReady(videoId);
        postJob(videoId, KEY, ALL_OPERATIONS).andExpect(status().isAccepted());

        postJob(videoId, KEY, "{\"operations\":[\"chapters\"]}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_REUSED"));
    }

    @Test
    void rejectsJobForMissingVideo() throws Exception {
        var videoId = UUID.randomUUID();
        when(videoClient.findVideo(videoId)).thenReturn(Optional.empty());

        postJob(videoId, KEY, ALL_OPERATIONS)
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("VIDEO_NOT_FOUND"))
                .andExpect(jsonPath("$.correlation_id").isNotEmpty());
        assertThat(jobs.count()).isZero();
    }

    @Test
    void rejectsJobBeforeUploadIsConfirmed() throws Exception {
        var videoId = UUID.randomUUID();
        when(videoClient.findVideo(videoId)).thenReturn(Optional.of(new VideoSummary(videoId, "uploading")));

        postJob(videoId, KEY, ALL_OPERATIONS)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("VIDEO_NOT_READY"));
    }

    @Test
    void reportsUnavailableVideoService() throws Exception {
        var videoId = UUID.randomUUID();
        when(videoClient.findVideo(videoId))
                .thenThrow(new VideoServiceUnavailableException(new RuntimeException("timeout")));

        postJob(videoId, KEY, ALL_OPERATIONS)
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("VIDEO_SERVICE_UNAVAILABLE"));
    }

    @Test
    void rejectsInvalidCreateRequests() throws Exception {
        var videoId = UUID.randomUUID();
        videoIsReady(videoId);

        postJob(videoId, KEY, "{\"operations\":[]}").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        postJob(videoId, KEY, "{\"operations\":[\"translation\"]}").andExpect(status().isBadRequest());
        postJob(videoId, KEY, "{\"operations\":[\"summary\",\"summary\"]}").andExpect(status().isBadRequest());
        postJob(videoId, KEY, "{not json").andExpect(status().isBadRequest());
        postJob(videoId, "short", ALL_OPERATIONS).andExpect(status().isBadRequest());
        mockMvc.perform(post("/api/v1/videos/{videoId}/jobs", videoId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(ALL_OPERATIONS))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Requisição inválida: header Idempotency-Key ausente"));
        mockMvc.perform(post("/api/v1/videos/not-a-uuid/jobs")
                        .header("Idempotency-Key", KEY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(ALL_OPERATIONS))
                .andExpect(status().isBadRequest());
        assertThat(jobs.count()).isZero();
    }

    @Test
    void healthIsAvailable() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void returnsJobOrNotFound() throws Exception {
        var jobId = createJob();

        mockMvc.perform(get("/api/v1/jobs/{jobId}", jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(jobId.toString()))
                .andExpect(jsonPath("$.created_at").isNotEmpty());
        mockMvc.perform(get("/api/v1/jobs/{jobId}", UUID.randomUUID()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("JOB_NOT_FOUND"));
    }

    @Test
    void cancelsUnfinishedJobsOnlyOnce() throws Exception {
        var jobId = createJob();

        mockMvc.perform(post("/api/v1/jobs/{jobId}/cancel", jobId))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.status").value("cancelled"));
        mockMvc.perform(post("/api/v1/jobs/{jobId}/cancel", jobId))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_JOB_STATE"));
        assertThat(attempts.findByJobIdOrderByAttempt(jobId)).singleElement()
                .satisfies(attempt -> assertThat(attempt.getStatus()).isEqualTo(JobStatus.CANCELLED));
    }

    @Test
    void retriesFailedJobsPreservingThePreviousAttempt() throws Exception {
        var jobId = createJob();
        mockMvc.perform(post("/api/v1/jobs/{jobId}/retry", jobId))
                .andExpect(status().isConflict());

        failJob(jobId);
        mockMvc.perform(get("/api/v1/jobs/{jobId}", jobId))
                .andExpect(jsonPath("$.status").value("failed"))
                .andExpect(jsonPath("$.stage").value("transcribing"))
                .andExpect(jsonPath("$.error.code").value("STT_TIMEOUT"))
                .andExpect(jsonPath("$.error.retryable").value(true));

        mockMvc.perform(post("/api/v1/jobs/{jobId}/retry", jobId))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.status").value("queued"))
                .andExpect(jsonPath("$.attempt").value(2))
                .andExpect(jsonPath("$.error").doesNotExist());

        var history = attempts.findByJobIdOrderByAttempt(jobId);
        assertThat(history).hasSize(2);
        assertThat(history.get(0).getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(history.get(0).getErrorCode()).isEqualTo("STT_TIMEOUT");
        assertThat(history.get(1).getStatus()).isEqualTo(JobStatus.QUEUED);
        assertThat(outbox.count()).isEqualTo(2);
    }

    @Test
    void returnsResultOnlyAfterCompletion() throws Exception {
        var jobId = createJob();
        mockMvc.perform(get("/api/v1/jobs/{jobId}/result", jobId))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("JOB_NOT_COMPLETED"));

        when(artifactStorage.readTranscript("t.json"))
                .thenReturn(List.of(new TranscriptSegment(0, 4.5, "Olá, turma.")));
        when(artifactStorage.readSummary("s.json")).thenReturn("Aula introdutória.");
        when(artifactStorage.readChapters("c.json")).thenReturn(List.of(new Chapter("Introdução", 0, 4.5)));
        completeJob(jobId, new ProcessingCompleted.Artifacts("t.json", "t.txt", null, "s.json", "c.json"));

        mockMvc.perform(get("/api/v1/jobs/{jobId}/result", jobId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.job_id").value(jobId.toString()))
                .andExpect(jsonPath("$.transcript[0].start_seconds").value(0.0))
                .andExpect(jsonPath("$.transcript[0].end_seconds").value(4.5))
                .andExpect(jsonPath("$.transcript[0].text").value("Olá, turma."))
                .andExpect(jsonPath("$.summary").value("Aula introdutória."))
                .andExpect(jsonPath("$.chapters[0].title").value("Introdução"))
                .andExpect(jsonPath("$.models").isArray())
                .andExpect(jsonPath("$.completed_at").isNotEmpty());
    }

    @Test
    void exportsTranscriptWithTemporaryUrl() throws Exception {
        var jobId = createJob();
        mockMvc.perform(get("/api/v1/jobs/{jobId}/transcript", jobId).param("format", "txt"))
                .andExpect(status().isConflict());

        when(artifactStorage.readTranscript("t.json")).thenReturn(List.of());
        completeJob(jobId, new ProcessingCompleted.Artifacts("t.json", "t.txt", null, null, null));
        var expiresAt = Instant.parse("2026-10-01T12:00:00Z");
        when(artifactStorage.presignDownload(eq("t.txt"), anyString()))
                .thenReturn(new PresignedUrl(URI.create("http://minio.local/t.txt?X-Amz-Signature=x"), expiresAt));

        mockMvc.perform(get("/api/v1/jobs/{jobId}/transcript", jobId).param("format", "txt"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.url").value("http://minio.local/t.txt?X-Amz-Signature=x"))
                .andExpect(jsonPath("$.expires_at").value("2026-10-01T12:00:00Z"));
        verify(artifactStorage).presignDownload("t.txt", "transcricao-" + jobId + ".txt");

        mockMvc.perform(get("/api/v1/jobs/{jobId}/transcript", jobId).param("format", "srt"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("ARTIFACT_NOT_AVAILABLE"));
        mockMvc.perform(get("/api/v1/jobs/{jobId}/transcript", jobId).param("format", "pdf"))
                .andExpect(status().isBadRequest());
        mockMvc.perform(get("/api/v1/jobs/{jobId}/transcript", jobId))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Requisição inválida: parâmetro format ausente"));
    }

    @Test
    void mapsUnknownRoutesAndMethods() throws Exception {
        mockMvc.perform(get("/api/v1/unknown"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
        mockMvc.perform(delete("/api/v1/jobs/{jobId}", UUID.randomUUID()))
                .andExpect(status().isMethodNotAllowed());
    }
}
