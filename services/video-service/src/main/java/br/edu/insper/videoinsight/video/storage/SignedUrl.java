package br.edu.insper.videoinsight.video.storage;

import java.net.URI;
import java.time.Instant;
import java.util.Map;

/** Corresponde ao schema {@code SignedUrl} do contrato. */
public record SignedUrl(URI url, String method, Instant expiresAt, Map<String, String> headers) {
}
