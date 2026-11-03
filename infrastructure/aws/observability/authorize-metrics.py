"""Adiciona uma chave sem shell, restrita às portas de métricas desta máquina."""

import ipaddress
import re
import sys
from pathlib import Path


def entry(public_key: str, host: str, gateway: bool, *, core: bool = False) -> str:
    ipaddress.ip_address(host)
    if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?", public_key.strip()):
        raise ValueError("Chave pública inválida")
    key = " ".join(public_key.split()[:2])
    ports = [9100, 9091] if gateway else [9100]
    options = ['command="/bin/false"', "restrict", "port-forwarding"]
    options += [f'permitopen="{host}:{port}"' for port in ports]
    if core:
        options += ['permitlisten="127.0.0.1:13000"', 'permitlisten="127.0.0.1:19090"']
    return ",".join(options) + " " + key + " video-insight-metrics"


if __name__ == "__main__":
    key = sys.stdin.read().strip()
    line = entry(key, sys.argv[1], sys.argv[2] == "gateway", core=sys.argv[2] == "core")
    path = Path.home() / ".ssh/authorized_keys"
    original = path.read_text()
    identity = " ".join(key.split()[:2])
    rows = [row for row in original.splitlines() if identity not in row]
    path.write_text("\n".join(rows + [line]) + "\n")
    path.chmod(0o600)
