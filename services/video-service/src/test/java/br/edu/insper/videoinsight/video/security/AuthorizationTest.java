package br.edu.insper.videoinsight.video.security;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import br.edu.insper.videoinsight.video.IntegrationTest;
import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;
import org.springframework.http.MediaType;

@TestPropertySource(properties = {"auth.enabled=true", "auth.issuer=https://example.auth0.com/", "auth.audience=https://video-insight-api"})
class AuthorizationTest extends IntegrationTest {
    @Test
    void rejectsMissingAndMalformedTokensButAllowsHealth() throws Exception {
        mockMvc.perform(get("/api/v1/videos")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.correlation_id").isNotEmpty());
        mockMvc.perform(get("/api/v1/videos")
                .header("Authorization", "Bearer malformed")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.correlation_id").isNotEmpty());
        mockMvc.perform(get("/health")).andExpect(status().isOk());
    }

    @Test
    void isolatesListsPaginationAndEveryVideoOperation() throws Exception {
        var response = mockMvc.perform(post("/api/v1/videos")
                .with(jwt().jwt(token -> token.subject("alice")))
                .contentType(MediaType.APPLICATION_JSON)
                .content(videoBody("aula.mp4", "video/mp4", SIZE)))
                .andExpect(status().isCreated()).andReturn().getResponse();
        var id = mapper.readTree(response.getContentAsString()).get("id").stringValue();
        mockMvc.perform(get("/api/v1/videos").with(jwt().jwt(token -> token.subject("bob"))))
                .andExpect(jsonPath("$.items.length()").value(0));
        mockMvc.perform(get("/api/v1/videos/" + id).with(jwt().jwt(token -> token.subject("alice"))))
                .andExpect(status().isOk());
        mockMvc.perform(get("/api/v1/videos/" + id).with(jwt().jwt(token -> token.subject("bob"))))
                .andExpect(status().isNotFound());
        mockMvc.perform(delete("/api/v1/videos/" + id).with(jwt().jwt(token -> token.subject("bob"))))
                .andExpect(status().isNotFound());
        for (var operation : new String[]{"upload-url", "playback-url", "upload-complete"}) {
            mockMvc.perform(post("/api/v1/videos/" + id + "/" + operation)
                    .with(jwt().jwt(token -> token.subject("bob")))
                    .contentType(MediaType.APPLICATION_JSON).content("{\"duration_seconds\":10}"))
                    .andExpect(status().isNotFound());
        }
    }
}
