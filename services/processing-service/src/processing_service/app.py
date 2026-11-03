"""API operacional do worker de processamento."""

import logging
import ipaddress
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response

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


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    """Expõe a conectividade do consumidor apenas à rede interna e ao host local."""
    try:
        address = ipaddress.ip_address(request.client.host if request.client else "")
    except ValueError:
        raise HTTPException(status_code=403)
    networks = get_settings().metrics_allowed_networks.split(",")
    if not (address.is_loopback or any(address in ipaddress.ip_network(network.strip())
                                      for network in networks if network.strip())):
        raise HTTPException(status_code=403)
    worker = getattr(app.state, "worker", None)
    connected = int(worker is not None and worker.connected)
    return Response(
        "# HELP video_insight_worker_connected Conexão com RabbitMQ disponível.\n"
        "# TYPE video_insight_worker_connected gauge\n"
        f"video_insight_worker_connected {connected}\n",
        media_type="text/plain; version=0.0.4",
    )
