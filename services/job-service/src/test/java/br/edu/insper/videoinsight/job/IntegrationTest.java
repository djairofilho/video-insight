package br.edu.insper.videoinsight.job;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import br.edu.insper.videoinsight.job.application.ProcessingEventHandler;
import br.edu.insper.videoinsight.job.domain.JobAttemptRepository;
import br.edu.insper.videoinsight.job.domain.JobRepository;
import br.edu.insper.videoinsight.job.domain.JobResultRepository;
import br.edu.insper.videoinsight.job.domain.OutboxEventRepository;
import br.edu.insper.videoinsight.job.domain.ProcessedEventRepository;
import br.edu.insper.videoinsight.job.domain.Stage;
import br.edu.insper.videoinsight.job.messaging.EventEnvelope;
import br.edu.insper.videoinsight.job.messaging.EventTypes;
import br.edu.insper.videoinsight.job.messaging.ProcessingCompleted;
import br.edu.insper.videoinsight.job.messaging.ProcessingEventData;
import br.edu.insper.videoinsight.job.messaging.ProcessingFailed;
import br.edu.insper.videoinsight.job.storage.ArtifactStorage;
import br.edu.insper.videoinsight.job.video.VideoClient;
import br.edu.insper.videoinsight.job.video.VideoSummary;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Contexto completo com H2; RabbitMQ, Video Service e MinIO são simulados. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public abstract class IntegrationTest {
    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected JsonMapper mapper;

    @Autowired
    protected JobRepository jobs;

    @Autowired
    protected JobAttemptRepository attempts;

    @Autowired
    protected JobResultRepository results;

    @Autowired
    protected OutboxEventRepository outbox;

    @Autowired
    protected ProcessedEventRepository processedEvents;

    @Autowired
    protected ProcessingEventHandler eventHandler;

    @MockitoBean
    protected RabbitTemplate rabbitTemplate;

    @MockitoBean
    protected VideoClient videoClient;

    @MockitoBean
    protected ArtifactStorage artifactStorage;

    @BeforeEach
    void cleanDatabase() {
        results.deleteAll();
        attempts.deleteAll();
        outbox.deleteAll();
        processedEvents.deleteAll();
        jobs.deleteAll();
    }

    protected void videoIsReady(UUID videoId) {
        when(videoClient.findVideo(videoId)).thenReturn(Optional.of(new VideoSummary(videoId, "ready")));
    }

    protected ResultActions postJob(UUID videoId, String idempotencyKey, String body) throws Exception {
        return mockMvc.perform(post("/api/v1/videos/{videoId}/jobs", videoId)
                .header("Idempotency-Key", idempotencyKey)
                .contentType(MediaType.APPLICATION_JSON)
                .content(body));
    }

    /** Cria um job pela API, com o vídeo pronto, e devolve seu id. */
    protected UUID createJob() throws Exception {
        var videoId = UUID.randomUUID();
        videoIsReady(videoId);
        var response = postJob(videoId, UUID.randomUUID().toString(),
                "{\"operations\":[\"transcription\",\"summary\",\"chapters\"]}")
                .andReturn().getResponse().getContentAsString();
        return UUID.fromString(mapper.readTree(response).get("id").stringValue());
    }

    protected JsonNode json(ResultActions actions) throws Exception {
        return mapper.readTree(actions.andReturn().getResponse().getContentAsString());
    }

    protected <T extends ProcessingEventData> EventEnvelope<T> event(String type, T data) {
        return new EventEnvelope<>(UUID.randomUUID(), type, 1, Instant.now(), UUID.randomUUID(), data);
    }

    protected void completeJob(UUID jobId, ProcessingCompleted.Artifacts artifacts) {
        var job = jobs.findById(jobId).orElseThrow();
        eventHandler.handle(event(EventTypes.PROCESSING_COMPLETED,
                new ProcessingCompleted(jobId, job.getVideoId(), job.getAttempt(), artifacts, List.of())));
    }

    protected void failJob(UUID jobId) {
        var job = jobs.findById(jobId).orElseThrow();
        eventHandler.handle(event(EventTypes.PROCESSING_FAILED, new ProcessingFailed(
                jobId, job.getVideoId(), job.getAttempt(), Stage.TRANSCRIBING, "STT_TIMEOUT", "Tempo esgotado", true)));
    }
}
