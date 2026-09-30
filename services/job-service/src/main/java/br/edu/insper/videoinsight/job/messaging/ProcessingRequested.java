package br.edu.insper.videoinsight.job.messaging;

import br.edu.insper.videoinsight.job.domain.Operation;
import java.util.List;
import java.util.UUID;

public record ProcessingRequested(
        UUID jobId,
        UUID videoId,
        String storageKey,
        List<Operation> operations,
        int attempt) {
}
