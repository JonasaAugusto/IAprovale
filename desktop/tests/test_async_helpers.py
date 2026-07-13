"""Tests for async_helpers.run_in_background (BUSCA-06 core).

Uses pytest-qt's `qtbot` fixture to drive a real Qt event loop so
QThreadPool worker threads can actually deliver their queued cross-thread
signal emissions back to the GUI thread — there is no `root`/polling
concept left to fake (05-RESEARCH.md Pitfall 4).
"""

from app.async_helpers import run_in_background


def test_success_routes_to_on_success(qtbot):
    results = []
    errors = []

    def fn():
        return "RESULT"

    run_in_background(fn, results.append, errors.append)

    qtbot.waitUntil(lambda: bool(results or errors), timeout=2000)

    assert results == ["RESULT"]
    assert errors == []


def test_error_routes_to_on_error(qtbot):
    results = []
    errors = []

    def fn():
        raise ValueError("boom")

    run_in_background(fn, results.append, errors.append)

    qtbot.waitUntil(lambda: bool(results or errors), timeout=2000)

    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert errors[0].args == ("boom",)


def test_worker_not_garbage_collected_before_signal_fires(qtbot):
    """Fire 20 workers in sequence; all 20 results must arrive (anti-GC, A3)."""
    results = []
    errors = []

    for i in range(20):

        def fn(i=i):
            return i

        run_in_background(fn, results.append, errors.append)

    qtbot.waitUntil(lambda: bool(len(results) + len(errors) == 20), timeout=5000)

    assert errors == []
    assert sorted(results) == list(range(20))
