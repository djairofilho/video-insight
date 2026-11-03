"""Autoriza somente MinIO na chave já instalada para o túnel do Job Service."""

import ipaddress
import re
import sys
from pathlib import Path


def authorize(content: str, public_key: str, host: str) -> str:
    ipaddress.ip_address(host)
    match = re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?", public_key.strip())
    if not match:
        raise ValueError("Chave pública inválida")
    key = " ".join(public_key.split()[:2])
    rows = content.splitlines()
    indices = [i for i, row in enumerate(rows) if key in row]
    if len(indices) != 1:
        raise ValueError("A chave deve existir uma única vez")
    index = indices[0]
    rule = f'permitopen="{host}:9000"'
    if rule not in rows[index]:
        if not rows[index].startswith("restrict,") and "restrict," not in rows[index]:
            raise ValueError("A chave existente deve manter a opção restrict")
        rows[index] = rule + "," + rows[index]
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    path = Path("/home/video-tunnel/.ssh/authorized_keys")
    previous = path.read_text()
    updated = authorize(previous, sys.stdin.read(), sys.argv[1])
    backup = path.with_suffix(".previous")
    backup.write_text(previous)
    backup.chmod(0o600)
    path.write_text(updated)
    path.chmod(0o600)
