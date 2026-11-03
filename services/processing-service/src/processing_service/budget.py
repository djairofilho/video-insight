"""Orçamento conservador compartilhado, persistente e reservado antes da chamada."""

import sqlite3
import time
from collections import deque
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Condition

from processing_service.config import Settings
from processing_service.domain import ProcessingError
from processing_service.metrics import METRICS


@dataclass(frozen=True)
class _BudgetDelay:
    seconds: float
    period_seconds: int
    measure: str


class ProviderBudget:
    def __init__(self, path: str, limits: dict[str, tuple[tuple[int, str, int], ...]], *,
                 clock=time.time, sleep=time.sleep, max_wait_seconds=0):
        self.path = path
        self.limits = limits
        self.clock = clock
        self.sleep = sleep
        self.max_wait_seconds = max_wait_seconds
        self._admission = {provider: (Condition(), deque()) for provider in limits}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS usage (ts REAL NOT NULL, provider TEXT NOT NULL, units REAL NOT NULL, tokens INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS usage_provider_ts ON usage(provider, ts)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    def report_metrics(self) -> None:
        now = self.clock()
        with closing(self._connect()) as db:
            for provider, limits in self.limits.items():
                for seconds, measure, limit in limits:
                    count, units, tokens = db.execute(
                        "SELECT COUNT(*), COALESCE(SUM(units),0), COALESCE(SUM(tokens),0) FROM usage WHERE provider=? AND ts>?",
                        (provider, now - seconds),
                    ).fetchone()
                    used = {"requests": count, "units": units, "tokens": tokens}[measure]
                    labels = (provider, str(seconds), measure)
                    METRICS.budget_remaining.labels(*labels).set(max(0, limit - used))
                    METRICS.budget_limit.labels(*labels).set(limit)

    def reserve(self, provider: str, *, units: float = 0, tokens: int = 0) -> None:
        started = time.monotonic()
        condition, queue = self._admission[provider]
        ticket = object()
        with condition:
            queue.append(ticket)
        try:
            # A reserva que já espera recebe a próxima vaga. Não mantém uma
            # transação SQLite aberta nem bloqueia a fila de outro provedor.
            with condition:
                while queue[0] is not ticket:
                    condition.wait()
            self._reserve_in_turn(provider, units=units, tokens=tokens)
        finally:
            with condition:
                queue.remove(ticket)
                condition.notify_all()
            METRICS.budget_wait.labels(provider).observe(time.monotonic() - started)

    def _reserve_in_turn(self, provider: str, *, units: float, tokens: int) -> None:
        deadline = time.monotonic() + self.max_wait_seconds
        while True:
            wait = self._reserve_once(provider, units=units, tokens=tokens)
            if wait is None:
                return
            if wait.seconds > deadline - time.monotonic():
                self._reject(provider, wait.period_seconds, wait.measure, 'wait_timeout')
            self.sleep(wait.seconds)

    @staticmethod
    def _reject(provider, period_seconds, measure, reason):
        METRICS.budget_rejections.labels(provider).inc()
        METRICS.budget_rejection_reasons.labels(provider, str(period_seconds), measure, reason).inc()
        raise ProcessingError("provider_budget_exhausted",
                              "Orçamento gratuito reservado esgotado; aguarde a renovação para tentar novamente.",
                              retryable=True)

    def _reserve_once(self, provider: str, *, units: float, tokens: int) -> _BudgetDelay | None:
        now = self.clock()
        try:
            with closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM usage WHERE ts <= ?", (now - 86400,))
                for seconds, measure, limit in self.limits[provider]:
                    count, total_units, total_tokens = db.execute(
                        "SELECT COUNT(*), COALESCE(SUM(units),0), COALESCE(SUM(tokens),0) FROM usage WHERE provider=? AND ts>?",
                        (provider, now - seconds),
                    ).fetchone()
                    proposed = {"requests": count + 1, "units": total_units + units,
                                "tokens": total_tokens + tokens}[measure]
                    if proposed > limit:
                        oldest = db.execute("SELECT MIN(ts) FROM usage WHERE provider=? AND ts>?",
                                            (provider, now - seconds)).fetchone()[0]
                        db.rollback()
                        incoming = {"requests": 1, "units": units, "tokens": tokens}[measure]
                        if seconds <= 60 and incoming <= limit and oldest is not None:
                            return _BudgetDelay(max(.05, oldest + seconds - now + .05), seconds, measure)
                        reason = 'request_exceeds_limit' if incoming > limit else 'window_exhausted'
                        self._reject(provider, seconds, measure, reason)
                db.execute("INSERT INTO usage VALUES (?,?,?,?)", (now, provider, units, tokens))
                db.commit()
        except sqlite3.Error as error:
            # Falha fechada: indisponibilidade do controle nunca libera chamadas sem orçamento.
            raise ProcessingError("provider_budget_unavailable", "Controle de consumo indisponível.",
                                  retryable=True) from error


@lru_cache(maxsize=8)
def _shared(path, audio_hour, audio_day, groq_minute, gemini_minute, gemini_day, tokens_minute):
    return ProviderBudget(path, {
        "groq": ((3600, "units", audio_hour), (86400, "units", audio_day), (60, "requests", groq_minute)),
        "google": ((60, "requests", gemini_minute), (86400, "requests", gemini_day), (60, "tokens", tokens_minute)),
    }, max_wait_seconds=65)


def get_budget(settings: Settings) -> ProviderBudget | None:
    if not settings.provider_budget_enabled:
        return None
    return _shared(settings.provider_budget_path, settings.groq_audio_seconds_per_hour,
                   settings.groq_audio_seconds_per_day, settings.groq_requests_per_minute,
                   settings.gemini_requests_per_minute, settings.gemini_requests_per_day,
                   settings.gemini_tokens_per_minute)
