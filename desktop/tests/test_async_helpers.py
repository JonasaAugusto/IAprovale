"""Tests for async_helpers.run_in_background (BUSCA-06 core).

Uses a fake `root` object whose `after(ms, cb)` just appends the callback
to a list — no real Tk display needed. Callbacks are driven manually by
popping and invoking them, simulating the Tk event loop deterministically.
"""

import time

from app.async_helpers import run_in_background


class _FakeRoot:
    def __init__(self):
        self.scheduled: list = []

    def after(self, ms, callback):
        self.scheduled.append(callback)

    def drive_until(self, predicate, max_iterations=2_000):
        """Pop and invoke scheduled callbacks until predicate() is True.

        Sleeps a little on every iteration (not just when nothing is
        queued) so real wall-clock time actually elapses for the worker
        thread to finish — otherwise a re-scheduling poll() loop can spin
        through all iterations near-instantly before the worker is done.
        """
        iterations = 0
        while not predicate() and iterations < max_iterations:
            if self.scheduled:
                callback = self.scheduled.pop(0)
                callback()
            time.sleep(0.001)
            iterations += 1
        if not predicate():
            raise AssertionError("drive_until exceeded max_iterations without success")


def test_polls_until_result():
    root = _FakeRoot()
    results = []
    errors = []

    def fn():
        time.sleep(0.02)  # give the poll loop a chance to re-schedule at least once
        return "RESULT"

    run_in_background(root, fn, results.append, errors.append, poll_ms=1)

    # Immediately after kickoff, exactly one poll() should be scheduled.
    assert len(root.scheduled) == 1

    root.drive_until(lambda: results or errors)

    assert results == ["RESULT"]
    assert errors == []


def test_error_path():
    root = _FakeRoot()
    results = []
    errors = []

    def fn():
        raise ValueError("boom")

    run_in_background(root, fn, results.append, errors.append, poll_ms=1)

    root.drive_until(lambda: results or errors)

    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert errors[0].args == ("boom",)


def test_never_touches_widgets():
    """fn runs to completion with no Tk import needed; only on_success/on_error fire."""
    root = _FakeRoot()
    calls = []

    def fn():
        return 42

    run_in_background(
        root,
        fn,
        lambda payload: calls.append(("success", payload)),
        lambda exc: calls.append(("error", exc)),
        poll_ms=1,
    )

    root.drive_until(lambda: calls)

    assert calls == [("success", 42)]
