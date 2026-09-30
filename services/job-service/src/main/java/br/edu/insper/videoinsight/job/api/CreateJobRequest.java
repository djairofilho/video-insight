package br.edu.insper.videoinsight.job.api;

import br.edu.insper.videoinsight.job.domain.Operation;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public record CreateJobRequest(@NotEmpty List<@NotNull Operation> operations) {
}
