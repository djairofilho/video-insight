import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "infrastructure/aws/observability"
entry = runpy.run_path(str(ROOT / "authorize-metrics.py"))["entry"]
unit = runpy.run_path(str(ROOT / "install-metrics-tunnel.py"))["unit"]


def test_metrics_key_is_restricted_to_known_ports_without_shell():
    line = entry("ssh-ed25519 AAAAtest comment", "127.0.0.1", False)
    assert 'command="/bin/false",restrict,port-forwarding' in line
    assert 'permitopen="127.0.0.1:9100"' in line
    assert ":9091" not in line
    assert ':9091"' in entry("ssh-ed25519 AAAAtest", "127.0.0.1", True)
    with pytest.raises(ValueError):
        entry("ssh-rsa invalid", "127.0.0.1", True)


def test_tunnel_has_pinned_host_and_only_expected_forwards():
    content = unit("gateway", "127.0.0.1", "127.0.0.1")
    assert "StrictHostKeyChecking=yes" in content
    assert "-L 127.0.0.1:19101:127.0.0.1:9100" in content
    assert "-L 127.0.0.1:19111:127.0.0.1:9091" in content
    core = unit("core", "127.0.0.1", "127.0.0.1", "127.0.0.1")
    assert ":9091" not in core
    assert "-R 127.0.0.1:13000:127.0.0.1:3000" in core
    assert "-R 127.0.0.1:19090:127.0.0.1:9090" in core
    restricted = entry("ssh-ed25519 AAAAtest", "127.0.0.1", False, core=True)
    assert 'permitlisten="127.0.0.1:13000"' in restricted
    assert 'permitlisten="127.0.0.1:19090"' in restricted
