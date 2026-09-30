FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --system app && useradd --system --gid app app
WORKDIR /app
COPY pyproject.toml .
COPY src src
RUN pip install --no-cache-dir .
USER app
EXPOSE 8080
CMD ["uvicorn", "processing_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
