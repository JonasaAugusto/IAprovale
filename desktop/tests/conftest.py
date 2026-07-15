"""Shared pytest fixtures for the desktop test suite.

Mirrors backend/tests/conftest.py's factory-fixture idiom (a fixture that
returns a callable) but has no DB/TestClient machinery — desktop tests
mock `requests.post`/`requests.get` directly via `unittest.mock.patch`.
"""

import pytest


class _FakeRequest:
    def __init__(self, url: str) -> None:
        self.url = url


class _FakeResponse:
    def __init__(
        self, status_code: int, json_body: dict, url: str, *, non_json: bool = False
    ) -> None:
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.content = b"{}"  # non-empty so `resp.content` is truthy
        self._json_body = json_body
        self._non_json = non_json
        self.request = _FakeRequest(url)

    def json(self) -> dict:
        # Simulate a non-JSON body (e.g. a Render/Cloudflare HTML error page):
        # requests' Response.json() raises ValueError (json.JSONDecodeError).
        if self._non_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._json_body


@pytest.fixture
def fake_response():
    """Factory fixture: builds a fake `requests.Response`-like object.

    Usage: fake_response(status_code=401, json_body={"detail": "..."})
    Pass non_json=True to simulate an HTML/non-JSON error body.
    """

    def _fake_response(
        status_code: int,
        json_body: dict | None = None,
        url: str = "http://x/y",
        non_json: bool = False,
    ) -> _FakeResponse:
        return _FakeResponse(
            status_code,
            json_body if json_body is not None else {},
            url,
            non_json=non_json,
        )

    return _fake_response
