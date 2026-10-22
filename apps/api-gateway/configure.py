"""Renderiza a origem CORS do frontend antes do build de produção."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

origin = os.environ["FRONTEND_ORIGIN"]
parsed = urlparse(origin)
if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
    raise SystemExit("FRONTEND_ORIGIN deve ser uma origem HTTPS, sem caminho")
path = Path(__file__).with_name("krakend.json")
config = json.loads(path.read_text())
config["extra_config"]["security/cors"]["allow_origins"] = [origin.rstrip("/")]
path.write_text(json.dumps(config, indent=2) + "\n")
