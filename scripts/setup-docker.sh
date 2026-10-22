#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
command -v docker >/dev/null || { echo 'Instale o Docker Desktop e execute este script novamente.' >&2; exit 1; }
docker compose version >/dev/null || { echo 'Docker Compose v2 é necessário.' >&2; exit 1; }
if ! docker info >/dev/null 2>&1; then
    if [[ "$(uname -s)" == Darwin ]]; then
        echo 'Abrindo Docker Desktop; aguardando o daemon...'
        open -a Docker
        for _ in {1..60}; do
            if docker info >/dev/null 2>&1; then break; fi
            sleep 2
        done
    fi
    docker info >/dev/null 2>&1 || { echo 'Inicie o Docker e tente novamente.' >&2; exit 1; }
fi
if [[ ! -f .env ]]; then
    umask 077
    cp .env.example .env
    echo 'Criado .env com valores exclusivos para desenvolvimento local.'
fi
if [[ ! -f apps/frontend/.env.local ]]; then
    umask 077
    cp apps/frontend/.env.example apps/frontend/.env.local
    echo 'Criada configuração pública Auth0 em apps/frontend/.env.local.'
fi
docker compose --env-file .env -f infrastructure/compose.yaml config --quiet
docker compose --env-file .env -f infrastructure/compose.yaml up -d --build --wait --wait-timeout 180 video-db job-db rabbitmq minio
docker compose --env-file .env -f infrastructure/compose.yaml ps
echo 'Dependências prontas. Inicie Video Service, Job Service e frontend em terminais separados.'
