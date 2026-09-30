package br.edu.insper.videoinsight.job.messaging;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "job-service.outbox.scheduler-enabled", havingValue = "true", matchIfMissing = true)
public class OutboxScheduler {
    private final OutboxPublisher publisher;

    public OutboxScheduler(OutboxPublisher publisher) {
        this.publisher = publisher;
    }

    @Scheduled(fixedDelayString = "${job-service.outbox.poll-interval}")
    public void publishPending() {
        publisher.publishPending();
    }
}
