package br.edu.insper.videoinsight.job.video;

public class VideoServiceUnavailableException extends RuntimeException {
    public VideoServiceUnavailableException(Throwable cause) {
        super("Video Service indisponível.", cause);
    }
}
