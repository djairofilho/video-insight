import runpy
from pathlib import Path

import pytest

authorize = runpy.run_path(str(Path(__file__).resolve().parents[2] /
    "infrastructure/aws/tunnels/allow-job-storage.py"))["authorize"]


def test_adds_only_storage_to_existing_restricted_key_and_is_idempotent():
    key = "ssh-ed25519 AAAAtest"
    original = 'restrict,port-forwarding,permitopen="127.0.0.1:5434" ' + key + " job\n"
    updated = authorize(original, key + " job", "127.0.0.1")
    assert updated == 'permitopen="127.0.0.1:9000",' + original
    assert authorize(updated, key, "127.0.0.1") == updated
    with pytest.raises(ValueError):
        authorize(original, "ssh-ed25519 BBBBother", "127.0.0.1")
    with pytest.raises(ValueError):
        authorize(key + "\n", key, "127.0.0.1")
