package br.edu.insper.videoinsight.job.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import software.amazon.awssdk.core.ResponseBytes;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectResponse;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

class ArtifactStorageTest {
    private final S3Client s3Client = mock(S3Client.class);
    private ArtifactStorage storage;

    @BeforeEach
    void setUp() {
        var properties = new JobServiceProperties(null, null, null, new JobServiceProperties.Storage(
                URI.create("http://minio:9000"), URI.create("http://localhost:9000"), "us-east-1",
                "access", "secret-key", "video-insight", Duration.ofMinutes(15)));
        var config = new StorageConfig();
        var mapper = JsonMapper.builder().propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE).build();
        storage = new ArtifactStorage(s3Client, config.s3Presigner(properties), mapper, properties);
        assertThat(config.s3Client(properties)).isNotNull();
    }

    @Test
    void readsTranscriptAsDocumentedObjectOrPlainList() {
        stub("{\"segments\":[{\"start_seconds\":0,\"end_seconds\":2.5,\"text\":\"Olá\"}]}");
        assertThat(storage.readTranscript("t.json")).containsExactly(new TranscriptSegment(0, 2.5, "Olá"));

        stub("[{\"start_seconds\":1,\"end_seconds\":2,\"text\":\"Tchau\"}]");
        assertThat(storage.readTranscript("t.json")).containsExactly(new TranscriptSegment(1, 2, "Tchau"));

        stub("{\"text\":\"sem lista\"}");
        assertThatThrownBy(() -> storage.readTranscript("t.json")).isInstanceOf(ArtifactFormatException.class);
    }

    @Test
    void readsChaptersAndSummary() {
        stub("{\"chapters\":[{\"title\":\"Início\",\"start_seconds\":0,\"end_seconds\":60}]}");
        assertThat(storage.readChapters("c.json")).containsExactly(new Chapter("Início", 0, 60));

        stub("{\"summary\":\"Resumo da aula.\"}");
        assertThat(storage.readSummary("s.json")).isEqualTo("Resumo da aula.");

        stub("\"Resumo direto.\"");
        assertThat(storage.readSummary("s.json")).isEqualTo("Resumo direto.");

        stub("{\"resumo\":\"campo errado\"}");
        assertThatThrownBy(() -> storage.readSummary("s.json")).isInstanceOf(ArtifactFormatException.class);
    }

    @Test
    void presignsDownloadsWithThePublicEndpoint() {
        var before = Instant.now();

        var url = storage.presignDownload("artifacts/job/transcript.txt", "transcricao.txt");

        assertThat(url.url().toString())
                .startsWith("http://localhost:9000/video-insight/artifacts/job/transcript.txt?")
                .contains("X-Amz-Signature=")
                .contains("response-content-disposition=");
        assertThat(url.expiresAt()).isBetween(before.plusSeconds(890), before.plusSeconds(910));
    }

    private void stub(String json) {
        when(s3Client.getObjectAsBytes(any(GetObjectRequest.class))).thenReturn(ResponseBytes.fromByteArray(
                GetObjectResponse.builder().build(), json.getBytes(StandardCharsets.UTF_8)));
    }
}
