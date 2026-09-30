package br.edu.insper.videoinsight.job.video;

import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** Consulta síncrona ao Video Service para saber se o vídeo existe e se o upload foi confirmado. */
@Component
public class VideoClient {
    private final RestClient restClient;

    public VideoClient(RestClient videoServiceRestClient) {
        this.restClient = videoServiceRestClient;
    }

    public Optional<VideoSummary> findVideo(UUID videoId) {
        try {
            return Optional.ofNullable(restClient.get()
                    .uri("/api/v1/videos/{videoId}", videoId)
                    .retrieve()
                    .body(VideoSummary.class));
        } catch (HttpClientErrorException.NotFound exception) {
            return Optional.empty();
        } catch (RestClientException exception) {
            throw new VideoServiceUnavailableException(exception);
        }
    }
}
