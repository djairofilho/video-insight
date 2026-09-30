package br.edu.insper.videoinsight.job.storage;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import java.net.URISyntaxException;
import java.util.List;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Lê os artefatos produzidos pelo Processing Service e gera URLs temporárias de download.
 *
 * <p>Os formatos estão em {@code contracts/artifacts}. A leitura aceita tanto o objeto documentado (por exemplo
 * {@code {"segments": [...]}}) quanto a lista direta, enquanto o formato final não é fechado com o Processing
 * Service.
 */
@Component
public class ArtifactStorage {
    private static final TypeReference<List<TranscriptSegment>> SEGMENTS = new TypeReference<>() {
    };
    private static final TypeReference<List<Chapter>> CHAPTERS = new TypeReference<>() {
    };

    private final S3Client s3Client;
    private final S3Presigner presigner;
    private final JsonMapper mapper;
    private final JobServiceProperties.Storage properties;

    public ArtifactStorage(
            S3Client s3Client, S3Presigner presigner, JsonMapper mapper, JobServiceProperties properties) {
        this.s3Client = s3Client;
        this.presigner = presigner;
        this.mapper = mapper;
        this.properties = properties.storage();
    }

    public List<TranscriptSegment> readTranscript(String key) {
        return mapper.convertValue(listField(read(key), "segments", key), SEGMENTS);
    }

    public List<Chapter> readChapters(String key) {
        return mapper.convertValue(listField(read(key), "chapters", key), CHAPTERS);
    }

    public String readSummary(String key) {
        var node = read(key);
        var summary = node.isString() ? node : node.path("summary");
        if (!summary.isString()) {
            throw new ArtifactFormatException("Artefato " + key + " não contém o campo summary.");
        }
        return summary.stringValue();
    }

    public PresignedUrl presignDownload(String key, String fileName) {
        var getObject = GetObjectRequest.builder()
                .bucket(properties.bucket())
                .key(key)
                .responseContentDisposition("attachment; filename=\"" + fileName + "\"")
                .build();
        var presigned = presigner.presignGetObject(GetObjectPresignRequest.builder()
                .signatureDuration(properties.presignTtl())
                .getObjectRequest(getObject)
                .build());
        try {
            return new PresignedUrl(presigned.url().toURI(), presigned.expiration());
        } catch (URISyntaxException exception) {
            throw new IllegalStateException("URL assinada inválida para " + key, exception);
        }
    }

    private JsonNode read(String key) {
        var request = GetObjectRequest.builder().bucket(properties.bucket()).key(key).build();
        return mapper.readTree(s3Client.getObjectAsBytes(request).asByteArray());
    }

    private static JsonNode listField(JsonNode node, String field, String key) {
        var list = node.isArray() ? node : node.path(field);
        if (!list.isArray()) {
            throw new ArtifactFormatException("Artefato " + key + " não contém a lista " + field + ".");
        }
        return list;
    }
}
