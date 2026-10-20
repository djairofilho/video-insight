package br.edu.insper.videoinsight.job.api;

import br.edu.insper.videoinsight.job.application.JobPage;
import java.util.List;

/** Corresponde ao schema {@code JobPage} do contrato. */
public record JobPageResponse(List<JobResponse> items, String nextCursor) {
    public static JobPageResponse from(JobPage page) {
        return new JobPageResponse(page.items().stream().map(JobResponse::from).toList(), page.nextCursor());
    }
}
