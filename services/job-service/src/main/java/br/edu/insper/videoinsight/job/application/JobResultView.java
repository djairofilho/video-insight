package br.edu.insper.videoinsight.job.application;

import br.edu.insper.videoinsight.job.domain.Chapter;
import br.edu.insper.videoinsight.job.domain.ModelReference;
import br.edu.insper.videoinsight.job.domain.TranscriptSegment;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Corresponde ao schema {@code JobResult} do contrato. */
public record JobResultView(
        UUID jobId,
        UUID videoId,
        List<TranscriptSegment> transcript,
        String summary,
        List<Chapter> chapters,
        List<ModelReference> models,
        Instant completedAt) {
}
