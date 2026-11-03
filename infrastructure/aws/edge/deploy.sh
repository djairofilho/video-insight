#!/usr/bin/env bash
# Atualiza somente o proxy; mantém a configuração anterior para recuperação.
set -euo pipefail
config=${1:?configuração obrigatória}
target=/opt/video-insight/edge/proxy.conf
image=nginx:1.29-alpine
docker pull "$image" >/dev/null
docker run --rm -v "$config:/etc/nginx/conf.d/default.conf:ro" "$image" nginx -t
sudo install -d -o ubuntu -g ubuntu /opt/video-insight/edge
previous=false
previous_container=
if [[ -f "$target" ]]; then
  cp "$target" "$target.previous"
  previous=true
fi
# Escreve no mesmo inode para que o bind mount veja a configuração atualizada.
cat "$config" > "$target"
rollback() {
  if [[ -n "$previous_container" ]]; then
    docker rm -f video-insight-edge-proxy >/dev/null 2>&1 || true
    docker rename "$previous_container" video-insight-edge-proxy
    docker start video-insight-edge-proxy >/dev/null
  fi
  if "$previous"; then
    cat "$target.previous" > "$target"
    docker exec video-insight-edge-proxy nginx -s reload || true
  fi
}
trap rollback ERR
if docker container inspect video-insight-edge-proxy >/dev/null 2>&1 && [[ "$(docker inspect -f '{{.HostConfig.LogConfig.Type}}' video-insight-edge-proxy)" != local ]]; then
  previous_container="video-insight-edge-proxy-rollback-$(date -u +%Y%m%dT%H%M%SZ)"
  docker stop video-insight-edge-proxy >/dev/null
  docker rename video-insight-edge-proxy "$previous_container"
fi
if docker container inspect video-insight-edge-proxy >/dev/null 2>&1; then
  docker exec video-insight-edge-proxy nginx -t
  docker exec video-insight-edge-proxy nginx -s reload
else
  docker run -d --name video-insight-edge-proxy --restart unless-stopped \
    --log-driver local --log-opt max-size=10m --log-opt max-file=3 \
    --network host --memory 64m -v "$target:/etc/nginx/conf.d/default.conf:ro" "$image" >/dev/null
fi
sleep 2
curl --fail --silent http://127.0.0.1:8081/health/video >/dev/null
trap - ERR
