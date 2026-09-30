package br.edu.insper.videoinsight.video.domain;

public class InvalidVideoStateException extends RuntimeException {
    public InvalidVideoStateException(String message) {
        super(message);
    }
}
