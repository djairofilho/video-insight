"""Carga autenticada de consultas; não cria jobs nem consome provedores de IA."""

import argparse
import json
import math
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx


def measure(client, url, requests, workers):
    def query(_):
        started = time.perf_counter()
        try:
            response = client.get(url)
            return response.status_code, (time.perf_counter() - started) * 1000
        except httpx.HTTPError:
            return 0, (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        samples = list(pool.map(query, range(requests)))
    elapsed = time.perf_counter() - started
    timings = sorted(duration for _, duration in samples)
    return {
        "requests": requests, "workers": workers, "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(requests / elapsed, 2),
        "status_counts": dict(Counter(str(status) for status, _ in samples)),
        "errors": sum(status < 200 or status >= 300 for status, _ in samples),
        "p50_ms": round(timings[math.ceil(len(timings) * .5) - 1], 2),
        "p95_ms": round(timings[math.ceil(len(timings) * .95) - 1], 2),
        "max_ms": round(timings[-1], 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL completa de listagem de vídeos ou consulta de um job de teste")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.requests <= 1000 or not 1 <= args.workers <= 20:
        parser.error("Use 1 a 1000 requisições e 1 a 20 clientes concorrentes.")
    token = os.environ.get("E2E_ACCESS_TOKEN")
    if not token:
        parser.error("Defina E2E_ACCESS_TOKEN; não passe tokens pela linha de comando.")
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        result = measure(client, args.url, args.requests, args.workers)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)
