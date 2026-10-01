"""Fluxo completo com o Processing Service e os provedores de IA reais."""

from support import run_together


def assert_complete_result(api, job_id: str, video_id: str) -> None:
    result = api.job_result(job_id)
    assert result.status_code == 200
    body = result.json()
    assert body["video_id"] == video_id
    assert body["transcript"], "transcrição vazia"
    for segment in body["transcript"]:
        assert 0 <= segment["start_seconds"] <= segment["end_seconds"]
    assert body["summary"].strip()
    assert body["chapters"]
    assert {model["purpose"] for model in body["models"]} == {"transcription", "summary", "chapters"}


def test_video_is_transcribed_summarized_and_chaptered(api, sample_video, job_timeout):
    content, duration = sample_video
    video_id = api.upload(content, duration)

    job = api.create_job(video_id)
    assert job.status_code == 202
    job_id = job.json()["id"]

    finished = api.wait_for_job(job_id, job_timeout)
    assert finished["status"] == "completed", finished
    assert finished["progress_percent"] == 100
    assert_complete_result(api, job_id, video_id)

    for fmt in ("txt", "srt", "json"):
        export = api.export_transcript(job_id, fmt)
        assert export.status_code == 200
        downloaded = api.client.get(export.json()["url"])
        assert downloaded.status_code == 200
        assert downloaded.content.strip()

    # O vídeo original continua disponível para navegar pelos timestamps.
    playback = api.playback_url(video_id).json()
    assert api.client.get(playback["url"]).content == content


def test_two_videos_are_processed_at_the_same_time(api, sample_video, job_timeout):
    content, duration = sample_video
    video_ids = run_together(2, lambda _: api.upload(content, duration))
    job_ids = [response.json()["id"] for response in run_together(2, lambda i: api.create_job(video_ids[i]))]

    finished = run_together(2, lambda i: api.wait_for_job(job_ids[i], job_timeout))

    assert [job["status"] for job in finished] == ["completed", "completed"], finished
    for job_id, video_id in zip(job_ids, video_ids):
        assert_complete_result(api, job_id, video_id)
