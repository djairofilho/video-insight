package br.edu.insper.videoinsight.video;

import java.net.URI;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("video-service")
public record VideoServiceProperties(Storage storage) {

    public record Storage(
            URI endpoint,
            URI publicEndpoint,
            String region,
            String accessKey,
            String secretKey,
            String bucket,
            Duration presignTtl) {
    }
}
