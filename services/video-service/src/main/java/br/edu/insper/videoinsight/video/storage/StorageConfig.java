package br.edu.insper.videoinsight.video.storage;

import br.edu.insper.videoinsight.video.VideoServiceProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

/**
 * O cliente usa o endereço interno do MinIO; o presigner usa o endereço público, porque a assinatura depende do host
 * que o navegador vai acessar.
 */
@Configuration
public class StorageConfig {
    @Bean
    S3Client s3Client(VideoServiceProperties properties) {
        var storage = properties.storage();
        return S3Client.builder()
                .endpointOverride(storage.endpoint())
                .region(Region.of(storage.region()))
                .credentialsProvider(credentials(storage))
                .forcePathStyle(true)
                .httpClient(UrlConnectionHttpClient.create())
                .build();
    }

    @Bean
    S3Presigner s3Presigner(VideoServiceProperties properties) {
        var storage = properties.storage();
        return S3Presigner.builder()
                .endpointOverride(storage.publicEndpoint())
                .region(Region.of(storage.region()))
                .credentialsProvider(credentials(storage))
                .serviceConfiguration(S3Configuration.builder().pathStyleAccessEnabled(true).build())
                .build();
    }

    private static StaticCredentialsProvider credentials(VideoServiceProperties.Storage storage) {
        return StaticCredentialsProvider.create(AwsBasicCredentials.create(storage.accessKey(), storage.secretKey()));
    }
}
