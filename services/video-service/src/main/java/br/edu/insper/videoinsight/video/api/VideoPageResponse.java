package br.edu.insper.videoinsight.video.api;

import br.edu.insper.videoinsight.video.application.VideoPage;
import java.util.List;

/** Corresponde ao schema {@code VideoPage} do contrato. */
public record VideoPageResponse(List<VideoResponse> items, String nextCursor) {
    public static VideoPageResponse from(VideoPage page) {
        return new VideoPageResponse(page.items().stream().map(VideoResponse::from).toList(), page.nextCursor());
    }
}
