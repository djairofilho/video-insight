package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import java.util.ArrayList;
import java.util.List;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarable;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Declara a topologia compartilhada com o Processing Service.
 *
 * <p>A fila de solicitações e sua DLX pertencem ao Processing Service e são declaradas com os mesmos argumentos
 * usados por ele (DLX topic, sem routing key, DLQ ligada com {@code #}); caso contrário o RabbitMQ recusa a
 * declaração de quem chegar depois. Declarar aqui evita perder solicitações antes de o worker se conectar. A fila de
 * eventos do Job Service usa uma DLX própria, para que suas mensagens rejeitadas não caiam na DLQ do worker.
 */
@Configuration
public class RabbitTopologyConfig {
    @Bean
    Declarables messagingTopology(JobServiceProperties properties) {
        var messaging = properties.messaging();
        var events = new TopicExchange(messaging.exchange(), true, false);
        List<Declarable> declarables = new ArrayList<>();
        declarables.add(events);

        // Fila de eventos consumida pelo Job Service.
        var jobDeadLetters = new DirectExchange(messaging.deadLetterExchange(), true, false);
        var eventsDeadLetterQueue = QueueBuilder.durable(messaging.deadLetterQueue(messaging.eventsQueue())).build();
        var eventsQueue = QueueBuilder.durable(messaging.eventsQueue())
                .deadLetterExchange(jobDeadLetters.getName())
                .deadLetterRoutingKey(eventsDeadLetterQueue.getName())
                .build();
        declarables.addAll(List.of(jobDeadLetters, eventsDeadLetterQueue, eventsQueue,
                BindingBuilder.bind(eventsDeadLetterQueue).to(jobDeadLetters).with(eventsDeadLetterQueue.getName())));
        for (var eventType : EventTypes.CONSUMED) {
            declarables.add(BindingBuilder.bind(eventsQueue).to(events).with(eventType));
        }

        // Fila de solicitações do Processing Service, com os argumentos definidos por ele.
        var requestDeadLetters = new TopicExchange(messaging.requestsDeadLetterExchange(), true, false);
        var requestsDeadLetterQueue =
                QueueBuilder.durable(messaging.deadLetterQueue(messaging.requestsQueue())).build();
        var requestsQueue = QueueBuilder.durable(messaging.requestsQueue())
                .deadLetterExchange(requestDeadLetters.getName())
                .build();
        declarables.addAll(List.of(requestDeadLetters, requestsDeadLetterQueue, requestsQueue,
                BindingBuilder.bind(requestsDeadLetterQueue).to(requestDeadLetters).with("#"),
                BindingBuilder.bind(requestsQueue).to(events).with(EventTypes.PROCESSING_REQUESTED)));

        return new Declarables(declarables);
    }
}
