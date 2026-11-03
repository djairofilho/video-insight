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
    assert renderer["render"](renderer["PROFILES"], tmp_path, environment) == 7
    nginx = (tmp_path / "infrastructure/aws/edge/proxy.conf").read_text()
    assert "proxy_set_header Host storage.example:9443;" in nginx
    config = json.loads((tmp_path / "apps/frontend/vercel.json").read_text())
    assert config["rewrites"][0]["destination"].startswith("http://localhost:")
    gateway = json.loads((tmp_path / "apps/api-gateway/krakend.json").read_text())
    assert gateway["extra_config"]["security/cors"]["allow_origins"] == ["https://frontend.example"]


@pytest.mark.parametrize("host", ["", "example; command", "example\nserver {}", "http://example"])
def test_rejects_missing_or_unsafe_hosts_without_writing_configuration(tmp_path, host):
    copy_templates(tmp_path)
    with pytest.raises(ValueError):
        renderer["render"](["frontend"], tmp_path, {"AWS_GATEWAY_HOST": host})
    assert not (tmp_path / "apps/frontend/vercel.json").exists()


def test_address_guard_accepts_only_local_and_documentation_addresses():
    assert list(guard["sensitive"]("localhost 127.0.0.1 203.0.113.1")) == []
    # Construído em tempo de teste para não versionar um endereço de infraestrutura.
    address = ".".join(map(str, (10, 20, 30, 40)))
    assert list(guard["sensitive"]("secret host:\n" + address)) == [2]
