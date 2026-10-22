package br.edu.insper.videoinsight.job.domain;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Limit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface JobRepository extends JpaRepository<Job, UUID> {
    Optional<Job> findByIdempotencyKey(String idempotencyKey);

    List<Job> findByVideoIdOrderByCreatedAtDescIdDesc(UUID videoId, Limit limit);

    /** Página seguinte ao cursor {@code (createdAt, id)}, na mesma ordem da primeira página. */
    @Query("""
            select j from Job j
            where j.videoId = :videoId
              and (j.createdAt < :createdAt or (j.createdAt = :createdAt and j.id < :id))
            order by j.createdAt desc, j.id desc
            """)
    List<Job> findPageByVideoAfter(UUID videoId, Instant createdAt, UUID id, Limit limit);
    Optional<Job> findByOwnerIdAndIdempotencyKey(String ownerId, String idempotencyKey);

    List<Job> findByOwnerIdAndVideoIdOrderByCreatedAtDescIdDesc(String ownerId, UUID videoId, Limit limit);

    @Query("""
            select j from Job j where j.ownerId = :ownerId and j.videoId = :videoId
            and (j.createdAt < :createdAt or (j.createdAt = :createdAt and j.id < :id))
            order by j.createdAt desc, j.id desc
            """)
    List<Job> findOwnedPageByVideoAfter(String ownerId, UUID videoId, Instant createdAt, UUID id, Limit limit);
}
