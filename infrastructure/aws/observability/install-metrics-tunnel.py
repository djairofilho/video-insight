"""Instala no monitor um túnel de métricas com chave e host previamente verificados."""

import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path

PORTS = {"gateway": 19101, "video": 19102, "processing": 19103, "core": 19104}


def unit(role, host, bridge, monitor_host=None):
    ipaddress.ip_address(host)
    ipaddress.ip_address(bridge)
    port = PORTS[role]
    forwards = f"-L {bridge}:{port}:{host}:9100"
    if role == "gateway":
        forwards += f" -L {bridge}:19111:{host}:9091"
    if role == "core":
        ipaddress.ip_address(monitor_host)
        forwards += f" -R 127.0.0.1:13000:127.0.0.1:3000 -R 127.0.0.1:19090:{monitor_host}:9090"
    return f"""[Unit]
Description=Video Insight metrics tunnel ({role})
After=network-online.target docker.service
Wants=network-online.target
[Service]
ExecStart=/usr/bin/ssh -NT -i /etc/video-insight/metrics_ed25519 -o BatchMode=yes -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/video-insight/metrics_known_hosts -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ConnectTimeout=10 {forwards} ubuntu@{host}
Restart=always
RestartSec=5
MemoryMax=32M
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
"""


if __name__ == "__main__":
    role = sys.argv[1]
    host, bridge = os.environ["TARGET_PRIVATE_HOST"], os.environ["AWS_DOCKER_BRIDGE_HOST"]
    content = unit(role, host, bridge, os.environ.get("AWS_JOB_PRIVATE_HOST"))
    host_key = sys.stdin.read().strip()
    if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?", host_key):
        raise ValueError("Host key inválida")
    known = Path("/etc/video-insight/metrics_known_hosts")
    rows = known.read_text().splitlines() if known.exists() else []
    rows = [row for row in rows if not row.startswith(host + " ")]
    known.write_text("\n".join(rows + [host + " " + host_key]) + "\n")
    known.chmod(0o600)
    name = f"video-insight-metrics-{role}.service"
    Path("/etc/systemd/system", name).write_text(content)
    # O Prometheus usa a rede do Compose, que pode ser diferente de docker0.
    import json
    container = json.loads(subprocess.check_output(["docker", "inspect", "video-insight-observability-prometheus-1"]))[0]
    for network_name in container["NetworkSettings"]["Networks"]:
        net = json.loads(subprocess.check_output(["docker", "network", "inspect", network_name]))[0]
        interface = net.get("Options", {}).get("com.docker.network.bridge.name", "br-" + net["Id"][:12])
        for config in net["IPAM"]["Config"]:
            network = config["Subnet"]
            if ipaddress.ip_network(network).version != 4:
                continue
            for port in [PORTS[role]] + ([19111] if role == "gateway" else []):
                subprocess.run(["ufw", "allow", "in", "on", interface, "from", network,
                                "to", bridge, "port", str(port), "proto", "tcp"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", name], check=True)
    subprocess.run(["systemctl", "restart", name], check=True)
