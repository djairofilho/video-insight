package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.domain.Job;
import br.edu.insper.videoinsight.job.domain.OutboxEvent;
import br.edu.insper.videoinsight.job.domain.OutboxEventRepository;
import br.edu.insper.videoinsight.job.support.CorrelationId;
import java.time.Clock;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/** Grava eventos no outbox dentro da mesma transação que altera o job. */
@Component
public class OutboxWriter {
    private final OutboxEventRepository outbox;
    private final JsonMapper mapper;
    private final Clock clock;

    public OutboxWriter(OutboxEventRepository outbox, JsonMapper mapper, Clock clock) {
        this.outbox = outbox;
        this.mapper = mapper;
        this.clock = clock;
    }

    @Transactional(propagation = Propagation.MANDATORY)
    public void enqueueProcessingRequested(Job job) {
        var data = new ProcessingRequested(
                job.getId(), job.getVideoId(), job.getStorageKey(), job.getOperations(), job.getAttempt());
        var event = EventEnvelope.create(
                EventTypes.PROCESSING_REQUESTED, CorrelationId.current(), data, clock.instant());
        outbox.save(new OutboxEvent(
                event.eventId(), event.eventType(), mapper.writeValueAsString(event), event.occurredAt()));
    }
}
