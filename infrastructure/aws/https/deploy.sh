#!/usr/bin/env bash
set -euo pipefail
source_config=${1:?Caddyfile obrigatório}
compose=${2:?Compose obrigatório}
target=/opt/video-insight/https
chmod 600 "$source_config"
docker pull caddy:2.11.7-alpine >/dev/null
docker run --rm -v "$source_config:/etc/caddy/Caddyfile:ro" caddy:2.11.7-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo install -d -o ubuntu -g ubuntu "$target"
if [[ -f "$target/Caddyfile" ]]; then
  sudo cp "$target/Caddyfile" "$target/Caddyfile.previous"
  sudo chmod 600 "$target/Caddyfile.previous"
fi
sudo touch "$target/Caddyfile"
sudo chown root:root "$target/Caddyfile"
sudo chmod 600 "$target/Caddyfile"
sudo tee "$target/Caddyfile" < "$source_config" >/dev/null
cp "$compose" "$target/compose.yaml"
cd "$target"
if sudo ufw status | grep -q 'Status: active'; then
  sudo ufw allow 80/tcp >/dev/null
  sudo ufw allow 443/tcp >/dev/null
  if grep -q ':8081 {' "$source_config"; then sudo ufw allow 8081/tcp >/dev/null; fi
fi
docker compose up -d
docker compose exec -T https caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
