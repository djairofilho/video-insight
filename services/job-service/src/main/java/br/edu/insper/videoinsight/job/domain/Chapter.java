package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** Os {@code blocks} gerados pelo Processing Service ainda não fazem parte do contrato e são ignorados. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Chapter(String title, double startSeconds, double endSeconds) {
}
