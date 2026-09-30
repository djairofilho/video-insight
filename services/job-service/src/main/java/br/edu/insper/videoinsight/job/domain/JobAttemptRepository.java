package br.edu.insper.videoinsight.job.domain;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobAttemptRepository extends JpaRepository<JobAttempt, UUID> {
    Optional<JobAttempt> findByJobIdAndAttempt(UUID jobId, int attempt);

    List<JobAttempt> findByJobIdOrderByAttempt(UUID jobId);
}
