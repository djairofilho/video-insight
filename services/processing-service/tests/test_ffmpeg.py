import json
import shutil
import subprocess

import pytest

from processing_service.domain import ProcessingError
from processing_service.media.ffmpeg import FfmpegMedia, MediaInfo


class RecordingRunner:
    def __init__(self, result=None, error=None) -> None:
        self.result = result or subprocess.CompletedProcess([], 0, "", "")
        self.error = error
        self.commands: list[list[str]] = []
        self.options: dict = {}

    def __call__(self, command, **options):
        self.commands.append(command)
        self.options = options
        if self.error:
            raise self.error
        return self.result


def probe_output(duration="12.5", codecs=("video", "audio")) -> subprocess.CompletedProcess:
    payload = {"format": {"duration": duration}, "streams": [{"codec_type": c} for c in codecs]}
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def test_probe_reads_duration_and_audio(tmp_path):
    runner = RecordingRunner(probe_output())

    info = FfmpegMedia(30, run=runner).probe(tmp_path / "video.mp4")

    assert info == MediaInfo(duration_seconds=12.5, has_audio=True)
    assert runner.commands[0][0] == "ffprobe"
    assert runner.options["timeout"] == 30
    assert runner.options["check"] is False


def test_probe_detects_missing_audio(tmp_path):
    runner = RecordingRunner(probe_output(codecs=("video",)))

    assert FfmpegMedia(30, run=runner).probe(tmp_path / "video.mp4").has_audio is False


@pytest.mark.parametrize(
    "stdout", ["isto não é json", json.dumps({"format": {}}), json.dumps({"format": {"duration": "N/A"}})]
)
def test_probe_rejects_unreadable_output(tmp_path, stdout):
    runner = RecordingRunner(subprocess.CompletedProcess([], 0, stdout, ""))

    with pytest.raises(ProcessingError) as raised:
        FfmpegMedia(30, run=runner).probe(tmp_path / "video.mp4")

    assert (raised.value.code, raised.value.retryable) == ("invalid_media", False)


def test_failed_command_reports_stderr(tmp_path):
    runner = RecordingRunner(subprocess.CompletedProcess([], 1, "", "moov atom not found\n"))

    with pytest.raises(ProcessingError) as raised:
        FfmpegMedia(30, run=runner).probe(tmp_path / "video.mp4")

    assert raised.value.code == "invalid_media"
    assert raised.value.message == "moov atom not found"
    assert raised.value.retryable is False


def test_failed_command_without_stderr_reports_exit_code(tmp_path):
    runner = RecordingRunner(subprocess.CompletedProcess([], 3, "", ""))

    with pytest.raises(ProcessingError) as raised:
        FfmpegMedia(30, run=runner).extract_audio(tmp_path / "v.mp4", tmp_path / "a.flac")

    assert raised.value.code == "audio_extraction_failed"
    assert raised.value.message == "código 3"


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (FileNotFoundError("ffprobe"), "ffmpeg_unavailable"),
        (subprocess.TimeoutExpired("ffprobe", 30), "media_timeout"),
    ],
)
def test_operational_errors_are_retryable(tmp_path, error, code):
    with pytest.raises(ProcessingError) as raised:
        FfmpegMedia(30, run=RecordingRunner(error=error)).probe(tmp_path / "video.mp4")

    assert (raised.value.code, raised.value.retryable) == (code, True)


def test_extract_audio_produces_mono_16khz(tmp_path):
    runner = RecordingRunner()
    destination = tmp_path / "audio.flac"

    result = FfmpegMedia(30, run=runner).extract_audio(tmp_path / "video.mp4", destination)

    command = runner.commands[0]
    assert result == destination
    assert command[0] == "ffmpeg"
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-c:a") + 1] == "flac"
    assert command[-1] == str(destination)


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")
def test_real_ffmpeg_extracts_audio_from_video(tmp_path):
    video = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-shortest", "-c:v", "libx264", "-c:a", "aac", str(video),
        ],
        check=True,
    )
    media = FfmpegMedia(60)

    info = media.probe(video)
    audio = media.extract_audio(video, tmp_path / "audio.flac")

    assert info.has_audio
    assert 1.5 < info.duration_seconds < 2.5
    assert media.probe(audio).has_audio
