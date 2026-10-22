package br.edu.insper.videoinsight.video.api;

import br.edu.insper.videoinsight.video.application.VideoService;
import br.edu.insper.videoinsight.video.storage.SignedUrl;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Implementa {@code contracts/openapi/video-service.yaml}. O Job Service consulta {@code GET /videos/{videoId}} antes de
 * criar um job. O serviço valida JWT Auth0 e restringe cada vídeo ao seu dono.
 */
@RestController
@RequestMapping("/api/v1/videos")
public class VideoController {
    private final VideoService videoService;

    public VideoController(VideoService videoService) {
        this.videoService = videoService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public VideoResponse createVideo(@Valid @RequestBody CreateVideoRequest request) {
        return VideoResponse.from(videoService.create(request.fileName(), request.contentType(), request.sizeBytes()));
    }

    @GetMapping
    public VideoPageResponse listVideos(
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int limit,
            @RequestParam(required = false) String cursor) {
        return VideoPageResponse.from(videoService.list(limit, cursor));
    }

    @GetMapping("/{videoId}")
    public VideoResponse getVideo(@PathVariable UUID videoId) {
        return VideoResponse.from(videoService.get(videoId));
    }

    @DeleteMapping("/{videoId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteVideo(@PathVariable UUID videoId) {
        videoService.delete(videoId);
    }

    @PostMapping("/{videoId}/upload-url")
    public SignedUrl createUploadUrl(@PathVariable UUID videoId) {
        return videoService.createUploadUrl(videoId);
    }

    @PostMapping("/{videoId}/upload-complete")
    public VideoResponse completeUpload(
            @PathVariable UUID videoId, @Valid @RequestBody CompleteUploadRequest request) {
        return VideoResponse.from(videoService.completeUpload(videoId, request.durationSeconds()));
    }

    @PostMapping("/{videoId}/playback-url")
    public SignedUrl createPlaybackUrl(@PathVariable UUID videoId) {
        return videoService.createPlaybackUrl(videoId);
    }
}
