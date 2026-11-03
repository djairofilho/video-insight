import asyncio

from processing_service.config import Settings
from processing_service.content_intelligence.factory import create_content_writers
from processing_service.domain import ConfigurationError
from processing_service.media.ffmpeg import FfmpegMedia
from processing_service.messaging.rabbitmq import RabbitMQWorker
from processing_service.pipeline import ProcessingPipeline
from processing_service.storage import MinioStorage
from processing_service.transcription.factory import create_transcriber


def build_pipeline(settings: Settings) -> ProcessingPipeline:
    summarizer, chapter_writer = create_content_writers(settings)
    return ProcessingPipeline(
        settings=settings,
        storage=MinioStorage.from_settings(settings),
        media=FfmpegMedia(settings.ffmpeg_timeout_seconds),
        transcriber=create_transcriber(settings),
        summarizer=summarizer,
        chapter_writer=chapter_writer,
    )


class WorkerPool:
    def __init__(self, workers: list[RabbitMQWorker]) -> None:
        self.workers = workers

    @property
    def connected(self) -> bool:
        return all(worker.connected for worker in self.workers)

    async def start(self) -> None:
        for worker in self.workers:
            await worker.start()

    async def stop(self) -> None:
        await asyncio.gather(*(worker.stop() for worker in self.workers))


def build_worker(settings: Settings) -> RabbitMQWorker | WorkerPool:
    if not settings.rabbitmq_password.get_secret_value():
        raise ConfigurationError("RABBITMQ_PASSWORD não foi definido")
    if settings.worker_concurrency == 1:
        return RabbitMQWorker(settings, build_pipeline(settings).run)
    workers = []
    for index in range(settings.worker_concurrency):
        isolated = settings.model_copy(update={"worker_id": f"{settings.worker_id}-{index + 1}"})
        workers.append(RabbitMQWorker(isolated, build_pipeline(isolated).run))
    return WorkerPool(workers)
