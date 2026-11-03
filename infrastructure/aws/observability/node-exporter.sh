#!/usr/bin/env bash
set -euo pipefail
: "${NODE_EXPORTER_BIND_HOST:?Configure o host privado}"
: "${MONITORING_PRIVATE_HOST:?Configure o coletor autorizado}"
root=/opt/video-insight/node-exporter
sudo install -d -m 755 "$root/textfile"
printf 'MONITORING_PRIVATE_HOST=%s\n' "$MONITORING_PRIVATE_HOST" | sudo tee "$root/network.env" >/dev/null
sudo chmod 600 "$root/network.env"
new_install=false
if ! command -v prometheus-node-exporter >/dev/null; then
  new_install=true
  sudo systemctl mask prometheus-node-exporter.service >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq --no-install-recommends prometheus-node-exporter >/dev/null
fi
sudo install -d /etc/systemd/system/prometheus-node-exporter.service.d
sudo tee /etc/systemd/system/prometheus-node-exporter.service.d/video-insight.conf >/dev/null <<EOF
[Unit]
After=docker.service
[Service]
EnvironmentFile=$root/network.env
ExecStartPre=+/bin/bash $root/metrics-firewall.sh
ExecStart=
ExecStart=/usr/bin/prometheus-node-exporter --web.listen-address=${NODE_EXPORTER_BIND_HOST}:9100 --collector.textfile.directory=$root/textfile
MemoryMax=64M
CPUQuota=10%
Restart=on-failure
RestartSec=5s
EOF
if "$new_install"; then sudo systemctl unmask prometheus-node-exporter.service >/dev/null; fi
sudo systemctl daemon-reload
sudo systemctl enable prometheus-node-exporter.service >/dev/null
sudo systemctl restart prometheus-node-exporter.service
sleep 2
curl --fail --silent "http://${NODE_EXPORTER_BIND_HOST}:9100/metrics" >/dev/null
