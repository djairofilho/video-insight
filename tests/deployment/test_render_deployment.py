import json
import runpy
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
renderer = runpy.run_path(str(ROOT / "scripts/render_deployment.py"))
guard = runpy.run_path(str(ROOT / "scripts/check_sensitive_addresses.py"))


def copy_templates(target):
    for paths in renderer["PROFILES"].values():
        for relative in paths:
            source = ROOT / (relative + ".template")
            destination = target / (relative + ".template")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def test_renders_all_components_without_exposing_hosts_in_source(tmp_path):
    copy_templates(tmp_path)
    environment = dict(renderer["EXAMPLES"], STORAGE_PUBLIC_ENDPOINT="https://storage.example:9443")
    assert renderer["render"](renderer["PROFILES"], tmp_path, environment) == 8
    nginx = (tmp_path / "infrastructure/aws/edge/proxy.conf").read_text()
    assert "proxy_set_header Host storage.example:9443;" in nginx
    assert "proxy_pass https://storage.example:9443/;" in nginx
    assert "proxy_ssl_verify on;" in nginx
    config = json.loads((tmp_path / "apps/frontend/vercel.json").read_text())
    assert next(route for route in config["rewrites"] if route["source"] == "/api/v1/:path*")["destination"].startswith("http://localhost:")
    gateway = json.loads((tmp_path / "apps/api-gateway/krakend.json").read_text())
    assert gateway["extra_config"]["security/cors"]["allow_origins"] == ["https://frontend.example"]


@pytest.mark.parametrize("host", ["", "example; command", "example\nserver {}", "http://example"])
def test_rejects_missing_or_unsafe_hosts_without_writing_configuration(tmp_path, host):
    copy_templates(tmp_path)
    with pytest.raises(ValueError):
        renderer["render"](["frontend"], tmp_path, dict(renderer["EXAMPLES"], AWS_GATEWAY_HOST=host))
    assert not (tmp_path / "apps/frontend/vercel.json").exists()


def test_address_guard_accepts_only_local_and_documentation_addresses():
    assert list(guard["sensitive"]("localhost 127.0.0.1 203.0.113.1")) == []
    # Construído em tempo de teste para não versionar um endereço de infraestrutura.
    address = ".".join(map(str, (10, 20, 30, 40)))
    assert list(guard["sensitive"]("secret host:\n" + address)) == [2]


def test_frontend_origins_preserve_primary_and_validate_extra_origins():
    environment = {"FRONTEND_ORIGIN": "https://app.example", "FRONTEND_ORIGINS": "https://legacy.example, https://app.example/"}
    assert json.loads(renderer["value"]("FRONTEND_ORIGINS_JSON", environment)) == ["https://app.example", "https://legacy.example"]
    for unsafe in ("*", "https://*.example", "http://legacy.example", "https://legacy.example/path"):
        with pytest.raises(ValueError):
            renderer["value"]("FRONTEND_ORIGINS_JSON", dict(environment, FRONTEND_ORIGINS=unsafe))


def test_monitoring_routes_are_host_scoped_and_do_not_publish_the_auth_hash(tmp_path):
    copy_templates(tmp_path)
    environment = dict(renderer["EXAMPLES"], GRAFANA_PUBLIC_HOST="grafana.example",
                       PROMETHEUS_PUBLIC_HOST="prometheus.example", STORAGE_PUBLIC_HOST="storage.example")
    renderer["render"](["frontend", "https-storage"], tmp_path, environment)
    frontend = (tmp_path / "apps/frontend/vercel.json").read_text()
    config = json.loads(frontend)
    assert config["redirects"] == [
        {"source": "/", "has": [{"type": "host", "value": "grafana.example"}],
         "destination": "/d/video-insight-infra", "permanent": False},
        {"source": "/", "has": [{"type": "host", "value": "prometheus.example"}],
         "destination": "/query", "permanent": False},
    ]
    for index, (host, service) in enumerate((("grafana.example", "grafana"), ("prometheus.example", "prometheus"))):
        route = config["rewrites"][index]
        assert route["has"] == [{"type": "host", "value": host}]
        assert route["destination"] == f"https://storage.example:8081/_monitor/{service}/:path*"
        header = config["headers"][-2 + index]
        assert header["has"] == route["has"]
        assert header["headers"] == [{"key": "Cache-Control", "value": "private, no-store"}]
    assert environment["PROMETHEUS_AUTH_HASH"] not in frontend
    caddy = (tmp_path / "infrastructure/aws/https/storage.Caddyfile").read_text()
    assert 'basic_auth bcrypt "Video Insight Monitoring"' in caddy
    assert "header_up -Authorization" in caddy
    assert "respond @management 403" in caddy
    assert "reverse_proxy localhost:9000" in caddy


def test_monitoring_renderer_refuses_plaintext_password():
    with pytest.raises(ValueError):
        renderer["value"]("PROMETHEUS_AUTH_HASH", {"PROMETHEUS_AUTH_HASH": "plaintext"})
