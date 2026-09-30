import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError

from processing_service.config import Settings
from processing_service.messaging.events import EventSink, OutgoingEvent, ProcessingRequested

logger = logging.getLogger(__name__)

EVENTS_EXCHANGE = "video-insight.processing"
DEAD_LETTER_EXCHANGE = "video-insight.processing.dlx"
REQUESTS_QUEUE = "processing-service.requests"
DEAD_LETTER_QUEUE = "processing-service.requests.dlq"
REQUESTED_ROUTING_KEY = "processing.requested"

RequestHandler = Callable[[ProcessingRequested, EventSink], None]
Connector = Callable[[str], Awaitable[AbstractRobustConnection]]


class RabbitMQWorker:
    def __init__(
        self,
        settings: Settings,
        handler: RequestHandler,
        *,
        connect: Connector = aio_pika.connect_robust,
    ) -> None:
        self._settings = settings
        self._handler = handler
        self._connect = connect
        self._connection: AbstractRobustConnection | None = None
        self._exchange: AbstractExchange | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        return self._connection is not None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._connect_with_retry(), name="rabbitmq-connect")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._connection is not None:
            await self._connection.close()

    async def _connect_with_retry(self) -> None:
        while True:
            try:
                await self._open()
                return
            except (aio_pika.exceptions.AMQPError, OSError) as error:
                delay = self._settings.rabbitmq_reconnect_seconds
                logger.warning("RabbitMQ indisponível (%s); nova tentativa em %ss", error, delay)
                await asyncio.sleep(delay)

    async def _open(self) -> None:
        connection = await self._connect(self._settings.rabbitmq_url)
        try:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            exchange = await channel.declare_exchange(
                EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
            )
            dead_letters = await channel.declare_exchange(
                DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
            )
            dead_letter_queue = await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
            await dead_letter_queue.bind(dead_letters, "#")
            queue = await channel.declare_queue(
                REQUESTS_QUEUE,
                durable=True,
                arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE},
            )
            await queue.bind(exchange, REQUESTED_ROUTING_KEY)
            self._exchange = exchange
            await queue.consume(self.handle_message)
        except BaseException:
            await connection.close()
            raise
        self._connection = connection
        logger.info("Consumindo a fila %s", REQUESTS_QUEUE)

    async def handle_message(self, message: AbstractIncomingMessage) -> None:
        try:
            request = ProcessingRequested.model_validate_json(message.body)
        except ValidationError as error:
            logger.error("Mensagem fora do contrato enviada à DLQ: %s", error)
            await message.reject(requeue=False)
            return

        loop = asyncio.get_running_loop()

        def emit(event: OutgoingEvent) -> None:
            future = asyncio.run_coroutine_threadsafe(self.publish(event), loop)
            future.result(timeout=self._settings.event_publish_timeout_seconds)

        try:
            await asyncio.to_thread(self._handler, request, emit)
        except Exception:
            logger.exception("Job %s não pôde ser concluído", request.data.job_id)
            await message.reject(requeue=False)
            return
        await message.ack()

    async def publish(self, event: OutgoingEvent) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ ainda não está conectado")
        await self._exchange.publish(
            aio_pika.Message(
                event.to_json(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=str(event.event_id),
                correlation_id=str(event.correlation_id),
                type=event.event_type,
            ),
            routing_key=event.event_type,
        )
