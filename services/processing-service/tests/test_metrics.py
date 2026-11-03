from types import SimpleNamespace

from fastapi.testclient import TestClient

from processing_service.app import app


def test_metrics_report_actual_broker_connectivity():
    with TestClient(app, client=("127.0.0.1", 1234)) as client:
        app.state.worker = SimpleNamespace(connected=True)
        assert "video_insight_worker_connected 1" in client.get("/metrics").text
        app.state.worker = SimpleNamespace(connected=False)
        assert "video_insight_worker_connected 0" in client.get("/metrics").text
        app.state.worker = None


def test_metrics_reject_public_clients():
    with TestClient(app, client=("203.0.113.1", 1234)) as client:
        assert client.get("/metrics").status_code == 403


def test_metrics_accept_explicit_network_configuration(monkeypatch):
    with TestClient(app, client=("203.0.113.1", 1234)) as client:
        monkeypatch.setattr("processing_service.app.get_settings",
                            lambda: SimpleNamespace(metrics_allowed_networks="203.0.113.0/24"))
        assert client.get("/metrics").status_code == 200
