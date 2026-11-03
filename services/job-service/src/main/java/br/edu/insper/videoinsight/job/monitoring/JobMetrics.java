package br.edu.insper.videoinsight.job.monitoring;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.concurrent.atomic.AtomicReference;
import java.time.Clock;
import java.time.Duration;
import java.sql.Timestamp;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Agregados operacionais privados; não incluem usuários nem identificadores de jobs. */
@Component
public class JobMetrics {
    private static final Logger LOG = LoggerFactory.getLogger(JobMetrics.class);
    private final JdbcTemplate jdbc;
    private final Clock clock;
    private final AtomicReference<Snapshot> snapshot = new AtomicReference<>(new Snapshot(0, 0, 0, 0));

    public JobMetrics(JdbcTemplate jdbc, MeterRegistry registry, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
        Gauge.builder("video_insight_jobs_queued", snapshot, state -> state.get().queued()).register(registry);
        Gauge.builder("video_insight_oldest_queued_job_seconds", snapshot, state -> state.get().oldest()).register(registry);
        Gauge.builder("video_insight_jobs_completed_last_hour", snapshot, state -> state.get().completed()).register(registry);
        Gauge.builder("video_insight_job_metrics_available", snapshot, state -> state.get().available()).register(registry);
    }

    @Scheduled(fixedDelayString = "${job-service.metrics.refresh-ms:15000}", initialDelay = 1000)
    public void refresh() {
        try {
            Snapshot next = jdbc.queryForObject("""
                    select
                      (select count(*) from jobs where status = 'QUEUED') as queued,
                      (select min(updated_at) from jobs where status = 'QUEUED') as oldest,
                      (select count(*) from jobs where status = 'COMPLETED'
                       and updated_at >= ?) as completed
                    """, (rs, row) -> {
                        Timestamp oldest = rs.getTimestamp("oldest");
                        double wait = oldest == null ? 0 : Math.max(0, Duration.between(oldest.toInstant(), clock.instant()).toMillis() / 1000.0);
                        return new Snapshot(rs.getDouble("queued"), wait, rs.getDouble("completed"), 1);
                    }, Timestamp.from(clock.instant().minusSeconds(3600)));
            if (next != null) snapshot.set(next);
        } catch (RuntimeException error) {
            snapshot.updateAndGet(old -> new Snapshot(old.queued(), old.oldest(), old.completed(), 0));
            LOG.warn("Coleta dos agregados operacionais indisponível ({})", error.getClass().getSimpleName());
        }
    }

    private record Snapshot(double queued, double oldest, double completed, double available) {}
}
