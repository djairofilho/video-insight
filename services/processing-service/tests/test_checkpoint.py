from processing_service.domain import Operation, ProcessingError
from test_pipeline import build, run, storage_with_video
from support import FakeChapterWriter, FakeTranscriber, RaisingStep, make_request
from concurrent.futures import ThreadPoolExecutor
import time


class CountingTranscriber(FakeTranscriber):
    def __init__(self):
        self.calls = 0

    def transcribe(self, *args, **kwargs):
        self.calls += 1
        return super().transcribe(*args, **kwargs)


def test_retry_reuses_transcript_and_summary_after_chapter_failure(settings):
    request = make_request()
    storage = storage_with_video(settings, request)
    transcriber = CountingTranscriber()
    broken = RaisingStep(ProcessingError('llm_unavailable', 'indisponível', retryable=True), Operation.CHAPTERS)
    assert run(build(settings, storage, transcriber=transcriber, chapter_writer=broken), request)[-1].event_type == 'processing.failed'
    retry = request.model_copy(update={'data': request.data.model_copy(update={'attempt': 2})})
    summary_must_not_run = RaisingStep(AssertionError('resumo repetido'), Operation.SUMMARY)
    result = run(build(settings, storage, transcriber=transcriber, summarizer=summary_must_not_run,
                       chapter_writer=FakeChapterWriter()), retry)
    assert result[-1].event_type == 'processing.completed'
    assert transcriber.calls == 1
    assert result[-1].data.artifacts.transcript_json_key.endswith('attempt-2/transcript.json')


def test_checkpoint_does_not_cross_jobs_or_changed_video_contents(settings):
    request = make_request(operations=('transcription',))
    storage = storage_with_video(settings, request)
    transcriber = CountingTranscriber()
    run(build(settings, storage, transcriber=transcriber), request)
    other = make_request(operations=('transcription',))
    run(build(settings, storage, transcriber=transcriber), other)
    assert transcriber.calls == 2
    storage.objects[(settings.videos_bucket, request.data.storage_key)] = b'novo conteudo'
    retry = request.model_copy(update={'data': request.data.model_copy(update={'attempt': 2})})
    run(build(settings, storage, transcriber=transcriber), retry)
    assert transcriber.calls == 3


def test_duplicate_delivery_to_two_consumers_runs_provider_once(settings):
    request = make_request(operations=('transcription',))
    storage = storage_with_video(settings, request)

    class SlowTranscriber(CountingTranscriber):
        def transcribe(self, *args, **kwargs):
            time.sleep(.03)
            return super().transcribe(*args, **kwargs)

    transcriber = SlowTranscriber()
    pipelines = [build(settings, storage, transcriber=transcriber) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pipeline: run(pipeline, request), pipelines))
    assert transcriber.calls == 1
    assert all(events[-1].event_type == 'processing.completed' for events in results)
