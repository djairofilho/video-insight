package br.edu.insper.videoinsight.job.security;

import static org.assertj.core.api.Assertions.assertThat;
import org.junit.jupiter.api.Test;

class MetricsAccessTest {
    @Test
    void allowsLoopbackAndOnlyExplicitlyConfiguredNetworks() {
        assertThat(SecurityConfig.metricsAllowed("localhost", "")).isTrue();
        assertThat(SecurityConfig.metricsAllowed("203.0.113.1", "")).isFalse();
        assertThat(SecurityConfig.metricsAllowed("203.0.113.1", "203.0.113.0/24")).isTrue();
        assertThat(SecurityConfig.metricsAllowed("198.51.100.1", "203.0.113.0/24")).isFalse();
        assertThat(SecurityConfig.metricsAllowed("203.0.113.1", "invalid-network")).isFalse();
    }
}
