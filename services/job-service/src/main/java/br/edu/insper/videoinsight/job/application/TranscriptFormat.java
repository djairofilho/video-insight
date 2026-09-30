package br.edu.insper.videoinsight.job.application;

import br.edu.insper.videoinsight.job.domain.JobResult;
import java.util.Arrays;
import java.util.Optional;
import java.util.function.Function;

public enum TranscriptFormat {
    TXT(JobResult::getTranscriptTxtKey),
    JSON(JobResult::getTranscriptJsonKey),
    SRT(JobResult::getTranscriptSrtKey);

    private final Function<JobResult, String> artifactKey;

    TranscriptFormat(Function<JobResult, String> artifactKey) {
        this.artifactKey = artifactKey;
    }

    public static Optional<TranscriptFormat> from(String value) {
        return Arrays.stream(values()).filter(format -> format.extension().equals(value)).findFirst();
    }

    public String extension() {
        return name().toLowerCase();
    }

    public Optional<String> artifactKey(JobResult result) {
        return Optional.ofNullable(artifactKey.apply(result));
    }
}
