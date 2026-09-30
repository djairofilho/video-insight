package br.edu.insper.videoinsight.job.messaging;

import static org.assertj.core.api.Assertions.assertThat;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.Exchange;
import org.springframework.amqp.core.ExchangeTypes;
import org.springframework.amqp.core.Queue;

/** A fila de solicitações precisa ter exatamente os argumentos declarados pelo Processing Service. */
class RabbitTopologyConfigTest {
    private final JobServiceProperties.Messaging messaging = new JobServiceProperties.Messaging(
            "video-insight.processing", "job-service.processing-events", "processing-service.requests",
            "video-insight.dlx", "video-insight.processing.dlx");
    private final org.springframework.amqp.core.Declarables topology = new RabbitTopologyConfig()
            .messagingTopology(new JobServiceProperties(messaging, null, null, null));

    @Test
    void declaresRequestsQueueLikeTheProcessingService() {
        assertThat(queue("processing-service.requests").getArguments())
                .isEqualTo(Map.of("x-dead-letter-exchange", "video-insight.processing.dlx"));
        assertThat(exchange("video-insight.processing.dlx").getType()).isEqualTo(ExchangeTypes.TOPIC);
        assertThat(binding("processing-service.requests.dlq").getRoutingKey()).isEqualTo("#");
        assertThat(binding("processing-service.requests").getExchange()).isEqualTo("video-insight.processing");
        assertThat(binding("processing-service.requests").getRoutingKey()).isEqualTo("processing.requested");
    }

    @Test
    void keepsJobServiceDeadLettersSeparate() {
        assertThat(queue("job-service.processing-events").getArguments()).containsExactlyInAnyOrderEntriesOf(Map.of(
                "x-dead-letter-exchange", "video-insight.dlx",
                "x-dead-letter-routing-key", "job-service.processing-events.dlq"));
        assertThat(exchange("video-insight.processing").getType()).isEqualTo(ExchangeTypes.TOPIC);
        assertThat(topology.getDeclarablesByType(Binding.class))
                .filteredOn(binding -> binding.getDestination().equals("job-service.processing-events"))
                .extracting(Binding::getRoutingKey)
                .containsExactlyInAnyOrderElementsOf(EventTypes.CONSUMED);
    }

    private Queue queue(String name) {
        return topology.getDeclarablesByType(Queue.class).stream()
                .filter(queue -> queue.getName().equals(name)).findFirst().orElseThrow();
    }

    private Exchange exchange(String name) {
        return topology.getDeclarablesByType(Exchange.class).stream()
                .filter(exchange -> exchange.getName().equals(name)).findFirst().orElseThrow();
    }

    private Binding binding(String destination) {
        return topology.getDeclarablesByType(Binding.class).stream()
                .filter(binding -> binding.getDestination().equals(destination)).findFirst().orElseThrow();
    }
}
