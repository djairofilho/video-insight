package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record TranscriptSegment(double startSeconds, double endSeconds, String text) {
}
