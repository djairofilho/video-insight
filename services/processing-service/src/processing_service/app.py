"""API operacional do worker de processamento."""

from fastapi import FastAPI

app = FastAPI(title="Video Insight Processing Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Informa que o processo está apto a receber trabalho."""
    return {"service": "processing-service", "status": "UP"}
