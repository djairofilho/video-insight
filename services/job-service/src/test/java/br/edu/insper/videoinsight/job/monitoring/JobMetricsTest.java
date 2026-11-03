package br.edu.insper.videoinsight.job.monitoring;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

class JobMetricsTest {
    @Test
    @SuppressWarnings("unchecked")
    void exposesQueueAgeAndCompletionsAndMarksCollectionFailure() throws Exception {
        var jdbc = mock(JdbcTemplate.class);
        var registry = new SimpleMeterRegistry();
        var now = Instant.parse("2026-11-03T00:00:00Z");
        var metrics = new JobMetrics(jdbc, registry, Clock.fixed(now, ZoneOffset.UTC));
        var row = mock(ResultSet.class);
        when(row.getDouble("queued")).thenReturn(3.0);
        when(row.getDouble("completed")).thenReturn(7.0);
        when(row.getTimestamp("oldest")).thenReturn(Timestamp.from(now.minusSeconds(90)));
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), any(Object[].class)))
                .thenAnswer(invocation -> ((RowMapper<?>) invocation.getArgument(1)).mapRow(row, 0));
        metrics.refresh();
        assertThat(registry.get("video_insight_jobs_queued").gauge().value()).isEqualTo(3);
        assertThat(registry.get("video_insight_oldest_queued_job_seconds").gauge().value()).isEqualTo(90);
        assertThat(registry.get("video_insight_jobs_completed_last_hour").gauge().value()).isEqualTo(7);
        assertThat(registry.get("video_insight_job_metrics_available").gauge().value()).isEqualTo(1);
        when(jdbc.queryForObject(anyString(), any(RowMapper.class), any(Object[].class)))
                .thenThrow(new IllegalStateException("indisponível"));
        metrics.refresh();
        assertThat(registry.get("video_insight_job_metrics_available").gauge().value()).isZero();
        assertThat(registry.get("video_insight_jobs_queued").gauge().value()).isEqualTo(3);
    }
}
