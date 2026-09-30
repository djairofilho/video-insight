package br.edu.insper.videoinsight.video.application;

import static org.assertj.core.api.Assertions.assertThat;

import br.edu.insper.videoinsight.video.IntegrationTest;
import br.edu.insper.videoinsight.video.domain.UploadStatus;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class VideoServiceConcurrencyTest extends IntegrationTest {
    private static final int THREADS = 8;

    @Autowired
    private VideoService videoService;

    @Test
    void simultaneousConfirmationsEndWithOneReadyVideo() throws Exception {
        var videoId = createVideo();
        objectStored(videoId, SIZE);

        var results = runTogether(() -> videoService.completeUpload(videoId, 42.0).getUploadStatus());

        assertThat(results).containsOnly(UploadStatus.READY);
        assertThat(videos.findById(videoId)).get()
                .satisfies(video -> assertThat(video.getDurationSeconds()).isEqualTo(42.0));
    }

    @Test
    void simultaneousUploadUrlsAllSucceed() throws Exception {
        var videoId = createVideo();

        var results = runTogether(() -> videoService.createUploadUrl(videoId).method());

        assertThat(results).containsOnly("PUT");
        assertThat(videos.findById(videoId)).get()
                .satisfies(video -> assertThat(video.getUploadStatus()).isEqualTo(UploadStatus.UPLOADING));
    }

    private static <T> List<T> runTogether(Callable<T> task) throws Exception {
        var start = new CountDownLatch(1);
        try (var executor = Executors.newFixedThreadPool(THREADS)) {
            var futures = new ArrayList<Future<T>>();
            for (int i = 0; i < THREADS; i++) {
                futures.add(executor.submit(() -> {
                    start.await();
                    return task.call();
                }));
            }
            start.countDown();
            var results = new ArrayList<T>();
            for (var future : futures) {
                results.add(future.get());
            }
            return results;
        }
    }
}
