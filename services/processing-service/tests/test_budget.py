from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread, current_thread

import pytest

from processing_service.budget import ProviderBudget
from processing_service.domain import ProcessingError
from processing_service.metrics import METRICS


def test_budget_is_atomic_across_instances_and_survives_restart(tmp_path):
    path = str(tmp_path / 'budget.sqlite3')
    limits = {'groq': ((60, 'requests', 3), (3600, 'units', 60))}
    budgets = [ProviderBudget(path, limits), ProviderBudget(path, limits)]

    def reserve(index):
        try:
            budgets[index % 2].reserve('groq', units=20)
            return True
        except ProcessingError as error:
            assert error.code == 'provider_budget_exhausted'
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(12))) == 3
    with pytest.raises(ProcessingError, match='Orçamento'):
        ProviderBudget(path, limits).reserve('groq', units=1)


def test_budget_uses_rolling_windows_and_counts_token_reservations(tmp_path):
    now = [100000.0]
    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'),
                            {'google': ((60, 'requests', 2), (60, 'tokens', 100))},
                            clock=lambda: now[0])
    budget.reserve('google', tokens=80)
    with pytest.raises(ProcessingError):
        budget.reserve('google', tokens=21)
    now[0] += 60
    budget.reserve('google', tokens=100)


def test_budget_fails_closed_when_database_is_unavailable(tmp_path):
    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'), {'groq': ((60, 'requests', 1),)})
    budget.path = str(tmp_path / 'missing' / 'budget.sqlite3')
    with pytest.raises(ProcessingError) as caught:
        budget.reserve('groq')
    assert caught.value.code == 'provider_budget_unavailable'


def test_short_rate_limit_waits_without_holding_the_database_lock(tmp_path):
    now = [100000.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'), {'google': ((60, 'requests', 1),)},
                            clock=lambda: now[0], sleep=sleep, max_wait_seconds=65)
    budget.reserve('google')
    budget.reserve('google')
    assert len(sleeps) == 1 and 60 <= sleeps[0] < 61


def test_waiting_consumer_is_not_overtaken_when_a_reservation_expires(tmp_path):
    now = [100000.0]
    waiting, release, second_done = Event(), Event(), Event()
    admitted, errors = [], []

    def sleep(seconds):
        if current_thread().name == 'first':
            waiting.set()
            assert release.wait(2)
        now[0] += seconds

    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'),
                            {'google': ((60, 'tokens', 120000),)},
                            clock=lambda: now[0], sleep=sleep, max_wait_seconds=65)
    budget.reserve('google', tokens=45000)
    now[0] += 1
    budget.reserve('google', tokens=45000)
    now[0] += 1

    def consumer():
        try:
            budget.reserve('google', tokens=45000)
            admitted.append(current_thread().name)
        except Exception as error:
            errors.append(error)
        finally:
            if current_thread().name == 'second':
                second_done.set()

    first, second = Thread(target=consumer, name='first'), Thread(target=consumer, name='second')
    first.start()
    assert waiting.wait(2)
    second.start()
    second_done.wait(.1)
    release.set()
    first.join(2)
    second.join(2)
    assert not first.is_alive() and not second.is_alive()
    assert not errors
    assert admitted == ['first', 'second']


def test_waiting_for_google_does_not_block_groq(tmp_path):
    now = [100000.0]
    waiting, release = Event(), Event()

    def sleep(seconds):
        waiting.set()
        assert release.wait(2)
        now[0] += seconds

    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'),
                            {'google': ((60, 'requests', 1),), 'groq': ((60, 'requests', 1),)},
                            clock=lambda: now[0], sleep=sleep, max_wait_seconds=65)
    budget.reserve('google')
    with ThreadPoolExecutor(max_workers=2) as pool:
        google = pool.submit(budget.reserve, 'google')
        assert waiting.wait(2)
        try:
            pool.submit(budget.reserve, 'groq').result(timeout=1)
        finally:
            release.set()
        google.result(timeout=2)


@pytest.mark.parametrize('limits,first,incoming,period,measure,reason', [
    (((60, 'tokens', 100),), 0, 101, '60', 'tokens', 'request_exceeds_limit'),
    (((60, 'tokens', 100),), 80, 21, '60', 'tokens', 'wait_timeout'),
    (((86400, 'requests', 1),), 1, 1, '86400', 'requests', 'window_exhausted'),
])
def test_budget_reports_rejection_reason_and_wait_without_charging_rejected_call(
        tmp_path, limits, first, incoming, period, measure, reason):
    budget = ProviderBudget(str(tmp_path / 'budget.sqlite3'), {'google': limits})
    if first:
        budget.reserve('google', tokens=first)
    counter = METRICS.budget_rejection_reasons.labels('google', period, measure, reason)
    before = counter._value.get()
    wait_count = METRICS.budget_wait.labels('google')._sum.get()
    with pytest.raises(ProcessingError, match='Orçamento'):
        budget.reserve('google', tokens=incoming)
    assert counter._value.get() == before + 1
    assert METRICS.budget_wait.labels('google')._sum.get() >= wait_count
    with budget._connect() as db:
        assert db.execute('SELECT COUNT(*) FROM usage').fetchone()[0] == int(bool(first))
