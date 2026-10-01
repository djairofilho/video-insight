package br.edu.insper.videoinsight.video.storage;

import br.edu.insper.videoinsight.video.VideoServiceProperties;
import java.net.URISyntaxException;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.awscore.presigner.PresignedRequest;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.model.S3Exception;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

/** Acesso ao bucket de vídeos. O arquivo nunca passa pelo serviço: o navegador usa URLs assinadas. */
@Component
public class VideoStorage {
    private static final String VIDEO_CONTENT_TYPE = "video/mp4";
    private static final int NOT_FOUND = 404;

    private final S3Client s3Client;
    private final S3Presigner presigner;
    private final VideoServiceProperties.Storage properties;

    public VideoStorage(S3Client s3Client, S3Presigner presigner, VideoServiceProperties properties) {
        this.s3Client = s3Client;
        this.presigner = presigner;
        this.properties = properties.storage();
    }

    /** O {@code Content-Type} entra na assinatura, então o navegador precisa enviar os headers devolvidos. */
    public SignedUrl presignUpload(String key) {
        var putObject = PutObjectRequest.builder()
                .bucket(properties.bucket())
                .key(key)
                .contentType(VIDEO_CONTENT_TYPE)
                .build();
        var presigned = presigner.presignPutObject(PutObjectPresignRequest.builder()
                .signatureDuration(properties.presignTtl())
                .putObjectRequest(putObject)
                .build());
        return signedUrl(presigned, "PUT");
    }

    public SignedUrl presignPlayback(String key) {
        var getObject = GetObjectRequest.builder()
                .bucket(properties.bucket())
                .key(key)
                .responseContentType(VIDEO_CONTENT_TYPE)
                .build();
        var presigned = presigner.presignGetObject(GetObjectPresignRequest.builder()
                .signatureDuration(properties.presignTtl())
                .getObjectRequest(getObject)
                .build());
        return signedUrl(presigned, "GET");
    }

    /** Tamanho do objeto enviado, ou vazio se o upload ainda não chegou ao storage. */
    public Optional<Long> objectSize(String key) {
        try {
            var head = s3Client.headObject(HeadObjectRequest.builder().bucket(properties.bucket()).key(key).build());
            return Optional.of(head.contentLength());
        } catch (NoSuchKeyException exception) {
            return Optional.empty();
        } catch (S3Exception exception) {
            if (exception.statusCode() == NOT_FOUND) {
                return Optional.empty();
            }
            throw exception;
        }
    }

    public void delete(String key) {
        s3Client.deleteObject(DeleteObjectRequest.builder().bucket(properties.bucket()).key(key).build());
    }

    /** Cria o bucket de vídeos quando ele ainda não existe. */
    public void ensureBucket() {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(properties.bucket()).build());
        } catch (NoSuchBucketException exception) {
            s3Client.createBucket(CreateBucketRequest.builder().bucket(properties.bucket()).build());
        }
    }

    private static SignedUrl signedUrl(PresignedRequest presigned, String method) {
        try {
            return new SignedUrl(presigned.url().toURI(), method, presigned.expiration(),
                    headersToSend(presigned.signedHeaders()));
        } catch (URISyntaxException exception) {
            throw new IllegalStateException("URL assinada inválida", exception);
        }
    }

    /** O {@code host} é definido pelo próprio cliente HTTP; os demais headers assinados precisam ser enviados. */
    private static Map<String, String> headersToSend(Map<String, List<String>> signedHeaders) {
        var headers = new TreeMap<String, String>();
        signedHeaders.forEach((name, values) -> {
            if (!"host".equalsIgnoreCase(name)) {
                headers.put(name, String.join(",", values));
            }
        });
        return headers.isEmpty() ? null : headers;
    }
}
