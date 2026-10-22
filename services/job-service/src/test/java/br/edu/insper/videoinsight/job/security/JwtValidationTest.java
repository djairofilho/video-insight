package br.edu.insper.videoinsight.job.security;

import static org.assertj.core.api.Assertions.assertThat;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;

class JwtValidationTest {
    @Test
    void validatesIssuerAudienceExpiryAndSubject() {
        var validator = SecurityConfig.validator("https://example.auth0.com/", "api");
        assertThat(validator.validate(token("https://example.auth0.com/", "api", "alice", 300)).hasErrors()).isFalse();
        assertThat(validator.validate(token("https://other.auth0.com/", "api", "alice", 300)).hasErrors()).isTrue();
        assertThat(validator.validate(token("https://example.auth0.com/", "other", "alice", 300)).hasErrors()).isTrue();
        assertThat(validator.validate(token("https://example.auth0.com/", "api", "alice", -300)).hasErrors()).isTrue();
        assertThat(validator.validate(token("https://example.auth0.com/", "api", "", 300)).hasErrors()).isTrue();
    }

    private Jwt token(String issuer, String audience, String subject, long seconds) {
        return Jwt.withTokenValue("test").header("alg", "RS256").issuer(issuer)
                .audience(List.of(audience)).subject(subject).issuedAt(Instant.now().minusSeconds(600))
                .expiresAt(Instant.now().plusSeconds(seconds)).build();
    }
}
