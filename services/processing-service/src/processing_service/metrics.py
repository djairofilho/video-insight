"""Métricas agregadas, sem identificadores de usuários, jobs ou endereços."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class ProcessingMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.jobs = Counter("video_insight_jobs", "Jobs executados", ["outcome"], registry=self.registry)
        self.active = Gauge("video_insight_jobs_active", "Jobs em execução", registry=self.registry)
        self.duration = Histogram("video_insight_job_duration_seconds", "Ocupação do worker por job",
                                  buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200), registry=self.registry)
        self.queue_wait = Histogram("video_insight_queue_wait_seconds", "Tempo desde a publicação do pedido",
                                    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1800), registry=self.registry)
        self.stages = Histogram("video_insight_stage_duration_seconds", "Tempo por etapa",
                                ["stage"], buckets=(.1, .5, 1, 5, 15, 30, 60, 120, 300, 600),
                                registry=self.registry)
        self.audio = Counter("video_insight_processed_audio_seconds", "Áudio de jobs concluídos",
                             registry=self.registry)
        self.providers = Counter("video_insight_provider_requests", "Tentativas externas",
                                 ["provider", "outcome"], registry=self.registry)
        self.budget_rejections = Counter("video_insight_budget_rejections", "Chamadas impedidas pelo orçamento",
                                         ["provider"], registry=self.registry)
        self.budget_rejection_reasons = Counter("video_insight_budget_rejection_reasons", "Motivo do bloqueio local",
            ["provider", "period_seconds", "measure", "reason"], registry=self.registry)
        self.budget_wait = Histogram("video_insight_budget_wait_seconds", "Espera local pela admissão no provedor",
            ["provider"], buckets=(.1, 1, 5, 15, 30, 60, 90, 120, 180), registry=self.registry)
        self.checkpoints = Counter("video_insight_checkpoint_hits", "Etapas reaproveitadas", ["stage"],
                                   registry=self.registry)
        self.tokens = Counter("video_insight_provider_tokens", "Tokens reportados pelo provedor",
                              ["provider"], registry=self.registry)
        self.budget_remaining = Gauge("video_insight_budget_remaining", "Saldo do orçamento local",
                                      ["provider", "period_seconds", "measure"], registry=self.registry)
        self.budget_limit = Gauge("video_insight_budget_limit", "Limite do orçamento local",
                                  ["provider", "period_seconds", "measure"], registry=self.registry)
        for outcome in ("completed", "failed", "replayed"):
            self.jobs.labels(outcome).inc(0)
        for stage in ("downloading", "extracting_audio", "transcribing", "summarizing", "creating_chapters", "uploading_artifacts"):
            self.stages.labels(stage)
        for provider in ("groq", "google"):
            self.budget_rejections.labels(provider).inc(0)
            self.budget_wait.labels(provider)
            for outcome in ("success", "error", "network_error"):
                self.providers.labels(provider, outcome).inc(0)

    def render(self) -> bytes:
        return generate_latest(self.registry)


METRICS = ProcessingMetrics()
