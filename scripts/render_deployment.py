"""Gera configurações de implantação com hosts fornecidos por secrets do ambiente."""

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

PROFILES = {
    "frontend": ["apps/frontend/vercel.json"],
    "gateway": ["apps/api-gateway/krakend.json"],
    "edge": ["infrastructure/aws/edge/proxy.conf"],
    "observability": ["infrastructure/aws/observability/prometheus.yml"],
    "tunnels": [f"infrastructure/aws/tunnels/{service}-service-tunnel.service"
                for service in ("video", "job", "processing")],
}
EXAMPLES = {key: "localhost" for key in (
    "AWS_GATEWAY_HOST", "AWS_VIDEO_PRIVATE_HOST", "AWS_JOB_PRIVATE_HOST",
    "AWS_PROCESSING_PRIVATE_HOST", "AWS_CORE_PRIVATE_HOST", "AWS_DOCKER_BRIDGE_HOST",
)}
EXAMPLES.update(FRONTEND_ORIGIN="https://frontend.example",
                STORAGE_PUBLIC_ENDPOINT="http://localhost:8081")
PLACEHOLDER = re.compile(r"__([A-Z][A-Z0-9_]+)__")


def value(key, environment):
    if key == "STORAGE_AUTHORITY":
        return urlsplit(value("STORAGE_PUBLIC_ENDPOINT", environment)).netloc
    raw = environment.get(key, "").strip()
    if not raw:
        raise ValueError(f"Configure o secret {key}")
    if key.endswith("_HOST"):
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", raw):
            raise ValueError(f"{key} deve conter somente um hostname ou endereço IPv4")
    elif key in ("FRONTEND_ORIGIN", "STORAGE_PUBLIC_ENDPOINT"):
        parsed = urlsplit(raw)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or any(c.isspace() for c in raw)):
            raise ValueError(f"{key} deve ser uma origem HTTP(S) sem credenciais ou caminho")
        if key == "FRONTEND_ORIGIN" and parsed.scheme != "https":
            raise ValueError("FRONTEND_ORIGIN deve usar HTTPS")
        if not re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname):
            raise ValueError(f"Host inválido em {key}")
        parsed.port  # Valida a porta sem incluí-la em mensagens de erro.
        raw = raw.rstrip("/")
    else:
        raise ValueError(f"Parâmetro de implantação desconhecido: {key}")
    return raw


def render(profiles, project_root, environment):
    pending = []
    for profile in profiles:
        for relative in PROFILES[profile]:
            target = project_root / relative
            source = Path(str(target) + ".template")
            content = PLACEHOLDER.sub(lambda match: value(match[1], environment),
                                      source.read_text(encoding="utf8"))
            if target.suffix == ".json":
                json.loads(content)
            pending.append((target, content))
    for target, content in pending:
        target.write_text(content, encoding="utf8")
    return len(pending)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="+", choices=PROFILES)
    parser.add_argument("--example", action="store_true", help="Usa somente hosts locais para validação")
    args = parser.parse_args()
    try:
        count = render(args.profiles, Path(__file__).resolve().parents[1], EXAMPLES if args.example else os.environ)
    except ValueError as error:
        parser.error(str(error))
    print(f"Configurações geradas: {count}; valores de hosts não são exibidos.")
