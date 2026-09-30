package br.edu.insper.videoinsight.job.storage;

import java.net.URI;
import java.time.Instant;

public record PresignedUrl(URI url, Instant expiresAt) {
}
