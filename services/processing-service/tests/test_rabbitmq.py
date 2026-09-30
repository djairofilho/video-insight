import asyncio
import json
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aio_pika
import pytest
from pydantic import SecretStr

from processing_service.messaging.events import OutgoingEvent, ProcessingStartedData
from processing_service.messaging.rabbitmq import (
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE,
    EVENTS_EXCHANGE,
    REQUESTED_ROUTING_KEY,
    REQUESTS_QUEUE,
    RabbitMQWorker,
)
from processing_service.pipeline import ProcessingPipeline
from support import (
    FakeChapterWriter,
    FakeMedia,
    FakeSummarizer,
    FakeTranscriber,
    InMemoryStorage,
    make_request,
    requires_docker,
)

RABBITMQ_IMAGE = "rabbitmq:4.3.5-management-alpine"
FINAL_EVENTS = {"processing.completed", "processing.failed"}


class FakeMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.acked = False
        self.rejected_with: bool | None = None

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        self.rejected_with = requeue


def fake_broker() -> SimpleNamespace:
    broker = SimpleNamespace(
        connection=AsyncMock(),
        channel=AsyncMock(),
        exchange=AsyncMock(),
        dead_letters=AsyncMock(),
        dead_letter_queue=AsyncMock(),
        queue=AsyncMock(),
    )
    broker.connection.channel.return_value = broker.channel
    broker.channel.declare_exchange.side_effect = [broker.exchange, broker.dead_letters]
    broker.channel.declare_queue.side_effect = [broker.dead_letter_queue, broker.queue]
    return broker


def started(request) -> OutgoingEvent:
    data = ProcessingStartedData(
        job_id=request.data.job_id,
        video_id=request.data.video_id,
        attempt=request.data.attempt,
        worker_id="worker-test",
    )
    return OutgoingEvent.of(data, correlation_id=request.correlation_id)


def ignore(request, emit) -> None:
    return None


async def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


async def connected_worker(settings, broker, handler=ignore) -> RabbitMQWorker:
    async def connect(url: str):
        return broker.connection

    worker = RabbitMQWorker(settings, handler, connect=connect)
    await worker.start()
    await wait_until(lambda: worker.connected)
    return worker


async def test_declares_topology_and_starts_consuming(settings):
    broker = fake_broker()

    worker = await connected_worker(settings, broker)

    broker.channel.set_qos.assert_awaited_once_with(prefetch_count=1)
    broker.channel.declare_exchange.assert_any_await(
        EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
    )
    broker.channel.declare_exchange.assert_any_await(
        DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
    )
    broker.channel.declare_queue.assert_any_await(
        REQUESTS_QUEUE, durable=True, arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE}
    )
    broker.queue.bind.assert_awaited_once_with(broker.exchange, REQUESTED_ROUTING_KEY)
    broker.dead_letter_queue.bind.assert_awaited_once_with(broker.dead_letters, "#")
    broker.queue.consume.assert_awaited_once_with(worker.handle_message)
    await worker.stop()
    broker.connection.close.assert_awaited_once()


async def test_publishes_persistent_json_routed_by_event_type(settings):
    broker = fake_broker()
    worker = await connected_worker(settings, broker)
    request = make_request()
    event = started(request)

    await worker.publish(event)

    call = broker.exchange.publish.await_args
    message = call.args[0]
    assert call.kwargs["routing_key"] == "processing.started"
    assert message.body == event.to_json()
    assert message.content_type == "application/json"
    assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    assert message.message_id == str(event.event_id)
    assert message.correlation_id == str(request.correlation_id)
    await worker.stop()


async def test_publish_before_connecting_fails(settings):
    worker = RabbitMQWorker(settings, ignore)

    with pytest.raises(RuntimeError):
        await worker.publish(started(make_request()))


async def test_keeps_retrying_until_the_broker_is_reachable(settings):
    broker = fake_broker()
    attempts: list[str] = []

    async def connect(url: str):
        attempts.append(url)
        if len(attempts) < 3:
            raise ConnectionRefusedError("recusado")
        return broker.connection

    worker = RabbitMQWorker(settings, ignore, connect=connect)
    await worker.start()
    await wait_until(lambda: worker.connected)

    assert len(attempts) == 3
    await worker.stop()


async def test_failed_setup_closes_the_connection_before_retrying(settings):
    broker = fake_broker()
    broker.channel.set_qos.side_effect = [OSError("canal caiu"), None]

    worker = await connected_worker(settings, broker)

    assert broker.connection.close.await_count == 1
    await worker.stop()


async def test_stop_is_safe_before_start_and_while_reconnecting(settings):
    await RabbitMQWorker(settings, ignore).stop()

    async def refuse(url: str):
        raise ConnectionRefusedError("recusado")

    worker = RabbitMQWorker(settings, ignore, connect=refuse)
    await worker.start()
    await asyncio.sleep(0.05)
    await worker.stop()

    assert worker.connected is False


async def test_message_outside_contract_goes_to_dead_letter_queue(settings):
    def fail(request, emit):
        pytest.fail("não deveria processar")

    message = FakeMessage(b'{"event_type": "processing.requested"}')

    await RabbitMQWorker(settings, fail).handle_message(message)

    assert message.rejected_with is False
    assert message.acked is False


async def test_valid_message_is_processed_in_a_thread_and_acknowledged(settings):
    published: list[OutgoingEvent] = []
    request = make_request()
    message = FakeMessage(request.model_dump_json().encode())
    worker = RabbitMQWorker(settings, lambda received, emit: emit(started(received)))

    async def publish(event: OutgoingEvent) -> None:
        published.append(event)

    worker.publish = publish
    await worker.handle_message(message)

    assert message.acked is True
    assert [event.event_type for event in published] == ["processing.started"]
    assert published[0].correlation_id == request.correlation_id


async def test_handler_crash_rejects_without_requeue(settings):
    def crash(request, emit):
        raise RuntimeError("broker caiu no meio da publicação")

    message = FakeMessage(make_request().model_dump_json().encode())

    await RabbitMQWorker(settings, crash).handle_message(message)

    assert message.rejected_with is False
    assert message.acked is False


async def collect_until_final(queue) -> list[dict]:
    received: list[dict] = []
    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process():
                payload = json.loads(message.body)
                received.append(payload)
                if payload["event_type"] in FINAL_EVENTS:
                    return received
    return received


@pytest.mark.integration
@requires_docker
async def test_processes_a_request_end_to_end_with_real_rabbitmq(settings, validate_event):
    from testcontainers.community.rabbitmq import RabbitMqContainer

    with RabbitMqContainer(RABBITMQ_IMAGE, username="video_insight", password="segredo") as rabbit:
        configured = settings.model_copy(
            update={
                "rabbitmq_host": rabbit.get_container_host_ip(),
                "rabbitmq_port": int(rabbit.get_exposed_port(5672)),
                "rabbitmq_password": SecretStr("segredo"),
            }
        )
        request = make_request()
        storage = InMemoryStorage()
        storage.objects[(configured.videos_bucket, request.data.storage_key)] = b"video"
        pipeline = ProcessingPipeline(
            settings=configured,
            storage=storage,
            media=FakeMedia(),
            transcriber=FakeTranscriber(),
            summarizer=FakeSummarizer(),
            chapter_writer=FakeChapterWriter(),
        )
        worker = RabbitMQWorker(configured, pipeline.run)
        await worker.start()
        await wait_until(lambda: worker.connected, timeout=60)

        connection = await aio_pika.connect_robust(configured.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
            )
            observer = await channel.declare_queue(exclusive=True)
            for event_type in ("started", "progressed", "completed", "failed"):
                await observer.bind(exchange, f"processing.{event_type}")

            await exchange.publish(
                aio_pika.Message(request.model_dump_json().encode()),
                routing_key=REQUESTED_ROUTING_KEY,
            )
            async with asyncio.timeout(30):
                received = await collect_until_final(observer)

            await exchange.publish(aio_pika.Message(b"isto nao e json"), REQUESTED_ROUTING_KEY)
            dead_letters = await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
            async with asyncio.timeout(30):
                while (dead := await dead_letters.get(fail=False)) is None:
                    await asyncio.sleep(0.1)
            await dead.ack()

        await worker.stop()

    assert [event["event_type"] for event in received] == (
        ["processing.started"] + ["processing.progressed"] * 6 + ["processing.completed"]
    )
    for event in received:
        validate_event(event)
        assert event["correlation_id"] == str(request.correlation_id)
    assert dead.body == b"isto nao e json"
