"""HTTP client for the Concurso Finder FastAPI backend.

This is the ONLY module in `desktop/app` allowed to import `requests`.
Every screen talks to the backend exclusively through the typed methods
defined here — never by constructing URLs or calling `requests` directly.

Error handling contract (Pitfall 4 / PATTERNS.md Analog 2): every backend
HTTP error is raised as a narrow `ApiError` subclass whose `.detail`
carries the backend's PT-BR `detail` string verbatim, never re-worded.
Connection-level failures (no HTTP response at all) are raised as their
own typed exceptions with a client-authored PT-BR message (added in the
request-methods layer).
"""

from __future__ import annotations

import requests

from app import config


class ApiError(Exception):
    """Base class for every error this module raises.

    `.detail` always carries the exact PT-BR message the UI should show
    the user verbatim — either the backend's own `detail` field or, for
    connection-level failures, a client-authored fallback string.
    """

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class InvalidCredentialsError(ApiError):
    """401 on POST /auth/login only."""


class AccountLockedError(ApiError):
    """423 — account temporarily locked after too many failed attempts."""


class SessionExpiredError(ApiError):
    """401 on any authenticated endpoint other than /auth/login."""


class ForbiddenError(ApiError):
    """403 — caller is authenticated but not authorized (e.g. not admin)."""


class NotFoundError(ApiError):
    """404 — target resource (e.g. user id) does not exist."""


class UsernameTakenError(ApiError):
    """409 — username already exists (POST /auth/users)."""


class CannotDeleteSelfError(ApiError):
    """409 — admin attempted to delete their own account (DELETE /auth/users/{id})."""


class CannotDeleteLastAdminError(ApiError):
    """409 — deleting this user would leave zero active admins."""


class RateLimitedError(ApiError):
    """429 — search rate limit exceeded."""


class SearchFailedError(ApiError):
    """502 — DeepSeek/MCP orchestration failed server-side."""


class ConnectionFailedError(ApiError):
    """requests.ConnectionError — no HTTP response reached the client."""


class TimeoutFailedError(ApiError):
    """requests.Timeout — no HTTP response reached the client in time."""


_STATUS_TO_EXC: dict[int, type[ApiError]] = {
    403: ForbiddenError,
    404: NotFoundError,
    409: UsernameTakenError,
    429: RateLimitedError,
    502: SearchFailedError,
}


def _raise_for_status(resp: requests.Response) -> None:
    """Raise the matching `ApiError` subclass for a non-OK response.

    No-op when `resp.ok` is True. Every raised exception carries the
    backend's `detail` string unmodified (Pitfall 4) — never rephrased.
    """
    if resp.ok:
        return

    # The backend's own errors are JSON with a PT-BR `detail`. But the most
    # common production error — a Render free-tier cold start / proxy 5xx —
    # returns an HTML body, so resp.json() raises. Fall back to a status-based
    # PT-BR message instead of leaking a raw "Expecting value: line 1..." to
    # the user (T-03).
    detail = "Erro desconhecido"
    if resp.content:
        try:
            detail = resp.json().get("detail", "Erro desconhecido")
        except ValueError:
            if resp.status_code >= 500:
                detail = (
                    "O servidor está iniciando ou instável no momento. "
                    "Aguarde alguns segundos e tente novamente."
                )
            else:
                detail = "Não foi possível completar a operação. Tente novamente."

    if resp.status_code == 423:
        raise AccountLockedError(detail)
    if resp.status_code == 401:
        if resp.request.url.endswith("/auth/login"):
            raise InvalidCredentialsError(detail)
        raise SessionExpiredError(detail)

    exc_cls = _STATUS_TO_EXC.get(resp.status_code, ApiError)
    raise exc_cls(detail)


_token: str | None = None


def set_token(token: str | None) -> None:
    """Store the bearer token attached to every subsequent authenticated call."""
    global _token
    _token = token


def _headers() -> dict[str, str] | None:
    if _token is None:
        return None
    return {"Authorization": f"Bearer {_token}"}


def _request(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    auth: bool = False,
    timeout: int = 90,
) -> dict | None:
    """Send one HTTP request and return the parsed JSON body (or None for 204).

    Wraps `requests.request`, mapping connection-level failures (no HTTP
    response at all) to typed exceptions, then delegates status-code
    handling to `_raise_for_status`. `timeout` defaults to 90s to
    accommodate Render free-tier cold starts plus DeepSeek/MCP latency
    (BUSCA-06/D-02) — a short timeout would spuriously fail real searches.
    """
    url = config.BACKEND_URL + path
    try:
        resp = requests.request(
            method,
            url,
            json=json_body,
            headers=_headers() if auth else None,
            timeout=timeout,
        )
    except requests.ConnectionError as exc:
        raise ConnectionFailedError(
            "Não foi possível conectar ao servidor. Verifique sua internet e tente novamente."
        ) from exc
    except requests.Timeout as exc:
        raise TimeoutFailedError(
            "O servidor demorou demais para responder. Tente novamente em instantes."
        ) from exc

    _raise_for_status(resp)

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def login(username: str, password: str) -> dict:
    """POST /auth/login -> {token, user_id, username, is_admin}."""
    return _request(
        "POST",
        "/auth/login",
        json_body={"username": username, "password": password},
        auth=False,
    )


def logout() -> None:
    """POST /auth/logout -> 204 (revokes the session server-side)."""
    _request("POST", "/auth/logout", auth=True)


def get_profile() -> dict:
    """GET /profile -> perfil completo (graduacao, tecnico, pos_graduacao,
    escolaridade, formacao_futura, uf, cidade, mobilidade, areas_interesse,
    experiencia, curriculo, updated_at). Campos nunca preenchidos vêm None."""
    return _request("GET", "/profile", auth=True)


def update_profile(campos: dict) -> dict:
    """PUT /profile -> perfil atualizado. `campos` carrega só os campos de
    perfil (graduacao, tecnico, ... , curriculo); o backend valida e faz
    upsert. Devolve o perfil salvo (mesmo shape de get_profile)."""
    return _request("PUT", "/profile", json_body=campos, auth=True)


def search(query: str, usar_curriculo: bool = False) -> dict:
    """POST /search -> {results, count, is_empty, message}.

    `usar_curriculo` opts in (per search) to the backend reading the saved
    profile's currículo as a secondary signal for the DeepSeek extraction.
    Always sent explicitly (default False) — the backend has its own
    default, but this keeps the client's request body self-documenting."""
    return _request(
        "POST",
        "/search",
        json_body={"query": query, "usar_curriculo": usar_curriculo},
        auth=True,
    )


def lookup_cep(cep: str) -> dict:
    """GET /cep/{cep} -> {cep, cidade, uf, bairro, logradouro}. O backend faz
    o proxy para a ViaCEP (o desktop nunca chama a ViaCEP direto). Timeout
    curto — é uma consulta leve, não uma busca de concursos."""
    return _request("GET", f"/cep/{cep}", auth=True, timeout=15)


def list_users() -> list[dict]:
    """GET /auth/users -> [{user_id, username, is_admin, is_active}, ...]."""
    return _request("GET", "/auth/users", auth=True)


def create_user(username: str, is_admin: bool = False) -> dict:
    """POST /auth/users -> {user_id, username, is_admin, generated_password}."""
    return _request(
        "POST",
        "/auth/users",
        json_body={"username": username, "is_admin": is_admin},
        auth=True,
    )


def deactivate_user(user_id: str) -> dict:
    """PATCH /auth/users/{user_id}/deactivate -> {user_id, is_active}."""
    return _request("PATCH", f"/auth/users/{user_id}/deactivate", auth=True)


def reactivate_user(user_id: str) -> dict:
    """PATCH /auth/users/{user_id}/reactivate -> {user_id, is_active}."""
    return _request("PATCH", f"/auth/users/{user_id}/reactivate", auth=True)


def reset_password(user_id: str) -> dict:
    """POST /auth/users/{user_id}/reset-password -> {user_id, generated_password}."""
    return _request("POST", f"/auth/users/{user_id}/reset-password", auth=True)


def rename_user(user_id: str, new_username: str) -> dict:
    """PATCH /auth/users/{user_id}/username -> {user_id, username, is_admin, is_active}.

    409 -> UsernameTakenError, 404 -> NotFoundError (existing `_STATUS_TO_EXC`
    mapping, backend `detail` carried verbatim).
    """
    return _request(
        "PATCH",
        f"/auth/users/{user_id}/username",
        json_body={"username": new_username},
        auth=True,
    )


def delete_user(user_id: str) -> None:
    """DELETE /auth/users/{user_id} -> None (204). Permanent, irreversible.

    The backend returns a generic 409 (UsernameTakenError, per
    `_STATUS_TO_EXC`) for two distinct guard conditions — this routes on the
    exact PT-BR `detail` string to raise the correct typed exception the UI
    can distinguish, without changing `_STATUS_TO_EXC`'s existing
    username-taken behavior for POST /auth/users.
    """
    try:
        return _request("DELETE", f"/auth/users/{user_id}", auth=True)
    except UsernameTakenError as exc:
        if "sua própria conta" in exc.detail:
            raise CannotDeleteSelfError(exc.detail) from exc
        if "único administrador ativo" in exc.detail:
            raise CannotDeleteLastAdminError(exc.detail) from exc
        raise
