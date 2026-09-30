package br.edu.insper.videoinsight.job.application;

import br.edu.insper.videoinsight.job.domain.Job;
import br.edu.insper.videoinsight.job.domain.JobAttempt;
import br.edu.insper.videoinsight.job.domain.JobAttemptRepository;
import br.edu.insper.videoinsight.job.domain.JobRepository;
import br.edu.insper.videoinsight.job.domain.JobResult;
import br.edu.insper.videoinsight.job.domain.JobResultRepository;
import br.edu.insper.videoinsight.job.domain.ProcessedEvent;
import br.edu.insper.videoinsight.job.domain.ProcessedEventRepository;
import br.edu.insper.videoinsight.job.messaging.EventEnvelope;
import br.edu.insper.videoinsight.job.messaging.ProcessingCompleted;
import br.edu.insper.videoinsight.job.messaging.ProcessingEventData;
import br.edu.insper.videoinsight.job.messaging.ProcessingFailed;
import br.edu.insper.videoinsight.job.messaging.ProcessingProgressed;
import br.edu.insper.videoinsight.job.messaging.ProcessingStarted;
import br.edu.insper.videoinsight.job.storage.ArtifactStorage;
import java.time.Clock;
import java.util.Optional;
import java.util.function.Consumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/**
 * Aplica ao job os eventos do Processing Service. É um consumidor idempotente: reentregas são descartadas pelo
 * {@code event_id} e eventos de tentativas antigas ou de jobs finalizados são ignorados.
 */
@Service
public class ProcessingEventHandler {
    private static final Logger log = LoggerFactory.getLogger(ProcessingEventHandler.class);

    private final JobRepository jobs;
    private final JobAttemptRepository attempts;
    private final JobResultRepository results;
    private final ProcessedEventRepository processedEvents;
    private final ArtifactStorage storage;
    private final JsonMapper mapper;
    private final Clock clock;

    public ProcessingEventHandler(
            JobRepository jobs,
            JobAttemptRepository attempts,
            JobResultRepository results,
            ProcessedEventRepository processedEvents,
            ArtifactStorage storage,
            JsonMapper mapper,
            Clock clock) {
        this.jobs = jobs;
        this.attempts = attempts;
        this.results = results;
        this.processedEvents = processedEvents;
        this.storage = storage;
        this.mapper = mapper;
        this.clock = clock;
    }

    @Transactional
    public void handle(EventEnvelope<? extends ProcessingEventData> event) {
        if (processedEvents.existsById(event.eventId())) {
            log.info("Evento {} já processado; reentrega ignorada", event.eventId());
            return;
        }
        processedEvents.save(new ProcessedEvent(event.eventId(), event.eventType(), clock.instant()));

        var data = event.data();
        var job = jobs.findById(data.jobId()).orElse(null);
        if (job == null || !job.acceptsEventsFor(data.attempt())) {
            log.info("Evento {} ignorado para o job {} (tentativa {})", event.eventType(), data.jobId(),
                    data.attempt());
            return;
        }

        var now = clock.instant();
        switch (data) {
            case ProcessingStarted started -> {
                job.start(now);
                updateAttempt(job, attempt -> attempt.started(now));
            }
            case ProcessingProgressed progressed -> job.progress(progressed.stage(), progressed.progressPercent(), now);
            case ProcessingCompleted completed -> complete(job, completed);
            case ProcessingFailed failed -> {
                job.fail(failed.stage(), failed.errorCode(), failed.errorMessage(), failed.retryable(), now);
                updateAttempt(job, attempt -> attempt.failed(
                        failed.stage(), failed.errorCode(), failed.errorMessage(), failed.retryable(), now));
            }
        }
    }

    private void complete(Job job, ProcessingCompleted completed) {
        var artifacts = completed.artifacts();
        var transcript = storage.readTranscript(artifacts.transcriptJsonKey());
        var summary = Optional.ofNullable(artifacts.summaryJsonKey()).map(storage::readSummary).orElse(null);
        var chapters = Optional.ofNullable(artifacts.chaptersJsonKey()).map(storage::readChapters).orElse(null);
        var now = clock.instant();

        results.save(new JobResult(
                job.getId(),
                mapper.writeValueAsString(transcript),
                summary,
                chapters == null ? null : mapper.writeValueAsString(chapters),
                mapper.writeValueAsString(completed.models()),
                artifacts.transcriptJsonKey(),
                artifacts.transcriptTxtKey(),
                artifacts.transcriptSrtKey(),
                now));
        job.complete(now);
        updateAttempt(job, attempt -> attempt.completed(now));
    }

    private void updateAttempt(Job job, Consumer<JobAttempt> update) {
        attempts.findByJobIdAndAttempt(job.getId(), job.getAttempt()).ifPresent(update);
    }
}
