package br.edu.insper.videoinsight.job.domain;

import com.fasterxml.jackson.annotation.JsonValue;

public enum JobStatus {
    QUEUED,
    PROCESSING,
    COMPLETED,
    FAILED,
    CANCELLED;

    @JsonValue
    public String value() {
        return name().toLowerCase();
    }

    public boolean isTerminal() {
        return this == COMPLETED || this == FAILED || this == CANCELLED;
    }
}
