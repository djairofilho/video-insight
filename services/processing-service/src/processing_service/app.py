"""API operacional do worker de processamento."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from processing_service.config import get_settings
from processing_service.domain import ConfigurationError
from processing_service.worker import build_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    worker = None
    if settings.consumer_enabled:
        try:
            worker = build_worker(settings)
        except ConfigurationError as error:
            logger.error("Consumidor desativado: %s", error)
        else:
            await worker.start()
    app.state.worker = worker
    try:
        yield
    finally:
        app.state.worker = None
        if worker is not None:
            await worker.stop()


app = FastAPI(title="Video Insight Processing Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Informa que o processo está apto a receber trabalho."""
    worker = getattr(app.state, "worker", None)
    if worker is None:
        consumer = "disabled"
    else:
        consumer = "connected" if worker.connected else "connecting"
    return {"service": "processing-service", "status": "UP", "consumer": consumer}
