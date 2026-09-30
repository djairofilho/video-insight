package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.application.ProcessingEventHandler;
import br.edu.insper.videoinsight.job.support.CorrelationId;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class ProcessingEventListener {
    private static final Logger log = LoggerFactory.getLogger(ProcessingEventListener.class);

    private final EventParser parser;
    private final ProcessingEventHandler handler;

    public ProcessingEventListener(EventParser parser, ProcessingEventHandler handler) {
        this.parser = parser;
        this.handler = handler;
    }

    /** Mensagens inválidas vão direto para a DLQ; falhas temporárias são repetidas pelo container. */
    @RabbitListener(queues = "${job-service.messaging.events-queue}")
    public void onMessage(Message message) {
        EventEnvelope<ProcessingEventData> event;
        try {
            event = parser.parse(message.getBody());
        } catch (InvalidEventException exception) {
            log.warn("Evento rejeitado e enviado para a DLQ: {}", exception.getMessage());
            throw new AmqpRejectAndDontRequeueException(exception.getMessage(), exception);
        }

        var correlationId = event.correlationId() == null ? CorrelationId.current() : event.correlationId();
        MDC.put(CorrelationId.MDC_KEY, correlationId.toString());
        try {
            handler.handle(event);
        } finally {
            MDC.remove(CorrelationId.MDC_KEY);
        }
    }
}
