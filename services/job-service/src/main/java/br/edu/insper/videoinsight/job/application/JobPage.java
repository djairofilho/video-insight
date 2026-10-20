package br.edu.insper.videoinsight.job.application;

import br.edu.insper.videoinsight.job.domain.Job;
import java.util.List;

public record JobPage(List<Job> items, String nextCursor) {
}
