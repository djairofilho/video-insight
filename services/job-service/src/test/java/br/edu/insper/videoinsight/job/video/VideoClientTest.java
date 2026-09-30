package br.edu.insper.videoinsight.job.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withResourceNotFound;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class VideoClientTest {
    private final UUID videoId = UUID.randomUUID();
    private MockRestServiceServer server;
    private VideoClient client;

    @BeforeEach
    void setUp() {
        var builder = RestClient.builder().baseUrl("http://video-service");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new VideoClient(builder.build());
    }

    @Test
    void readsTheVideoUploadStatus() {
        server.expect(requestTo("http://video-service/api/v1/videos/" + videoId))
                .andRespond(withSuccess("""
                        {"id":"%s","file_name":"aula.mp4","content_type":"video/mp4","size_bytes":10,
                         "upload_status":"ready","created_at":"2026-09-30T12:00:00Z"}
                        """.formatted(videoId), MediaType.APPLICATION_JSON));

        var video = client.findVideo(videoId).orElseThrow();

        assertThat(video.id()).isEqualTo(videoId);
        assertThat(video.isReady()).isTrue();
        server.verify();
    }

    @Test
    void videoWithPendingUploadIsNotReady() {
        server.expect(requestTo("http://video-service/api/v1/videos/" + videoId))
                .andRespond(withSuccess("{\"id\":\"%s\",\"upload_status\":\"pending\"}".formatted(videoId),
                        MediaType.APPLICATION_JSON));

        assertThat(client.findVideo(videoId)).get().satisfies(video -> assertThat(video.isReady()).isFalse());
    }

    @Test
    void missingVideoIsEmpty() {
        server.expect(requestTo("http://video-service/api/v1/videos/" + videoId)).andRespond(withResourceNotFound());

        assertThat(client.findVideo(videoId)).isEmpty();
    }

    @Test
    void reportsServerErrorsAsUnavailable() {
        server.expect(requestTo("http://video-service/api/v1/videos/" + videoId)).andRespond(withServerError());

        assertThatThrownBy(() -> client.findVideo(videoId)).isInstanceOf(VideoServiceUnavailableException.class);
    }
}
