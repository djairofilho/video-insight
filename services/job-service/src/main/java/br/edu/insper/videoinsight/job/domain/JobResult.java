package br.edu.insper.videoinsight.job.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** Resultado estruturado de um job concluído; listas são guardadas como JSON. */
@Entity
@Table(name = "job_results")
public class JobResult {
    @Id
    private UUID jobId;

    @Column(nullable = false)
    private String transcript;

    private String summary;

    private String chapters;

    @Column(nullable = false)
    private String models;

    @Column(nullable = false)
    private String transcriptJsonKey;

    private String transcriptTxtKey;

    private String transcriptSrtKey;

    @Column(nullable = false)
    private Instant completedAt;

    protected JobResult() {
    }

    public JobResult(
            UUID jobId,
            String transcript,
            String summary,
            String chapters,
            String models,
            String transcriptJsonKey,
            String transcriptTxtKey,
            String transcriptSrtKey,
            Instant completedAt) {
        this.jobId = jobId;
        this.transcript = transcript;
        this.summary = summary;
        this.chapters = chapters;
        this.models = models;
        this.transcriptJsonKey = transcriptJsonKey;
        this.transcriptTxtKey = transcriptTxtKey;
        this.transcriptSrtKey = transcriptSrtKey;
        this.completedAt = completedAt;
    }

    public UUID getJobId() {
        return jobId;
    }

    public String getTranscript() {
        return transcript;
    }

    public String getSummary() {
        return summary;
    }

    public String getChapters() {
        return chapters;
    }

    public String getModels() {
        return models;
    }

    public String getTranscriptJsonKey() {
        return transcriptJsonKey;
    }

    public String getTranscriptTxtKey() {
        return transcriptTxtKey;
    }

    public String getTranscriptSrtKey() {
        return transcriptSrtKey;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }
}
