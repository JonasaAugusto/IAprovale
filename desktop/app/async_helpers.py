"""Qt-native background dispatch helper (BUSCA-06 core, Pitfall 1).

`run_in_background` is the single reusable helper every screen must use
for any network call: no `api_client.*` call may be made directly inside a
Qt widget's clicked-signal handler (it would freeze the GUI event loop for
the full round-trip, which can be 30-90s for a cold Render start).

HARD RULE: `fn` runs on a `QThreadPool` worker thread and MUST NOT touch
any Qt widget. Only `on_success`/`on_error` (invoked on the GUI thread, via
Qt's signal/slot auto-marshaling across threads) may touch widgets.

Unlike the old Tkinter version, there is no root-window argument or
polling-interval parameter — QThreadPool is process-global and Qt's
signal/slot mechanism delivers cross-thread emissions without any polling
loop.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(object)


class _Worker(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - deliberately broad; caller inspects exc
            self.signals.error.emit(exc)
        else:
            self.signals.result.emit(result)


_POOL = QThreadPool.globalInstance()

# Empirically required (05-RESEARCH.md Assumption A3, verified in
# test_async_helpers.py's 20-worker lifetime test): firing many QRunnables
# in quick succession WITHOUT holding a Python-side reference causes some
# `_Worker`/`_WorkerSignals` instances to be garbage-collected before their
# `run()` finishes and the queued signal is delivered to the GUI thread —
# `QThreadPool.start()` alone does not keep the reference alive for us.
# Kept as a module-level set, cleaned up once each worker's outcome fires.
_LIVE_WORKERS: set[_Worker] = set()


def run_in_background(fn, on_success, on_error) -> None:
    """Run `fn` off the GUI thread, deliver the outcome back on it.

    `fn` runs on a `QThreadPool` worker thread and MUST NOT touch any
    widget. `on_success(result)`/`on_error(exc)` are Qt signal slots — Qt's
    signal/slot mechanism auto-marshals the `emit()` call back onto the GUI
    thread (queued connection, the default for cross-thread connections),
    so they are safe to touch widgets from, exactly like the old
    on_success/on_error callbacks invoked via root.after() polling.
    """
    worker = _Worker(fn)

    def _forget(_payload=None, *, _worker=worker) -> None:
        _LIVE_WORKERS.discard(_worker)

    worker.signals.result.connect(on_success)
    worker.signals.error.connect(on_error)
    worker.signals.result.connect(_forget)
    worker.signals.error.connect(_forget)

    _LIVE_WORKERS.add(worker)
    _POOL.start(worker)
