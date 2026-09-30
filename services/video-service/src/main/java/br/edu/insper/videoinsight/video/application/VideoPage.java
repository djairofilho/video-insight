package br.edu.insper.videoinsight.video.application;

import br.edu.insper.videoinsight.video.domain.Video;
import java.util.List;

public record VideoPage(List<Video> items, String nextCursor) {
}
