package br.edu.insper.videoinsight.job.messaging;

import java.util.UUID;

/** Dados dos eventos publicados pelo Processing Service. */
public sealed interface ProcessingEventData
        permits ProcessingStarted, ProcessingProgressed, ProcessingCompleted, ProcessingFailed {
    UUID jobId();

    UUID videoId();

    Integer attempt();
}
