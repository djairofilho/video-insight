package br.edu.insper.videoinsight.video.domain;

import com.fasterxml.jackson.annotation.JsonValue;

public enum UploadStatus {
    PENDING,
    UPLOADING,
    READY,
    FAILED;

    @JsonValue
    public String value() {
        return name().toLowerCase();
    }
}
