#!/usr/bin/env bash
# Executado por SSH na EC2 Ubuntu com Docker já instalado.
set -euo pipefail
image=${1:?Informe a imagem}
port=${2:-8081}
[[ "$image" =~ ^video-insight/frontend:[a-f0-9]{40}$ ]] || { echo 'Imagem inválida' >&2; exit 1; }
[[ "$port" =~ ^[0-9]+$ ]] && ((port >= 1024 && port <= 65535)) || { echo 'Porta inválida' >&2; exit 1; }
name=video-insight-frontend
candidate=video-insight-frontend-candidate
backup=video-insight-frontend-previous
swapping=false
had_previous=false

check_routes() {
    local base=$1
    curl --fail --silent --max-time 5 "$base/health" | grep -qx ok || return 1
    for route in / /login /videos /jobs/example/result; do
        curl --fail --silent --max-time 5 "$base$route" | grep -q 'id="root"' || return 1
    done
    test "$(curl --silent --max-time 5 --output /dev/null --write-out '%{http_code}' "$base/assets/missing.js")" = 404
}

cleanup() {
    local status=$?
    trap - EXIT
    sudo docker rm -f "$candidate" >/dev/null 2>&1 || true
    if [[ "$status" != 0 && "$swapping" == true ]]; then
        sudo docker rm -f "$name" >/dev/null 2>&1 || true
        if [[ "$had_previous" == true ]]; then
            sudo docker rename "$backup" "$name"
            sudo docker start "$name" >/dev/null
        fi
        echo 'Deploy falhou; contêiner anterior restaurado quando disponível.' >&2
    fi
    exit "$status"
}
trap cleanup EXIT

# Não sobrescreve um backup deixado por uma execução interrompida.
if sudo docker container inspect "$backup" >/dev/null 2>&1; then
    echo "Existe um backup $backup; confira o deploy anterior antes de continuar." >&2
    exit 1
fi
sudo docker run --rm "$image" nginx -t
sudo docker run -d --name "$candidate" --memory 128m -p 127.0.0.1::80 "$image" >/dev/null
candidate_port=$(sudo docker port "$candidate" 80/tcp | awk -F: '{print $NF}')
ready=false
for _ in {1..20}; do
    if check_routes "http://127.0.0.1:$candidate_port"; then ready=true; break; fi
    sleep 2
done
[[ "$ready" == true ]]
sudo docker rm -f "$candidate" >/dev/null

if sudo docker container inspect "$name" >/dev/null 2>&1; then
    sudo docker rename "$name" "$backup"
    had_previous=true
fi
swapping=true
if [[ "$had_previous" == true ]]; then sudo docker stop "$backup" >/dev/null; fi
sudo docker run -d --name "$name" --restart unless-stopped --memory 128m -p "$port:80" "$image" >/dev/null
ready=false
for _ in {1..20}; do
    if check_routes "http://127.0.0.1:$port"; then ready=true; break; fi
    sleep 2
done
[[ "$ready" == true ]]
swapping=false
if [[ "$had_previous" == true ]]; then sudo docker rm "$backup" >/dev/null; fi
echo 'Frontend publicado e rotas verificadas.'
