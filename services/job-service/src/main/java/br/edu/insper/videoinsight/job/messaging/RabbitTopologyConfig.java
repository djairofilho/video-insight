package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import java.util.ArrayList;
import java.util.List;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarable;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Declara a topologia descrita em {@code contracts/README.md}: exchange topic de eventos, filas com DLQ e a fila de
 * solicitações do Processing Service, para que nenhuma solicitação se perca antes de o worker se conectar.
 */
@Configuration
public class RabbitTopologyConfig {
    @Bean
    Declarables messagingTopology(JobServiceProperties properties) {
        var messaging = properties.messaging();
        var events = new TopicExchange(messaging.exchange(), true, false);
        var deadLetters = new DirectExchange(messaging.deadLetterExchange(), true, false);

        List<Declarable> declarables = new ArrayList<>(List.of(events, deadLetters));

        var eventsQueue = queueWithDeadLetter(messaging, messaging.eventsQueue(), deadLetters, declarables);
        for (var eventType : EventTypes.CONSUMED) {
            declarables.add(BindingBuilder.bind(eventsQueue).to(events).with(eventType));
        }

        var requestsQueue = queueWithDeadLetter(messaging, messaging.requestsQueue(), deadLetters, declarables);
        declarables.add(BindingBuilder.bind(requestsQueue).to(events).with(EventTypes.PROCESSING_REQUESTED));

        return new Declarables(declarables);
    }

    private static Queue queueWithDeadLetter(
            JobServiceProperties.Messaging messaging,
            String name,
            DirectExchange deadLetters,
            List<Declarable> declarables) {
        var deadLetterQueue = QueueBuilder.durable(messaging.deadLetterQueue(name)).build();
        var queue = QueueBuilder.durable(name)
                .deadLetterExchange(deadLetters.getName())
                .deadLetterRoutingKey(deadLetterQueue.getName())
                .build();
        declarables.add(queue);
        declarables.add(deadLetterQueue);
        declarables.add(BindingBuilder.bind(deadLetterQueue).to(deadLetters).with(deadLetterQueue.getName()));
        return queue;
    }
}
