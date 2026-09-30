package br.edu.insper.videoinsight.job.video;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.UUID;

/** Campos do {@code Video} do Video Service que o Job Service usa. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record VideoSummary(
        @JsonProperty("id") UUID id,
        @JsonProperty("upload_status") String uploadStatus) {

    public boolean isReady() {
        return "ready".equals(uploadStatus);
    }
}
