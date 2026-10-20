package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import tools.jackson.databind.JsonNode;

/**
 * Os {@code blocks} gerados pelo Processing Service são repassados sem interpretação; o formato de cada tipo está no
 * README do Processing Service.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Chapter(String title, double startSeconds, double endSeconds, List<JsonNode> blocks) {
    public Chapter(String title, double startSeconds, double endSeconds) {
        this(title, startSeconds, endSeconds, null);
    }
}
