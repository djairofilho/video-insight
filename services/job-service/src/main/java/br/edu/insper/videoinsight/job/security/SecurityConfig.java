package br.edu.insper.videoinsight.job.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import br.edu.insper.videoinsight.job.api.ErrorResponse;
import org.springframework.security.web.AuthenticationEntryPoint;
import tools.jackson.databind.json.JsonMapper;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {
    @Bean
    SecurityFilterChain apiSecurity(HttpSecurity http,
            @Value("${auth.enabled:false}") boolean enabled,
            @Value("${auth.issuer:}") String issuer,
            @Value("${auth.audience:}") String audience, JsonMapper mapper) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
        if (!enabled) {
            http.authorizeHttpRequests(requests -> requests.anyRequest().permitAll());
        } else {
            if (!issuer.startsWith("https://") || !issuer.endsWith("/") || audience.isBlank()) {
                throw new IllegalArgumentException("Configure AUTH_ISSUER (HTTPS, com / final) e AUTH_AUDIENCE.");
            }
            var decoder = NimbusJwtDecoder.withJwkSetUri(issuer + ".well-known/jwks.json").build();
            decoder.setJwtValidator(validator(issuer, audience));
            AuthenticationEntryPoint unauthorized = (request, response, exception) -> {
                response.setStatus(401);
                response.setHeader("WWW-Authenticate", "Bearer");
                response.setContentType("application/json");
                mapper.writeValue(response.getOutputStream(), ErrorResponse.of("UNAUTHORIZED", "Token ausente ou inválido."));
            };
            http.exceptionHandling(errors -> errors.authenticationEntryPoint(unauthorized));
            http.authorizeHttpRequests(requests -> requests
                    .requestMatchers("/health", "/actuator/health", "/actuator/health/**").permitAll()
                    .anyRequest().authenticated())
                    .oauth2ResourceServer(oauth -> oauth.authenticationEntryPoint(unauthorized).jwt(jwt -> jwt.decoder(decoder)));
        }
        return http.build();
    }
    static OAuth2TokenValidator<Jwt> validator(String issuer, String audience) {
        return new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(issuer),
                jwt -> jwt.getAudience().contains(audience) && jwt.getSubject() != null && !jwt.getSubject().isBlank()
                        ? OAuth2TokenValidatorResult.success()
                        : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token")));
    }
}
