package br.edu.insper.videoinsight.job;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class HealthControllerTest {
    @Test
    void reportsHealthy() {
        var response = new HealthController().health();

        assertEquals("job-service", response.get("service"));
        assertEquals("UP", response.get("status"));
    }
}
