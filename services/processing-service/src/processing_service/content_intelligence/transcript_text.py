from processing_service.domain import Transcript


def render(transcript: Transcript) -> str:
    return "\n".join(
        f"[{segment.start_seconds:.1f}s – {segment.end_seconds:.1f}s] {segment.text}"
        for segment in transcript.segments
    )
