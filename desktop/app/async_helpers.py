"""Thread + queue + Tk-`after()` polling helper (BUSCA-06 core, Pitfall 1).

`run_in_background` is the single reusable helper every screen must use
for any network call: no `api_client.*` call may be made directly inside a
Tkinter `command=` handler (it would freeze the UI for the full round-trip,
which can be 30-90s for a cold Render start).

HARD RULE: `fn` runs in a daemon worker thread and MUST NOT touch any
Tkinter widget. Only `on_success`/`on_error` (invoked on the main thread,
via `root.after()` polling) may touch widgets.

`root` is only ever used through its `.after(ms, callback)` method, so any
object exposing a compatible `after()` (including a fake test double) can
drive this deterministically without a real Tk display.
"""

import queue
import threading


def run_in_background(root, fn, on_success, on_error, poll_ms: int = 50) -> None:
    q: queue.Queue = queue.Queue()

    def worker():
        try:
            q.put(("ok", fn()))
        except Exception as exc:  # noqa: BLE001 - deliberately broad; caller inspects exc
            q.put(("error", exc))

    threading.Thread(target=worker, daemon=True).start()

    def poll():
        try:
            status, payload = q.get_nowait()
        except queue.Empty:
            root.after(poll_ms, poll)
            return
        if status == "ok":
            on_success(payload)
        else:
            on_error(payload)

    root.after(poll_ms, poll)
