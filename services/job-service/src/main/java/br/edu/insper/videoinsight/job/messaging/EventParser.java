package br.edu.insper.videoinsight.job.messaging;

import jakarta.validation.Validator;
import java.time.Instant;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Converte e valida os eventos recebidos do Processing Service. */
@Component
public class EventParser {
    private final JsonMapper mapper;
    private final Validator validator;

    public EventParser(JsonMapper mapper, Validator validator) {
        this.mapper = mapper;
        this.validator = validator;
    }

    public EventEnvelope<ProcessingEventData> parse(byte[] body) {
        RawEnvelope raw;
        ProcessingEventData data;
        try {
            raw = mapper.readValue(body, RawEnvelope.class);
            if (raw.eventId() == null || raw.eventType() == null || raw.data() == null) {
                throw new InvalidEventException("Evento sem event_id, event_type ou data.");
            }
            data = mapper.treeToValue(raw.data(), dataType(raw.eventType()));
        } catch (JacksonException exception) {
            throw new InvalidEventException("Evento com JSON inválido: " + exception.getOriginalMessage(), exception);
        }

        var violations = validator.validate(data);
        if (!violations.isEmpty()) {
            var details = violations.stream()
                    .map(violation -> violation.getPropertyPath() + " " + violation.getMessage())
                    .sorted()
                    .collect(Collectors.joining(", "));
            throw new InvalidEventException("Evento " + raw.eventType() + " inválido: " + details);
        }

        var version = raw.eventVersion() == null ? EventEnvelope.VERSION : raw.eventVersion();
        return new EventEnvelope<>(raw.eventId(), raw.eventType(), version, raw.occurredAt(), raw.correlationId(), data);
    }

    private static Class<? extends ProcessingEventData> dataType(String eventType) {
        return switch (eventType) {
            case EventTypes.PROCESSING_STARTED -> ProcessingStarted.class;
            case EventTypes.PROCESSING_PROGRESSED -> ProcessingProgressed.class;
            case EventTypes.PROCESSING_COMPLETED -> ProcessingCompleted.class;
            case EventTypes.PROCESSING_FAILED -> ProcessingFailed.class;
            default -> throw new InvalidEventException("Tipo de evento não suportado: " + eventType);
        };
    }

    private record RawEnvelope(
            UUID eventId,
            String eventType,
            Integer eventVersion,
            Instant occurredAt,
            UUID correlationId,
            JsonNode data) {
    }
}
