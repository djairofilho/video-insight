package br.edu.insper.videoinsight.job;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.hamcrest.Matchers.containsString;
import org.junit.jupiter.api.Test;

class MetricsTest extends IntegrationTest {
    @org.springframework.beans.factory.annotation.Autowired
    br.edu.insper.videoinsight.job.monitoring.JobMetrics metrics;

    @Test
    void exposesApplicationMetricsOnlyToInternalClients() throws Exception {
        metrics.refresh();
        mockMvc.perform(get("/actuator/prometheus"))
                .andExpect(status().isOk()).andExpect(content().string(containsString("jvm_memory_used_bytes")))
                .andExpect(content().string(containsString("video_insight_job_metrics_available 1")));
        mockMvc.perform(get("/actuator/prometheus").with(request -> {
            request.setRemoteAddr("203.0.113.1");
            return request;
        })).andExpect(status().isForbidden());
    }
}
