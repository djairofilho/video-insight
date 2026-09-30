package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import br.edu.insper.videoinsight.job.domain.OutboxEvent;
import br.edu.insper.videoinsight.job.domain.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.data.domain.Limit;
import org.springframework.stereotype.Component;

/** Publica no RabbitMQ os eventos pendentes do outbox, em ordem de criação. */
@Component
public class OutboxPublisher {
    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    private final OutboxEventRepository outbox;
    private final RabbitTemplate rabbitTemplate;
    private final JobServiceProperties properties;
    private final Clock clock;

    public OutboxPublisher(
            OutboxEventRepository outbox,
            RabbitTemplate rabbitTemplate,
            JobServiceProperties properties,
            Clock clock) {
        this.outbox = outbox;
        this.rabbitTemplate = rabbitTemplate;
        this.properties = properties;
        this.clock = clock;
    }

    /** Retorna quantos eventos foram publicados; para no primeiro erro para preservar a ordem. */
    public int publishPending() {
        var pending = outbox.findByPublishedAtIsNullOrderByCreatedAt(Limit.of(properties.outbox().batchSize()));
        var published = 0;
        for (var event : pending) {
            try {
                rabbitTemplate.send(properties.messaging().exchange(), event.getRoutingKey(), toMessage(event));
            } catch (AmqpException exception) {
                log.warn("Falha ao publicar o evento {} do outbox; nova tentativa no próximo ciclo",
                        event.getId(), exception);
                break;
            }
            event.markPublished(clock.instant());
            outbox.save(event);
            published++;
        }
        return published;
    }

    private static Message toMessage(OutboxEvent event) {
        return MessageBuilder.withBody(event.getPayload().getBytes(StandardCharsets.UTF_8))
                .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                .setContentEncoding(StandardCharsets.UTF_8.name())
                .setDeliveryMode(MessageDeliveryMode.PERSISTENT)
                .setMessageId(event.getId().toString())
                .setType(event.getRoutingKey())
                .build();
    }
}
