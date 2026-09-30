package br.edu.insper.videoinsight.job.domain;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobResultRepository extends JpaRepository<JobResult, UUID> {
}
