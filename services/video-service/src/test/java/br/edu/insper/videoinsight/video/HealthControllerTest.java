package br.edu.insper.videoinsight.video;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class HealthControllerTest {
    @Test
    void reportsHealthy() {
        var response = new HealthController().health();

        assertEquals("video-service", response.get("service"));
        assertEquals("UP", response.get("status"));
    }
}
