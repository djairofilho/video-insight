package br.edu.insper.videoinsight.job.video;

import br.edu.insper.videoinsight.job.JobServiceProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class VideoClientConfig {
    @Bean
    RestClient videoServiceRestClient(RestClient.Builder builder, JobServiceProperties properties) {
        var videoService = properties.videoService();
        var requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(videoService.timeout());
        requestFactory.setReadTimeout(videoService.timeout());
        return builder.baseUrl(videoService.baseUrl().toString()).requestFactory(requestFactory).build();
    }
}
