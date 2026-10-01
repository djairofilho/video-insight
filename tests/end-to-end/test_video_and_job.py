"""Video Service e Job Service juntos, sem depender dos provedores de IA."""

import uuid

from support import FAKE_MEDIA


def test_upload_goes_directly_to_storage_and_can_be_played(api):
    video_id = api.upload(FAKE_MEDIA, 12.5)

    video = api.get_video(video_id).json()
    assert video["upload_status"] == "ready"
    assert video["duration_seconds"] == 12.5
    assert video["size_bytes"] == len(FAKE_MEDIA)

    playback = api.playback_url(video_id).json()
    assert playback["method"] == "GET"
    downloaded = api.client.get(playback["url"])
    assert downloaded.status_code == 200
    assert downloaded.content == FAKE_MEDIA

    listed = api.list_videos(limit=100).json()["items"]
    assert video_id in {item["id"] for item in listed}


def test_invalid_videos_are_rejected(api):
    assert api.create_video(1000, content_type="video/quicktime").status_code == 400
    assert api.create_video(104_857_601).status_code == 400
    assert api.create_video(0).status_code == 400

    video_id = api.create_video(len(FAKE_MEDIA)).json()["id"]
    assert api.complete_upload(video_id, 601).status_code == 400


def test_confirming_without_the_file_is_a_conflict(api):
    video_id = api.create_video(len(FAKE_MEDIA)).json()["id"]

    response = api.complete_upload(video_id, 10)

    assert response.status_code == 409
    assert response.json()["code"] == "UPLOAD_NOT_FOUND"
    assert api.get_video(video_id).json()["upload_status"] == "pending"


def test_file_with_another_size_fails_the_upload(api):
    video_id = api.create_video(len(FAKE_MEDIA) + 10).json()["id"]
    api.put_file(api.upload_url(video_id).json(), FAKE_MEDIA).raise_for_status()

    response = api.complete_upload(video_id, 10)

    assert response.status_code == 409
    assert response.json()["code"] == "UPLOAD_SIZE_MISMATCH"
    assert api.get_video(video_id).json()["upload_status"] == "failed"
    assert api.playback_url(video_id).status_code == 409


def test_job_service_checks_the_video_synchronously(api):
    unknown = api.create_job(str(uuid.uuid4()))
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "VIDEO_NOT_FOUND"

    pending_id = api.create_video(len(FAKE_MEDIA)).json()["id"]
    pending = api.create_job(pending_id)
    assert pending.status_code == 409
    assert pending.json()["code"] == "VIDEO_NOT_READY"


def test_deleted_video_disappears_for_both_services(api):
    video_id = api.upload(FAKE_MEDIA, 5)
    playback = api.playback_url(video_id).json()

    assert api.delete_video(video_id).status_code == 204

    assert api.get_video(video_id).status_code == 404
    assert api.client.get(playback["url"]).status_code == 404
    assert api.create_job(video_id).status_code == 404
    assert api.delete_video(video_id).status_code == 404


def test_unreadable_media_fails_the_job_and_can_be_retried(api, job_timeout):
    """O worker rejeita o arquivo antes de chamar a IA, então o teste não consome cota."""
    video_id = api.upload(FAKE_MEDIA, 5)
    job = api.create_job(video_id, ["transcription"]).json()
    assert job["status"] == "queued"

    failed = api.wait_for_job(job["id"], job_timeout)
    assert failed["status"] == "failed"
    assert failed["error"]["code"]
    assert api.job_result(job["id"]).status_code == 409

    retried = api.retry_job(job["id"])
    assert retried.status_code == 202
    assert retried.json()["attempt"] == 2
    assert api.wait_for_job(job["id"], job_timeout)["status"] == "failed"


def test_cancelled_job_stays_cancelled(api):
    video_id = api.upload(FAKE_MEDIA, 5)
    job_id = api.create_job(video_id, ["transcription"]).json()["id"]

    cancelled = api.cancel_job(job_id)

    assert cancelled.status_code == 202
    assert cancelled.json()["status"] == "cancelled"
    assert api.cancel_job(job_id).status_code == 409
    assert api.get_job(job_id).json()["status"] == "cancelled"
