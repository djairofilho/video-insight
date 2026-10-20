package br.edu.insper.videoinsight.job.application;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;

/** Cursor opaco da listagem: posição {@code (createdAt, id)} do último job da página anterior. */
record JobCursor(Instant createdAt, UUID id) {
    private static final String SEPARATOR = "|";

    String encode() {
        var raw = createdAt + SEPARATOR + id;
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    static JobCursor decode(String value) {
        try {
            var raw = new String(Base64.getUrlDecoder().decode(value), StandardCharsets.UTF_8);
            var separator = raw.indexOf(SEPARATOR);
            return new JobCursor(Instant.parse(raw.substring(0, separator)), UUID.fromString(raw.substring(separator + 1)));
        } catch (RuntimeException exception) {
            throw ApiException.badRequest("Cursor inválido.");
        }
    }
}
