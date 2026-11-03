"""Carga real e limitada: upload direto, fila e três operações de IA.

O orçamento persistente do worker deve estar ativo. Este cliente não altera
planos, credenciais, limites do servidor nem repete jobs que falharam.
"""
import argparse
import hashlib
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

TERMINAL = {"completed", "failed", "cancelled"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def check_cases(root, manifest):
    """Rejeita arquivos alterados, maiores que 100 MiB ou acima de 10 min."""
    root = Path(root).resolve()
    cases = []
    for item in manifest["cases"]:
        path = (root / item["filename"]).resolve()
        if path.parent != root or not path.is_file():
            raise ValueError("Arquivo fora da pasta de mídia ou ausente")
        if not 0 < item["duration_seconds"] <= 600 or not 0 < path.stat().st_size <= 104857600:
            raise ValueError("Mídia fora dos limites da aplicação")
        if path.stat().st_size != item["size_bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("A mídia não corresponde ao manifesto revisado")
        cases.append(dict(item, path=path))
    if not cases:
        raise ValueError("Manifesto sem casos")
    return cases


class Evidence:
    def __init__(self, path):
        self.stream = open(path, "x", encoding="utf-8", buffering=1)
        self.lock = threading.Lock()

    def emit(self, kind, **fields):
        with self.lock:
            self.stream.write(json.dumps(dict(at_utc=utc_now(), event=kind, **fields), ensure_ascii=False) + "\n")


class Run:
    def __init__(self, client, args, cases, evidence):
        self.client, self.args, self.cases, self.evidence = client, args, cases, evidence
        self.started = time.monotonic()
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.submitted = 0
        self.audio_seconds = 0
        self.stop_reason = None
        self.run_id = "real-load-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]

    def elapsed(self):
        return time.monotonic() - self.started

    def halt(self, reason):
        with self.lock:
            if not self.stop.is_set():
                self.stop_reason = reason
                self.evidence.emit("injection_stopped", elapsed_seconds=self.elapsed(), reason=reason)
                self.stop.set()

    def request(self, method, path, **kwargs):
        response = self.client.request(method, self.args.base_url.rstrip("/") + path, **kwargs)
        if not response.is_success:
            # Nunca inclui corpo, headers, URL assinada ou bearer em exceções/evidências.
            raise RuntimeError("api_http_" + str(response.status_code))
        return response.json() if response.content else {}

    def next_case(self):
        stop_file = getattr(self.args, "stop_file", None)
        if stop_file and stop_file.exists():
            self.halt("monitor_guard")
            return None
        with self.lock:
            if self.stop.is_set() or self.elapsed() >= self.args.window_seconds - self.args.stop_before_end_seconds:
                return None
            if self.submitted >= self.args.max_jobs:
                return None
            case = self.cases[self.submitted % len(self.cases)]
            if self.audio_seconds + case["duration_seconds"] > self.args.max_audio_seconds:
                return None
            self.submitted += 1
            self.audio_seconds += case["duration_seconds"]
            return self.submitted, case

    def pipeline(self, number, case):
        started = self.elapsed()
        video_id = job_id = None
        event = dict(sequence=number, case=case["filename"], duration_seconds=case["duration_seconds"])
        self.evidence.emit("case_started", **event, elapsed_seconds=started)
        try:
            video_id = self.request("POST", "/api/v1/videos", json={"file_name": f"{self.run_id}-{number}.mp4",
                "content_type": "video/mp4", "size_bytes": case["size_bytes"]})["id"]
            self.evidence.emit("video_created", **event, video_id=video_id, elapsed_seconds=self.elapsed())
            signed = self.request("POST", f"/api/v1/videos/{video_id}/upload-url")
            if urlsplit(signed["url"]).scheme != "https":
                raise RuntimeError("storage_requires_https")
            upload_start = self.elapsed()
            # Cliente separado: o token Auth0 nunca é transmitido ao storage.
            response = httpx.put(signed["url"], content=case["path"].read_bytes(),
                headers=signed.get("headers") or {}, timeout=180)
            if not response.is_success:
                raise RuntimeError("storage_http_" + str(response.status_code))
            upload_seconds = self.elapsed() - upload_start
            video = self.request("POST", f"/api/v1/videos/{video_id}/upload-complete",
                json={"duration_seconds": case["duration_seconds"]})
            if video.get("upload_status") != "ready":
                raise RuntimeError("upload_not_ready")
            job = self.request("POST", f"/api/v1/videos/{video_id}/jobs",
                json={"operations": ["transcription", "summary", "chapters"]},
                headers={"Idempotency-Key": self.run_id + "-" + str(number)})
            job_id = job["id"]
            self.evidence.emit("job_submitted", **event, video_id=video_id, job_id=job_id,
                elapsed_seconds=self.elapsed(), upload_seconds=upload_seconds,
                upload_transaction_seconds=self.elapsed() - started)
            last_state = None
            while self.elapsed() < self.args.window_seconds + self.args.drain_seconds:
                job = self.request("GET", f"/api/v1/jobs/{job_id}")
                state = tuple(str(job.get(k)) for k in ("status", "stage", "progress_percent", "attempt"))
                if state != last_state:
                    fields = {k: job.get(k) for k in ("status", "stage", "progress_percent", "attempt", "created_at", "updated_at")}
                    self.evidence.emit("job_state", sequence=number, elapsed_seconds=self.elapsed(), **fields)
                    last_state = state
                if job["status"] in TERMINAL:
                    valid = None
                    if job["status"] == "completed":
                        result = self.request("GET", f"/api/v1/jobs/{job_id}/result")
                        valid = bool(result.get("transcript") and result.get("summary") and result.get("chapters"))
                        self.evidence.emit("result_checked", sequence=number, elapsed_seconds=self.elapsed(),
                            valid=valid, transcript_segments=len(result.get("transcript") or []),
                            summary_characters=len(result.get("summary") or ""),
                            chapter_count=len(result.get("chapters") or []), models=result.get("models"))
                    self.evidence.emit("case_finished", **event, status=job["status"], valid=valid,
                        elapsed_seconds=self.elapsed(), end_to_end_seconds=self.elapsed() - started,
                        inside_window=self.elapsed() <= self.args.window_seconds)
                    if job["status"] != "completed" or not valid:
                        # Interrompe novas admissões no primeiro erro; jobs em execução podem drenar.
                        error = job.get("error")
                        error_code = error.get("code") if isinstance(error, dict) else None
                        self.evidence.emit("failure_code", sequence=number, code=error_code)
                        self.halt("job_failed_or_invalid_result")
                    return
                time.sleep(self.args.poll_seconds)
            self.evidence.emit("case_pending", **event, elapsed_seconds=self.elapsed())
            self.halt("drain_deadline")
        except (httpx.HTTPError, RuntimeError, KeyError) as error:
            reason = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            self.evidence.emit("client_error", sequence=number, elapsed_seconds=self.elapsed(), reason=reason,
                video_id=video_id, job_id=job_id)
            self.halt("client_error")

    def worker(self):
        while (item := self.next_case()) is not None:
            self.pipeline(*item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--media-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--window-seconds", type=int, default=3600)
    parser.add_argument("--stop-before-end-seconds", type=int, default=300)
    parser.add_argument("--drain-seconds", type=int, default=600)
    parser.add_argument("--max-jobs", type=int, default=18)
    parser.add_argument("--max-audio-seconds", type=int, default=5400)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args()
    if not (1 <= args.window_seconds <= 3600 and 1 <= args.max_jobs <= 24 and
            1 <= args.max_audio_seconds <= 5400 and 1 <= args.concurrency <= 2 and
            0 <= args.stop_before_end_seconds < args.window_seconds and 1 <= args.poll_seconds <= 30 and
            0 <= args.drain_seconds <= 600):
        parser.error("Parâmetros fora do envelope gratuito revisado")
    token = os.environ.get("E2E_ACCESS_TOKEN")
    if not token or urlsplit(args.base_url).scheme != "https":
        parser.error("Defina E2E_ACCESS_TOKEN no ambiente e use HTTPS")
    manifest = json.loads((args.media_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    cases = check_cases(args.media_dir, manifest)
    evidence = Evidence(args.output)
    with httpx.Client(headers={"Authorization": "Bearer " + token}, timeout=45) as client:
        run = Run(client, args, cases, evidence)
        evidence.emit("run_started", run_id=run.run_id, window_seconds=args.window_seconds,
            concurrency=args.concurrency, max_jobs=args.max_jobs, max_audio_seconds=args.max_audio_seconds,
            media_manifest=manifest, tools={"driver": "Python/httpx", "httpx": httpx.__version__})
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(run.worker) for _ in range(args.concurrency)]
            while run.elapsed() < args.window_seconds:
                if args.stop_file and args.stop_file.exists():
                    run.halt("monitor_guard")
                print(json.dumps({"elapsed_seconds": round(run.elapsed()), "admitted": run.submitted,
                    "audio_minutes_admitted": round(run.audio_seconds / 60, 2), "injection_stopped": run.stop.is_set()}), flush=True)
                time.sleep(min(30, max(0.01, args.window_seconds - run.elapsed())))
            evidence.emit("measurement_window_ended", elapsed_seconds=run.elapsed())
            for future in futures:
                future.result()
        evidence.emit("run_ended", elapsed_seconds=run.elapsed(), admitted=run.submitted,
            audio_seconds_admitted=run.audio_seconds, stop_reason=run.stop_reason)
    evidence.stream.close()


if __name__ == "__main__":
    main()
