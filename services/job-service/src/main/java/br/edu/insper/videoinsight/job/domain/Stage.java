package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

public enum Stage {
    DOWNLOADING,
    EXTRACTING_AUDIO,
    TRANSCRIBING,
    SUMMARIZING,
    CREATING_CHAPTERS,
    UPLOADING_ARTIFACTS;

    @JsonValue
    public String value() {
        return name().toLowerCase();
    }

    @JsonCreator
    public static Stage from(String value) {
        return Arrays.stream(values())
                .filter(stage -> stage.value().equals(value))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Etapa desconhecida: " + value));
    }
}
