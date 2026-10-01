package br.edu.insper.videoinsight.video.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.edu.insper.videoinsight.video.VideoServiceProperties;
import java.net.URI;
import java.time.Duration;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketResponse;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.S3Exception;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

/** O presigner é real: a assinatura é calculada localmente, sem acesso à rede. */
class VideoStorageTest {
    private static final VideoServiceProperties PROPERTIES = new VideoServiceProperties(
            new VideoServiceProperties.Storage(
                    URI.create("http://minio:9000"),
                    URI.create("http://localhost:9000"),
                    "us-east-1",
                    "chave",
                    "segredo-de-teste",
                    "videos",
                    Duration.ofMinutes(15)));

    private final S3Client s3Client = mock(S3Client.class);
    private final S3Presigner presigner = new StorageConfig().s3Presigner(PROPERTIES);
    private final VideoStorage storage = new VideoStorage(s3Client, presigner, PROPERTIES);

    @AfterEach
    void closePresigner() {
        presigner.close();
    }

    @Test
    void presignsUploadWithThePublicEndpointAndContentType() {
        var url = storage.presignUpload("abc/original.mp4");

        assertThat(url.method()).isEqualTo("PUT");
        assertThat(url.url().toString()).startsWith("http://localhost:9000/videos/abc/original.mp4?");
        assertThat(url.url().getQuery()).contains("X-Amz-Signature=").contains("X-Amz-Expires=900");
        assertThat(url.headers()).containsEntry("content-type", "video/mp4").doesNotContainKey("host");
        assertThat(url.expiresAt()).isNotNull();
    }

    @Test
    void presignsPlayback() {
        var url = storage.presignPlayback("abc/original.mp4");

        assertThat(url.method()).isEqualTo("GET");
        assertThat(url.url().toString()).startsWith("http://localhost:9000/videos/abc/original.mp4?");
        assertThat(url.headers()).isNull();
    }

    @Test
    void readsTheSizeOfTheUploadedObject() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenReturn(HeadObjectResponse.builder().contentLength(123L).build());

        assertThat(storage.objectSize("abc/original.mp4")).contains(123L);
    }

    @Test
    void missingObjectHasNoSize() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenThrow(NoSuchKeyException.builder().build())
                .thenThrow(S3Exception.builder().statusCode(404).build());

        assertThat(storage.objectSize("abc/original.mp4")).isEmpty();
        assertThat(storage.objectSize("abc/original.mp4")).isEmpty();
    }

    @Test
    void otherStorageErrorsPropagate() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenThrow(S3Exception.builder().statusCode(403).build());

        assertThatThrownBy(() -> storage.objectSize("abc/original.mp4")).isInstanceOf(S3Exception.class);
    }

    @Test
    void deletesTheObject() {
        storage.delete("abc/original.mp4");

        verify(s3Client).deleteObject(DeleteObjectRequest.builder().bucket("videos").key("abc/original.mp4").build());
    }

    @Test
    void createsTheBucketOnlyWhenMissing() {
        when(s3Client.headBucket(any(HeadBucketRequest.class))).thenReturn(HeadBucketResponse.builder().build());
        storage.ensureBucket();
        verify(s3Client, never()).createBucket(any(CreateBucketRequest.class));

        when(s3Client.headBucket(any(HeadBucketRequest.class))).thenThrow(NoSuchBucketException.builder().build());
        storage.ensureBucket();
        verify(s3Client).createBucket(CreateBucketRequest.builder().bucket("videos").build());
    }

    @Test
    void bucketFailureDoesNotStopTheService() {
        var failingStorage = mock(VideoStorage.class);
        doThrow(new IllegalStateException("MinIO fora do ar")).when(failingStorage).ensureBucket();

        new BucketInitializer(failingStorage).createBucketIfMissing();

        verify(failingStorage).ensureBucket();
    }
}
