package br.edu.insper.videoinsight.video.storage;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * Garante o bucket de vídeos na inicialização. Uma falha não derruba o serviço: o {@code /health} precisa responder
 * mesmo com o MinIO fora do ar, e as operações de storage falham com 503 até ele voltar.
 */
@Component
public class BucketInitializer {
    private static final Logger log = LoggerFactory.getLogger(BucketInitializer.class);

    private final VideoStorage storage;

    public BucketInitializer(VideoStorage storage) {
        this.storage = storage;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void createBucketIfMissing() {
        try {
            storage.ensureBucket();
        } catch (RuntimeException exception) {
            log.warn("Não foi possível garantir o bucket de vídeos", exception);
        }
    }
}
