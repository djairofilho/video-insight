"""Verifica a autorização no ambiente real usando somente recursos criados pelo teste."""

import httpx
import pytest

from support import FAKE_MEDIA


@pytest.mark.parametrize("token", [None, "invalid.jwt.token"])
def test_rejects_missing_or_invalid_token(api, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = httpx.get(f"{api.video_url}/api/v1/videos", headers=headers, timeout=30)
    assert response.status_code == 401


def test_accounts_cannot_access_each_others_resources(api, other_api):
    video_a = api.upload(FAKE_MEDIA, duration_seconds=1)
    video_b = other_api.create_video(32, file_name="e2e-owner-b.mp4").raise_for_status().json()["id"]
    job_a = api.create_job(video_a, operations=["transcription"]).raise_for_status().json()["id"]

    assert video_a in {video["id"] for video in api.list_videos(limit=100).raise_for_status().json()["items"]}
    assert video_a not in {video["id"] for video in other_api.list_videos(limit=100).raise_for_status().json()["items"]}
    assert api.get_video(video_b).status_code == 404
    assert other_api.get_video(video_a).status_code == 404
    for response in (
        other_api.upload_url(video_a), other_api.playback_url(video_a),
        other_api.complete_upload(video_a, 1), other_api.delete_video(video_a),
        other_api.get_job(job_a), other_api.job_result(job_a),
        other_api.export_transcript(job_a, "txt"), other_api.cancel_job(job_a),
        other_api.retry_job(job_a), other_api.create_job(video_a),
    ):
        assert response.status_code == 404
    assert api.get_video(video_a).status_code == 200
    assert other_api.get_video(video_b).status_code == 200
