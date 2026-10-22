package br.edu.insper.videoinsight.video.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Limit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface VideoRepository extends JpaRepository<Video, UUID> {
    List<Video> findAllByOrderByCreatedAtDescIdDesc(Limit limit);

    /** Página seguinte ao cursor {@code (createdAt, id)}, na mesma ordem da primeira página. */
    @Query("""
            select v from Video v
            where v.createdAt < :createdAt or (v.createdAt = :createdAt and v.id < :id)
            order by v.createdAt desc, v.id desc
            """)
    List<Video> findPageAfter(Instant createdAt, UUID id, Limit limit);
    List<Video> findByOwnerIdOrderByCreatedAtDescIdDesc(String ownerId, Limit limit);

    @Query("""
            select v from Video v where v.ownerId = :ownerId
            and (v.createdAt < :createdAt or (v.createdAt = :createdAt and v.id < :id))
            order by v.createdAt desc, v.id desc
            """)
    List<Video> findOwnedPageAfter(String ownerId, Instant createdAt, UUID id, Limit limit);
}
