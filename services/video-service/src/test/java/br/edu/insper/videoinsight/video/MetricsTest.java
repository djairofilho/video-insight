package br.edu.insper.videoinsight.video;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.hamcrest.Matchers.containsString;
import org.junit.jupiter.api.Test;

class MetricsTest extends IntegrationTest {
    @Test
    void exposesApplicationMetricsOnlyToInternalClients() throws Exception {
        mockMvc.perform(get("/actuator/prometheus"))
                .andExpect(status().isOk()).andExpect(content().string(containsString("jvm_memory_used_bytes")));
        mockMvc.perform(get("/actuator/prometheus").with(request -> {
            request.setRemoteAddr("203.0.113.1");
            return request;
        })).andExpect(status().isForbidden());
    }
}
