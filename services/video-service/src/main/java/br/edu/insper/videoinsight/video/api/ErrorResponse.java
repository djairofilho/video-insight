package br.edu.insper.videoinsight.video.api;

import br.edu.insper.videoinsight.video.support.CorrelationId;
import java.util.UUID;

/** Corresponde ao schema {@code Error} do contrato. */
public record ErrorResponse(String code, String message, UUID correlationId) {
    public static ErrorResponse of(String code, String message) {
        return new ErrorResponse(code, message, CorrelationId.current());
    }
}
