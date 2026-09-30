package br.edu.insper.videoinsight.job.messaging;

import java.util.List;

public final class EventTypes {
    public static final String PROCESSING_REQUESTED = "processing.requested";
    public static final String PROCESSING_STARTED = "processing.started";
    public static final String PROCESSING_PROGRESSED = "processing.progressed";
    public static final String PROCESSING_COMPLETED = "processing.completed";
    public static final String PROCESSING_FAILED = "processing.failed";

    /** Eventos publicados pelo Processing Service e consumidos pelo Job Service. */
    public static final List<String> CONSUMED = List.of(
            PROCESSING_STARTED, PROCESSING_PROGRESSED, PROCESSING_COMPLETED, PROCESSING_FAILED);

    private EventTypes() {
    }
}
