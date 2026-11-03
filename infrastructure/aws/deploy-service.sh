#!/usr/bin/env bash
# Substitui apenas o contêiner da aplicação e preserva o anterior para rollback.
set -euo pipefail
component=${1:?componente obrigatório}
image=${2:?imagem obrigatória}
env_file=${3:?arquivo de ambiente obrigatório}
case "$component" in
  video|job) memory=512m; health=/health ;;
  processing) memory=512m; health=/health ;;
  gateway) memory=256m; health=/health/video ;;
  *) echo 'Componente inválido' >&2; exit 2 ;;
esac
port=8081
binding=8081:8080
if [[ "$component" == gateway ]]; then
  port=8082
  binding=127.0.0.1:8082:8080
fi
name="video-insight-$component"
backup="$name-rollback-$(date -u +%Y%m%dT%H%M%SZ)"
had_previous=false
docker image inspect "$image" >/dev/null
test -f "$env_file"
if docker container inspect "$name" >/dev/null 2>&1; then
  docker stop "$name" >/dev/null
  if ! docker rename "$name" "$backup"; then
    docker start "$name" >/dev/null
    exit 1
  fi
  had_previous=true
fi
rollback() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  if "$had_previous"; then
    docker rename "$backup" "$name"
    docker start "$name" >/dev/null
  fi
}
trap rollback ERR
extra_args=()
if [[ "$component" == processing ]]; then
  extra_args+=(--mount type=volume,src=video-insight-provider-budget,dst=/var/lib/video-insight)
fi
if [[ "$component" == gateway ]]; then
  metrics_bind=$(awk -F= '$1 == "METRICS_BIND_HOST" {print substr($0,index($0,"=")+1)}' "$env_file")
  [[ "$metrics_bind" =~ ^[0-9.]+$ ]]
  extra_args+=(-p "${metrics_bind}:9091:9091")
fi
docker run -d --name "$name" --restart unless-stopped --memory "$memory" \
  --log-driver local --log-opt max-size=10m --log-opt max-file=3 \
  "${extra_args[@]}" \
  --env-file "$env_file" -p "$binding" "$image" >/dev/null
healthy=false
for _ in {1..40}; do
  if curl --fail --silent "http://127.0.0.1:$port$health" >/dev/null; then
    healthy=true
    break
  fi
  sleep 3
done
test "$healthy" = true
if [[ "$component" == video || "$component" == job || "$component" == gateway ]]; then
  path=/api/v1/videos
  [[ "$component" != job ]] || path=/api/v1/jobs/00000000-0000-0000-0000-000000000000
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:$port$path")
  test "$status" = 401
fi
if [[ "$component" == processing ]]; then
  curl --fail --silent http://127.0.0.1:8081/health | grep -q '"consumer":"connected"'
fi
# Uma aplicação que reinicia logo após o primeiro health check ainda não está estável.
restarts=$(docker inspect -f '{{.RestartCount}}' "$name")
sleep 10
curl --fail --silent "http://127.0.0.1:$port$health" >/dev/null
test "$(docker inspect -f '{{.RestartCount}}' "$name")" = "$restarts"
trap - ERR
echo "Implantado: $image. Rollback disponível: $backup"
