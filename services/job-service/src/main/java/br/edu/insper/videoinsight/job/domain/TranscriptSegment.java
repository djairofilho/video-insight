package br.edu.insper.videoinsight.job.domain;

public record TranscriptSegment(double startSeconds, double endSeconds, String text) {
}
