package br.edu.insper.videoinsight.job.messaging;

import java.time.Instant;
import java.util.UUID;

/** Envelope comum a todos os eventos de {@code contracts/events}. */
public record EventEnvelope<T>(
        UUID eventId,
        String eventType,
        int eventVersion,
        Instant occurredAt,
        UUID correlationId,
        T data) {

    public static final int VERSION = 1;

    public static <T> EventEnvelope<T> create(String eventType, UUID correlationId, T data, Instant now) {
        return new EventEnvelope<>(UUID.randomUUID(), eventType, VERSION, now, correlationId, data);
    }
}
