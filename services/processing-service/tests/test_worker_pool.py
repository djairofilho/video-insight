from types import SimpleNamespace

import pytest

from processing_service import worker as module
from processing_service.config import Settings


@pytest.mark.asyncio
async def test_pool_has_isolated_pipelines_and_requires_all_connections(monkeypatch):
    pipelines = []

    class Pipeline:
        def __init__(self, settings):
            self.settings = settings

        def run(self, request, emit):
            pass

    def build(settings):
        pipeline = Pipeline(settings)
        pipelines.append(pipeline)
        return pipeline

    monkeypatch.setattr(module, 'build_pipeline', build)
    pool = module.build_worker(Settings(worker_concurrency=2, rabbitmq_password='test'))
    assert len(pipelines) == 2 and pipelines[0] is not pipelines[1]
    assert pipelines[0].settings.worker_id != pipelines[1].settings.worker_id
    events = []

    class Consumer:
        connected = True

        async def start(self):
            events.append('start')

        async def stop(self):
            events.append('stop')

    pool.workers = [Consumer(), Consumer()]
    await pool.start()
    assert pool.connected
    pool.workers[1].connected = False
    assert not pool.connected
    await pool.stop()
    assert events == ['start', 'start', 'stop', 'stop']
