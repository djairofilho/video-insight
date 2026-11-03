import hashlib
from types import SimpleNamespace

import httpx
import pytest

from real_video_load import Run, check_cases


class Evidence:
    def __init__(self):
        self.events = []

    def emit(self, kind, **fields):
        self.events.append((kind, fields))


def test_manifest_rejects_changed_media_and_path_escape(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"reviewed")
    item = dict(filename="clip.mp4", duration_seconds=59, size_bytes=8,
                sha256=hashlib.sha256(b"reviewed").hexdigest())
    assert check_cases(tmp_path, {"cases": [item]})[0]["path"] == media
    media.write_bytes(b"modified")
    with pytest.raises(ValueError, match="manifesto"):
        check_cases(tmp_path, {"cases": [item]})
    with pytest.raises(ValueError, match="fora da pasta"):
        check_cases(tmp_path, {"cases": [dict(item, filename="../clip.mp4")]})


def test_admission_respects_audio_budget_and_stop_guard():
    args = SimpleNamespace(window_seconds=3600, stop_before_end_seconds=300,
                           max_jobs=18, max_audio_seconds=100)
    run = Run(None, args, [{"duration_seconds": 59}], Evidence())
    assert run.next_case()[0] == 1
    assert run.next_case() is None
    assert run.audio_seconds == 59
    run.halt("monitor_guard")
    assert run.stop.is_set() and run.stop_reason == "monitor_guard"
    assert run.next_case() is None


def test_api_errors_do_not_reveal_response_body_or_token():
    args = SimpleNamespace(base_url="https://gateway.test")
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403, text="secret-body"))) as client:
        run = Run(client, args, [], Evidence())
        with pytest.raises(RuntimeError, match="^api_http_403$"):
            run.request("GET", "/api/v1/videos")


def test_existing_monitor_stop_file_prevents_first_upload(tmp_path):
    stop = tmp_path / "stop"
    stop.write_text("Monitor indisponível", encoding="utf-8")
    run = Run(None, SimpleNamespace(stop_file=stop), [{"duration_seconds": 59}], Evidence())
    assert run.next_case() is None
    assert run.submitted == 0 and run.stop_reason == "monitor_guard"


def test_upload_uses_separate_client_and_checks_all_ai_outputs(tmp_path, monkeypatch):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"media")
    calls = []

    def reply(request):
        assert request.headers["Authorization"] == "Bearer test-session"
        calls.append(request.url.path)
        if request.url.path.endswith("/upload-url"):
            data = {"url": "https://storage.test/object?signature=private", "headers": {"Content-Type": "video/mp4"}}
        elif request.url.path.endswith("/upload-complete"):
            data = {"upload_status": "ready"}
        elif request.url.path.endswith("/result"):
            data = {"transcript": [{"text": "fala"}], "summary": "resumo", "chapters": [{"title": "capítulo"}]}
        elif request.url.path.endswith("/jobs/j1"):
            data = {"status": "completed"}
        else:
            data = {"id": "j1" if request.url.path.endswith("/jobs") else "v1"}
        return httpx.Response(200, json=data)

    def put(url, **kwargs):
        assert "Authorization" not in kwargs["headers"]
        assert kwargs["content"] == b"media"
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "put", put)
    args = SimpleNamespace(base_url="https://gateway.test", window_seconds=3600, drain_seconds=600, poll_seconds=5)
    evidence = Evidence()
    with httpx.Client(headers={"Authorization": "Bearer test-session"}, transport=httpx.MockTransport(reply)) as client:
        run = Run(client, args, [], evidence)
        run.pipeline(1, dict(filename="clip.mp4", duration_seconds=59, size_bytes=5, path=path))
    finished = [data for kind, data in evidence.events if kind == "case_finished"]
    assert finished[0]["valid"] is True and finished[0]["inside_window"] is True
    assert not run.stop.is_set()
    assert "/api/v1/jobs/j1/result" in calls
