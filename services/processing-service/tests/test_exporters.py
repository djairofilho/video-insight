from processing_service.domain import Transcript, TranscriptSegment
from processing_service.transcription.exporters import to_json, to_srt, to_txt

TRANSCRIPT = Transcript(
    language="pt",
    duration_seconds=3725.5,
    segments=(
        TranscriptSegment(start_seconds=0.0, end_seconds=2.5, text=" Olá, turma. "),
        TranscriptSegment(start_seconds=3661.0015, end_seconds=3725.5, text="Até a próxima."),
    ),
)
EMPTY = Transcript(language="pt", duration_seconds=4.0, segments=())


def test_srt_numbers_cues_and_formats_milliseconds():
    assert to_srt(TRANSCRIPT).decode() == (
        "1\n00:00:00,000 --> 00:00:02,500\nOlá, turma.\n\n"
        "2\n01:01:01,002 --> 01:02:05,500\nAté a próxima.\n"
    )


def test_txt_prefixes_each_segment_with_its_start():
    assert to_txt(TRANSCRIPT).decode() == "[00:00:00] Olá, turma.\n[01:01:01] Até a próxima.\n"


def test_json_round_trips():
    assert Transcript.model_validate_json(to_json(TRANSCRIPT)) == TRANSCRIPT


def test_empty_transcript_exports_empty_files():
    assert to_txt(EMPTY) == b""
    assert to_srt(EMPTY) == b""
