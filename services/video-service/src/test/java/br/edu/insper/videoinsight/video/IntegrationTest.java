package br.edu.insper.videoinsight.video;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import br.edu.insper.videoinsight.video.domain.VideoRepository;
import br.edu.insper.videoinsight.video.storage.SignedUrl;
import br.edu.insper.videoinsight.video.storage.VideoStorage;
import java.net.URI;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
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

/** Contexto completo com H2; o MinIO é simulado. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public abstract class IntegrationTest {
    protected static final long SIZE = 1_048_576;

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected JsonMapper mapper;

    @Autowired
    protected VideoRepository videos;

    @MockitoBean
    protected VideoStorage storage;

    @BeforeEach
    void cleanDatabase() {
        videos.deleteAll();
        when(storage.presignUpload(anyString())).thenAnswer(invocation -> signedUrl("PUT", invocation.getArgument(0)));
        when(storage.presignPlayback(anyString())).thenAnswer(invocation -> signedUrl("GET", invocation.getArgument(0)));
    }

    protected ResultActions postVideo(String body) throws Exception {
        return mockMvc.perform(post("/api/v1/videos").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    protected static String videoBody(String fileName, String contentType, long sizeBytes) {
        return "{\"file_name\":\"%s\",\"content_type\":\"%s\",\"size_bytes\":%d}"
                .formatted(fileName, contentType, sizeBytes);
    }

    /** Cadastra um vídeo pela API e devolve seu id. */
    protected UUID createVideo() throws Exception {
        var response = json(postVideo(videoBody("aula.mp4", "video/mp4", SIZE)));
        return UUID.fromString(response.get("id").stringValue());
    }

    protected ResultActions completeUpload(UUID videoId, String body) throws Exception {
        return mockMvc.perform(post("/api/v1/videos/{videoId}/upload-complete", videoId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(body));
    }

    /** Cadastra um vídeo e confirma seu upload, simulando o arquivo no storage. */
    protected UUID createReadyVideo() throws Exception {
        var videoId = createVideo();
        objectStored(videoId, SIZE);
        completeUpload(videoId, "{\"duration_seconds\":120.5}");
        return videoId;
    }

    protected void objectStored(UUID videoId, long size) {
        when(storage.objectSize(videoId + "/original.mp4")).thenReturn(Optional.of(size));
    }

    protected JsonNode json(ResultActions actions) throws Exception {
        return mapper.readTree(actions.andReturn().getResponse().getContentAsString());
    }

    private static SignedUrl signedUrl(String method, String key) {
        return new SignedUrl(URI.create("http://localhost:9000/videos/" + key + "?X-Amz-Signature=teste"),
                method, Instant.parse("2026-01-01T00:15:00Z"), Map.of("content-type", "video/mp4"));
    }
}
