package br.edu.insper.videoinsight.job;

import java.net.URI;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("job-service")
public record JobServiceProperties(
        Messaging messaging,
        Outbox outbox,
        VideoService videoService,
        Storage storage) {

    public record Messaging(
            String exchange,
            String eventsQueue,
            String requestsQueue,
            String deadLetterExchange,
            String requestsDeadLetterExchange) {
        public String deadLetterQueue(String queue) {
            return queue + ".dlq";
        }
    }

    public record Outbox(boolean schedulerEnabled, Duration pollInterval, int batchSize) {
    }

    public record VideoService(URI baseUrl, String storageKeyTemplate, Duration timeout) {
    }

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
