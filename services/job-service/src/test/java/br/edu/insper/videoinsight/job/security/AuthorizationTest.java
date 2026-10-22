package br.edu.insper.videoinsight.job.security;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import br.edu.insper.videoinsight.job.IntegrationTest;
import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;
import org.springframework.http.MediaType;

@TestPropertySource(properties = {"auth.enabled=true", "auth.issuer=https://example.auth0.com/", "auth.audience=https://video-insight-api"})
class AuthorizationTest extends IntegrationTest {
    @Test
    void rejectsMissingAndMalformedTokensButAllowsHealth() throws Exception {
        mockMvc.perform(get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.correlation_id").isNotEmpty());
        mockMvc.perform(get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
                .header("Authorization", "Bearer malformed")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.correlation_id").isNotEmpty());
        mockMvc.perform(get("/health")).andExpect(status().isOk());
    }

    @Test
    void isolatesJobsAndScopesIdempotencyKeysPerUser() throws Exception {
        var videoId = java.util.UUID.randomUUID();
        videoIsReady(videoId);
        String aliceId = null;
        for (var subject : new String[]{"alice", "bob"}) {
            var response = mockMvc.perform(post("/api/v1/videos/" + videoId + "/jobs")
                    .with(jwt().jwt(token -> token.subject(subject)))
                    .header("Idempotency-Key", "same-key-different-users")
                    .contentType(MediaType.APPLICATION_JSON).content("{\"operations\":[\"transcription\"]}"))
                    .andExpect(status().isAccepted()).andReturn().getResponse();
            var id = mapper.readTree(response.getContentAsString()).get("id").stringValue();
            if (aliceId == null) aliceId = id;
            else org.assertj.core.api.Assertions.assertThat(id).isNotEqualTo(aliceId);
        }
        mockMvc.perform(get("/api/v1/videos/" + videoId + "/jobs")
                .with(jwt().jwt(token -> token.subject("charlie"))))
                .andExpect(jsonPath("$.items.length()").value(0));
        for (var path : new String[]{"", "/result", "/transcript?format=txt"}) {
            mockMvc.perform(get("/api/v1/jobs/" + aliceId + path).with(jwt().jwt(token -> token.subject("bob"))))
                    .andExpect(status().isNotFound());
        }
        for (var operation : new String[]{"cancel", "retry"}) {
            mockMvc.perform(post("/api/v1/jobs/" + aliceId + "/" + operation)
                    .with(jwt().jwt(token -> token.subject("bob"))))
                    .andExpect(status().isNotFound());
        }
    }
}
