package br.edu.insper.videoinsight.job.security;

import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

/** A identidade vem exclusivamente de um JWT validado, nunca de headers enviados pelo cliente. */
public final class CurrentUser {
    private CurrentUser() {}

    public static String subject() {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication instanceof JwtAuthenticationToken jwt) {
            return jwt.getToken().getSubject();
        }
        return "local-development";
    }
}
