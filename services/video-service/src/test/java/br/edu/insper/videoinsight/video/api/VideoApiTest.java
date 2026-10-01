package br.edu.insper.videoinsight.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import br.edu.insper.videoinsight.video.IntegrationTest;
import br.edu.insper.videoinsight.video.domain.UploadStatus;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import software.amazon.awssdk.core.exception.SdkClientException;
import tools.jackson.databind.JsonNode;

class VideoApiTest extends IntegrationTest {

    @Test
    void createsPendingVideo() throws Exception {
        var correlationId = UUID.randomUUID().toString();

        mockMvc.perform(post("/api/v1/videos")
                        .header("X-Correlation-Id", correlationId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(videoBody("aula.mp4", "video/mp4", SIZE)))
                .andExpect(status().isCreated())
                .andExpect(header().string("X-Correlation-Id", correlationId))
                .andExpect(jsonPath("$.id").isString())
                .andExpect(jsonPath("$.file_name").value("aula.mp4"))
                .andExpect(jsonPath("$.content_type").value("video/mp4"))
                .andExpect(jsonPath("$.size_bytes").value(SIZE))
                .andExpect(jsonPath("$.upload_status").value("pending"))
                .andExpect(jsonPath("$.created_at").isString())
                .andExpect(jsonPath("$.updated_at").isString())
                .andExpect(jsonPath("$.duration_seconds").doesNotExist());

        assertThat(videos.count()).isEqualTo(1);
    }

    @Test
    void rejectsInvalidVideos() throws Exception {
        postVideo(videoBody("aula.mov", "video/quicktime", SIZE))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
                .andExpect(jsonPath("$.correlation_id").isString());
        postVideo(videoBody("grande.mp4", "video/mp4", 104_857_601)).andExpect(status().isBadRequest());
        postVideo(videoBody("vazio.mp4", "video/mp4", 0)).andExpect(status().isBadRequest());
        postVideo(videoBody(" ", "video/mp4", SIZE)).andExpect(status().isBadRequest());
        postVideo("{\"file_name\":\"aula.mp4\"}").andExpect(status().isBadRequest());
        postVideo("isto nao e json").andExpect(status().isBadRequest());

        assertThat(videos.count()).isZero();
    }

    @Test
    void acceptsTheMaximumSize() throws Exception {
        postVideo(videoBody("limite.mp4", "video/mp4", 104_857_600)).andExpect(status().isCreated());
    }

    @Test
    void getsVideoById() throws Exception {
        var videoId = createVideo();

        mockMvc.perform(get("/api/v1/videos/{videoId}", videoId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(videoId.toString()))
                .andExpect(jsonPath("$.upload_status").value("pending"));
    }

    @Test
    void unknownVideoIsNotFound() throws Exception {
        mockMvc.perform(get("/api/v1/videos/{videoId}", UUID.randomUUID()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("VIDEO_NOT_FOUND"));
        mockMvc.perform(get("/api/v1/videos/nao-e-uuid")).andExpect(status().isBadRequest());
    }

    @Test
    void uploadUrlMovesVideoToUploading() throws Exception {
        var videoId = createVideo();

        mockMvc.perform(post("/api/v1/videos/{videoId}/upload-url", videoId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.method").value("PUT"))
                .andExpect(jsonPath("$.url").value(containsString(videoId + "/original.mp4")))
                .andExpect(jsonPath("$.expires_at").isString())
                .andExpect(jsonPath("$.headers.content-type").value("video/mp4"));

        assertThat(videos.findById(videoId)).get()
                .satisfies(video -> assertThat(video.getUploadStatus()).isEqualTo(UploadStatus.UPLOADING));

        // Uma nova URL pode ser pedida enquanto o upload não foi confirmado.
        mockMvc.perform(post("/api/v1/videos/{videoId}/upload-url", videoId)).andExpect(status().isOk());
    }

    @Test
    void uploadUrlForReadyVideoIsAConflict() throws Exception {
        var videoId = createReadyVideo();

        mockMvc.perform(post("/api/v1/videos/{videoId}/upload-url", videoId))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_VIDEO_STATE"));
        mockMvc.perform(post("/api/v1/videos/{videoId}/upload-url", UUID.randomUUID()))
                .andExpect(status().isNotFound());
    }

    @Test
    void completingTheUploadMakesTheVideoReady() throws Exception {
        var videoId = createVideo();
        mockMvc.perform(post("/api/v1/videos/{videoId}/upload-url", videoId));
        objectStored(videoId, SIZE);

        completeUpload(videoId, "{\"duration_seconds\":120.5}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.upload_status").value("ready"))
                .andExpect(jsonPath("$.duration_seconds").value(120.5));

        // Repetir a confirmação devolve o mesmo vídeo.
        completeUpload(videoId, "{\"duration_seconds\":120.5}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.upload_status").value("ready"));
    }

    @Test
    void completingWithoutTheFileIsAConflict() throws Exception {
        var videoId = createVideo();
        when(storage.objectSize(anyString())).thenReturn(Optional.empty());

        completeUpload(videoId, "{\"duration_seconds\":30}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("UPLOAD_NOT_FOUND"));

        assertThat(videos.findById(videoId)).get()
                .satisfies(video -> assertThat(video.getUploadStatus()).isEqualTo(UploadStatus.PENDING));
    }

    @Test
    void fileWithAnotherSizeFailsTheUpload() throws Exception {
        var videoId = createVideo();
        objectStored(videoId, SIZE + 1);

        completeUpload(videoId, "{\"duration_seconds\":30}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("UPLOAD_SIZE_MISMATCH"));

        mockMvc.perform(get("/api/v1/videos/{videoId}", videoId))
                .andExpect(jsonPath("$.upload_status").value("failed"));
        completeUpload(videoId, "{\"duration_seconds\":30}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_VIDEO_STATE"));
    }

    @Test
    void rejectsInvalidDurations() throws Exception {
        var videoId = createVideo();
        objectStored(videoId, SIZE);

        completeUpload(videoId, "{\"duration_seconds\":600.5}").andExpect(status().isBadRequest());
        completeUpload(videoId, "{\"duration_seconds\":0}").andExpect(status().isBadRequest());
        completeUpload(videoId, "{}").andExpect(status().isBadRequest());
        completeUpload(videoId, "{\"duration_seconds\":600}").andExpect(status().isOk());
    }

    @Test
    void playbackUrlRequiresAReadyVideo() throws Exception {
        var pending = createVideo();
        mockMvc.perform(post("/api/v1/videos/{videoId}/playback-url", pending))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("VIDEO_NOT_READY"));

        var ready = createReadyVideo();
        mockMvc.perform(post("/api/v1/videos/{videoId}/playback-url", ready))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.method").value("GET"));
    }

    @Test
    void deletesVideoAndItsFile() throws Exception {
        var videoId = createReadyVideo();

        mockMvc.perform(delete("/api/v1/videos/{videoId}", videoId)).andExpect(status().isNoContent());

        verify(storage).delete(videoId + "/original.mp4");
        mockMvc.perform(get("/api/v1/videos/{videoId}", videoId)).andExpect(status().isNotFound());
        mockMvc.perform(delete("/api/v1/videos/{videoId}", videoId)).andExpect(status().isNotFound());
    }

    @Test
    void keepsTheVideoWhenTheFileCannotBeDeleted() throws Exception {
        var videoId = createVideo();
        doThrow(SdkClientException.create("MinIO fora do ar")).when(storage).delete(anyString());

        mockMvc.perform(delete("/api/v1/videos/{videoId}", videoId))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("STORAGE_UNAVAILABLE"));

        assertThat(videos.existsById(videoId)).isTrue();
    }

    @Test
    void listsVideosNewestFirstWithCursor() throws Exception {
        var created = new ArrayList<UUID>();
        for (int i = 0; i < 5; i++) {
            created.add(createVideo());
        }

        var first = json(mockMvc.perform(get("/api/v1/videos").param("limit", "2")).andExpect(status().isOk()));
        var second = json(mockMvc.perform(get("/api/v1/videos").param("limit", "2")
                .param("cursor", first.get("next_cursor").stringValue())));
        var third = json(mockMvc.perform(get("/api/v1/videos").param("limit", "2")
                .param("cursor", second.get("next_cursor").stringValue())));

        assertThat(first.get("items")).hasSize(2);
        assertThat(second.get("items")).hasSize(2);
        assertThat(third.get("items")).hasSize(1);
        assertThat(third.has("next_cursor")).isFalse();

        var seen = new HashSet<String>();
        for (JsonNode page : List.of(first, second, third)) {
            page.get("items").forEach(item -> seen.add(item.get("id").stringValue()));
        }
        assertThat(seen).containsExactlyInAnyOrderElementsOf(created.stream().map(UUID::toString).toList());
    }

    @Test
    void listUsesDefaultLimitAndValidatesParameters() throws Exception {
        createVideo();

        mockMvc.perform(get("/api/v1/videos"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.next_cursor").doesNotExist());
        mockMvc.perform(get("/api/v1/videos").param("limit", "0")).andExpect(status().isBadRequest());
        mockMvc.perform(get("/api/v1/videos").param("limit", "101")).andExpect(status().isBadRequest());
        mockMvc.perform(get("/api/v1/videos").param("cursor", "invalido"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void unsupportedRoutesAndMethodsUseTheErrorFormat() throws Exception {
        mockMvc.perform(get("/api/v1/nada")).andExpect(status().isNotFound());
        mockMvc.perform(put("/api/v1/videos")).andExpect(status().isMethodNotAllowed());
        verify(storage, never()).delete(anyString());
    }

    @Test
    void healthIsStillAvailableForDeploy() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
