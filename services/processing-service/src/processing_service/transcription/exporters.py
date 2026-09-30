from processing_service.domain import Transcript


def to_json(transcript: Transcript) -> bytes:
    return transcript.model_dump_json(indent=2).encode()


def to_txt(transcript: Transcript) -> bytes:
    lines = [
        f"[{_clock(segment.start_seconds)}] {segment.text.strip()}"
        for segment in transcript.segments
    ]
    return ("\n".join(lines) + "\n").encode() if lines else b""


def to_srt(transcript: Transcript) -> bytes:
    cues = [
        f"{index}\n"
        f"{_srt_time(segment.start_seconds)} --> {_srt_time(segment.end_seconds)}\n"
        f"{segment.text.strip()}\n"
        for index, segment in enumerate(transcript.segments, start=1)
    ]
    return "\n".join(cues).encode()


def _clock(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
