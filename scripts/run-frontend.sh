#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root/apps/frontend"
command -v node >/dev/null && command -v npm >/dev/null || { echo 'Instale Node.js 22.12+ e npm.' >&2; exit 1; }
node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if(major<22 || (major===22 && minor<12)) { console.error("Use Node.js 22.12 ou superior"); process.exit(1) }'
if [[ ! -f .env.local ]]; then
    umask 077
    cp .env.example .env.local
    echo 'Criado apps/frontend/.env.local com a configuração pública Auth0 deste projeto.'
fi
if command -v lsof >/dev/null && lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    echo 'A porta 5173 está ocupada. Encerre o frontend anterior com Ctrl+C e tente novamente.' >&2
    exit 1
fi
npm ci
exec npm run dev:local -- --port 5173 --strictPort
