package br.edu.insper.videoinsight.video.application;

import br.edu.insper.videoinsight.video.domain.Video;
import br.edu.insper.videoinsight.video.domain.VideoRepository;
import br.edu.insper.videoinsight.video.storage.SignedUrl;
import br.edu.insper.videoinsight.video.storage.VideoStorage;
import java.time.Clock;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.data.domain.Limit;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Cadastro, upload e consulta de vídeos. As transições de estado usam versionamento otimista: quando duas requisições
 * alteram o mesmo vídeo ao mesmo tempo, a segunda relê o vídeo e decide de novo em vez de sobrescrever a primeira.
 */
@Service
public class VideoService {
    private static final int MAX_UPDATE_ATTEMPTS = 3;

    private final VideoRepository videos;
    private final VideoStorage storage;
    private final TransactionTemplate transaction;
    private final Clock clock;

    public VideoService(VideoRepository videos, VideoStorage storage, TransactionTemplate transaction, Clock clock) {
        this.videos = videos;
        this.storage = storage;
        this.transaction = transaction;
        this.clock = clock;
    }

    public Video create(String fileName, String contentType, long sizeBytes) {
        return videos.save(Video.create(fileName, contentType, sizeBytes, clock.instant()));
    }

    @Transactional(readOnly = true)
    public Video get(UUID videoId) {
        return find(videoId);
    }

    @Transactional(readOnly = true)
    public VideoPage list(int limit, String cursor) {
        // Um item a mais indica se existe próxima página.
        var page = cursor == null
                ? videos.findAllByOrderByCreatedAtDescIdDesc(Limit.of(limit + 1))
                : findPageAfter(VideoCursor.decode(cursor), limit + 1);
        if (page.size() <= limit) {
            return new VideoPage(page, null);
        }
        var items = page.subList(0, limit);
        var last = items.getLast();
        return new VideoPage(items, new VideoCursor(last.getCreatedAt(), last.getId()).encode());
    }

    public SignedUrl createUploadUrl(UUID videoId) {
        var video = update(videoId, current -> current.startUpload(clock.instant()));
        return storage.presignUpload(video.storageKey());
    }

    /**
     * Confirma o upload conferindo o objeto no storage. Repetir a confirmação de um vídeo pronto devolve o mesmo vídeo.
     */
    public Video completeUpload(UUID videoId, double durationSeconds) {
        var video = find(videoId);
        if (video.isReady()) {
            return video;
        }
        var size = storage.objectSize(video.storageKey())
                .orElseThrow(() -> ApiException.conflict("UPLOAD_NOT_FOUND", "O arquivo do vídeo não foi enviado."));
        if (size != video.getSizeBytes()) {
            update(videoId, current -> current.markFailed(clock.instant()));
            throw ApiException.conflict("UPLOAD_SIZE_MISMATCH",
                    "O arquivo enviado tem " + size + " bytes; o cadastro informa " + video.getSizeBytes() + ".");
        }
        return update(videoId, current -> {
            if (!current.isReady()) {
                current.markReady(durationSeconds, clock.instant());
            }
        });
    }

    @Transactional(readOnly = true)
    public SignedUrl createPlaybackUrl(UUID videoId) {
        var video = find(videoId);
        if (!video.isReady()) {
            throw ApiException.conflict("VIDEO_NOT_READY", "O upload do vídeo ainda não foi confirmado.");
        }
        return storage.presignPlayback(video.storageKey());
    }

    /** Remove o arquivo antes do registro, para que um vídeo listado nunca aponte para um arquivo apagado. */
    public void delete(UUID videoId) {
        var video = find(videoId);
        storage.delete(video.storageKey());
        videos.deleteById(video.getId());
    }

    /** Relê e altera o vídeo numa transação; só grava se algo mudou, então repetir uma transição não conflita. */
    private Video update(UUID videoId, Consumer<Video> change) {
        for (int attempt = 1; ; attempt++) {
            try {
                return transaction.execute(status -> {
                    var video = find(videoId);
                    change.accept(video);
                    videos.flush();
                    return video;
                });
            } catch (OptimisticLockingFailureException concurrentUpdate) {
                if (attempt == MAX_UPDATE_ATTEMPTS) {
                    throw concurrentUpdate;
                }
            }
        }
    }

    private List<Video> findPageAfter(VideoCursor cursor, int limit) {
        return videos.findPageAfter(cursor.createdAt(), cursor.id(), Limit.of(limit));
    }

    private Video find(UUID videoId) {
        return videos.findById(videoId)
                .orElseThrow(() -> ApiException.notFound("VIDEO_NOT_FOUND", "Vídeo não encontrado."));
    }
}
