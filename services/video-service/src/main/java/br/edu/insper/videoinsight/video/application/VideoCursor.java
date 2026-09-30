package br.edu.insper.videoinsight.video.application;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.UUID;

/** Cursor opaco da listagem: posição {@code (createdAt, id)} do último vídeo da página anterior. */
record VideoCursor(Instant createdAt, UUID id) {
    private static final String SEPARATOR = "|";

    String encode() {
        var raw = createdAt + SEPARATOR + id;
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    static VideoCursor decode(String value) {
        try {
            var raw = new String(Base64.getUrlDecoder().decode(value), StandardCharsets.UTF_8);
            var separator = raw.indexOf(SEPARATOR);
            return new VideoCursor(Instant.parse(raw.substring(0, separator)), UUID.fromString(raw.substring(separator + 1)));
        } catch (RuntimeException exception) {
            throw ApiException.badRequest("Cursor inválido.");
        }
    }
}
