package br.edu.insper.videoinsight.video.support;

import java.util.UUID;
import org.slf4j.MDC;

/** Identificador que acompanha uma requisição ou mensagem entre os serviços. */
public final class CorrelationId {
    public static final String HEADER = "X-Correlation-Id";
    public static final String MDC_KEY = "correlationId";

    private CorrelationId() {
    }

    /** Retorna o identificador do contexto atual ou gera um novo. */
    public static UUID current() {
        var value = MDC.get(MDC_KEY);
        return value == null ? UUID.randomUUID() : UUID.fromString(value);
    }

    /** Aceita somente UUIDs, conforme os contratos; qualquer outro valor é substituído. */
    public static UUID parseOrGenerate(String value) {
        if (value != null) {
            try {
                return UUID.fromString(value);
            } catch (IllegalArgumentException ignored) {
                // Valor inválido: gera um novo identificador abaixo.
            }
        }
        return UUID.randomUUID();
    }
}
