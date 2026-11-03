#!/usr/bin/env bash
# Simula falha da nova imagem e verifica que o contêiner anterior é restaurado.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
mkdir "$scratch/bin"
touch "$scratch/runtime.env"
export DEPLOY_TEST_LOG="$scratch/calls"
cat > "$scratch/bin/docker" <<'MOCK'
#!/usr/bin/env bash
echo "docker $*" >> "$DEPLOY_TEST_LOG"
if [[ "$1" == rename && "${FAIL_RENAME:-false}" == true ]]; then exit 18; fi
if [[ "$1" == run ]]; then exit 17; fi
exit 0
MOCK
chmod +x "$scratch/bin/docker"
if PATH="$scratch/bin:$PATH" bash "$root/deploy-service.sh" video test:broken "$scratch/runtime.env"; then
  echo 'A implantação inválida não pode ser considerada concluída' >&2
  exit 1
fi
grep -q '^docker stop video-insight-video$' "$DEPLOY_TEST_LOG"
grep -q '^docker rm -f video-insight-video$' "$DEPLOY_TEST_LOG"
grep -Eq '^docker rename video-insight-video-rollback-[^ ]+ video-insight-video$' "$DEPLOY_TEST_LOG"
grep -q '^docker start video-insight-video$' "$DEPLOY_TEST_LOG"
echo 'Rollback após falha de inicialização: OK'
: > "$DEPLOY_TEST_LOG"
if FAIL_RENAME=true PATH="$scratch/bin:$PATH" bash "$root/deploy-service.sh" video test:broken "$scratch/runtime.env"; then
  exit 1
fi
grep -q '^docker start video-insight-video$' "$DEPLOY_TEST_LOG"
if grep -q '^docker rm ' "$DEPLOY_TEST_LOG"; then
  echo 'O contêiner anterior não pode ser apagado quando seu rename falha' >&2
  exit 1
fi
echo 'Recuperação após falha de rename: OK'
