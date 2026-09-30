package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

public enum Operation {
    TRANSCRIPTION,
    SUMMARY,
    CHAPTERS;

    @JsonValue
    public String value() {
        return name().toLowerCase();
    }

    @JsonCreator
    public static Operation from(String value) {
        return Arrays.stream(values())
                .filter(operation -> operation.value().equals(value))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Operação desconhecida: " + value));
    }
}
