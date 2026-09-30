package br.edu.insper.videoinsight.job.support;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

class CorrelationIdTest {
    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    void keepsValidUuidsAndReplacesAnythingElse() {
        var id = UUID.randomUUID();

        assertThat(CorrelationId.parseOrGenerate(id.toString())).isEqualTo(id);
        assertThat(CorrelationId.parseOrGenerate("abc")).isNotNull();
        assertThat(CorrelationId.parseOrGenerate(null)).isNotNull();
    }

    @Test
    void readsTheCurrentIdFromTheLoggingContext() {
        var id = UUID.randomUUID();
        MDC.put(CorrelationId.MDC_KEY, id.toString());

        assertThat(CorrelationId.current()).isEqualTo(id);
        MDC.clear();
        assertThat(CorrelationId.current()).isNotEqualTo(id);
    }
}
