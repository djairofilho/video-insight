"""Requisições simultâneas entre Video Service e Job Service."""

import uuid

from support import FAKE_MEDIA, run_together

PARALLEL = 10


def test_parallel_uploads_create_distinct_ready_videos(api):
    video_ids = run_together(PARALLEL, lambda _: api.upload(FAKE_MEDIA, 7))

    assert len(set(video_ids)) == PARALLEL
    for video_id in video_ids:
        assert api.get_video(video_id).json()["upload_status"] == "ready"


def test_simultaneous_confirmations_of_the_same_upload(api):
    video_id = api.create_video(len(FAKE_MEDIA)).json()["id"]
    api.put_file(api.upload_url(video_id).json(), FAKE_MEDIA).raise_for_status()

    responses = run_together(PARALLEL, lambda _: api.complete_upload(video_id, 9))

    assert {response.status_code for response in responses} == {200}
    assert {response.json()["upload_status"] for response in responses} == {"ready"}
    assert api.get_video(video_id).json()["duration_seconds"] == 9


def test_simultaneous_upload_urls_for_the_same_video(api):
    video_id = api.create_video(len(FAKE_MEDIA)).json()["id"]

    responses = run_together(PARALLEL, lambda _: api.upload_url(video_id))

    assert {response.status_code for response in responses} == {200}
    assert api.get_video(video_id).json()["upload_status"] == "uploading"


def test_same_idempotency_key_creates_a_single_job(api):
    video_id = api.upload(FAKE_MEDIA, 5)
    key = f"e2e-{uuid.uuid4()}"

    responses = run_together(PARALLEL, lambda _: api.create_job(video_id, ["transcription"], key))

    assert {response.status_code for response in responses} == {202}
    job_ids = {response.json()["id"] for response in responses}
    assert len(job_ids) == 1
    api.cancel_job(job_ids.pop())


def test_different_keys_create_independent_jobs(api):
    video_id = api.upload(FAKE_MEDIA, 5)

    responses = run_together(PARALLEL, lambda _: api.create_job(video_id, ["transcription"]))

    assert {response.status_code for response in responses} == {202}
    job_ids = {response.json()["id"] for response in responses}
    assert len(job_ids) == PARALLEL
    for job_id in job_ids:
        api.cancel_job(job_id)


def test_deleting_while_jobs_are_requested(api):
    """Excluir e pedir jobs ao mesmo tempo nunca produz erro interno em nenhum dos serviços."""
    video_id = api.upload(FAKE_MEDIA, 5)

    def act(index: int):
        return api.delete_video(video_id) if index == 0 else api.create_job(video_id, ["transcription"])

    responses = run_together(PARALLEL, act)

    assert all(response.status_code < 500 for response in responses)
    assert api.get_video(video_id).status_code == 404
    for response in responses[1:]:
        if response.status_code == 202:
            api.cancel_job(response.json()["id"])
