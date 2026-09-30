FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache ffmpeg
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY pyproject.toml .
COPY src src
RUN pip install --no-cache-dir .
USER app
EXPOSE 8080
CMD ["uvicorn", "processing_service.app:app", "--host", "0.0.0.0", "--port", "8080"]
