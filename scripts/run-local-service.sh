#!/usr/bin/env bash
# Carrega as configurações locais sem exibir senhas no terminal.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
service=${1:-}
case "$service" in video|job) ;; *) echo 'Uso: bash scripts/run-local-service.sh video|job' >&2; exit 1 ;; esac
[[ -f "$root/.env" && -f "$root/apps/frontend/.env.local" ]] || { echo 'Configure .env e apps/frontend/.env.local antes de iniciar.' >&2; exit 1; }
set -a
source "$root/.env"
source "$root/apps/frontend/.env.local"
set +a
: "${VITE_AUTH0_DOMAIN:?Configure VITE_AUTH0_DOMAIN}"
: "${VITE_AUTH0_AUDIENCE:?Configure VITE_AUTH0_AUDIENCE}"
export AUTH_ENABLED=true
export AUTH_ISSUER="https://${VITE_AUTH0_DOMAIN}/"
export AUTH_AUDIENCE="$VITE_AUTH0_AUDIENCE"
export STORAGE_ENDPOINT="http://127.0.0.1:${MINIO_API_PORT}"
export STORAGE_PUBLIC_ENDPOINT="$STORAGE_ENDPOINT"
export STORAGE_ACCESS_KEY="$MINIO_ROOT_USER"
export STORAGE_SECRET_KEY="$MINIO_ROOT_PASSWORD"
export VIDEO_SERVICE_URL=http://127.0.0.1:8081
export RABBITMQ_HOST=127.0.0.1
if [[ "$service" == video ]]; then
    export DB_URL="jdbc:postgresql://127.0.0.1:${VIDEO_DB_PORT}/${VIDEO_DB_NAME}"
    export DB_USER="$VIDEO_DB_USER" DB_PASSWORD="$VIDEO_DB_PASSWORD" SERVER_PORT=8081
else
    export DB_URL="jdbc:postgresql://127.0.0.1:${JOB_DB_PORT}/${JOB_DB_NAME}"
    export DB_USER="$JOB_DB_USER" DB_PASSWORD="$JOB_DB_PASSWORD" SERVER_PORT="${JOB_SERVICE_PORT:-8082}"
fi
if [[ -z "${JAVA_HOME:-}" && -d /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ]]; then
    export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
fi
if command -v lsof >/dev/null && lsof -nP -iTCP:"$SERVER_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "A porta $SERVER_PORT está ocupada. Encerre o serviço anterior com Ctrl+C e tente novamente." >&2
    exit 1
fi
if [[ -n "${JAVA_HOME:-}" ]]; then java_bin="$JAVA_HOME/bin/java"; else java_bin=java; fi
"$java_bin" -version >/dev/null 2>&1 || { echo 'Instale e configure o JDK 21.' >&2; exit 1; }
echo "Iniciando $service-service em http://localhost:$SERVER_PORT com Auth0 ativo."
cd "$root/services/video-service"
exec sh mvnw -f "../${service}-service/pom.xml" spring-boot:run
