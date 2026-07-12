"""Unit tests for `desktop/app/api_client.py`.

All tests mock the `requests` transport layer (or use the `fake_response`
factory fixture from conftest.py) — no real HTTP calls are made.
"""

from unittest.mock import patch

import requests
import pytest

from app import api_client
from app import config


# ---------------------------------------------------------------------------
# Task 1: exception taxonomy + _raise_for_status status mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status_code,expected_exc",
    [
        (423, api_client.AccountLockedError),
        (403, api_client.ForbiddenError),
        (404, api_client.NotFoundError),
        (409, api_client.UsernameTakenError),
        (429, api_client.RateLimitedError),
        (502, api_client.SearchFailedError),
    ],
)
def test_raise_maps_status_to_exception(fake_response, status_code, expected_exc):
    detail = f"detail for {status_code}"
    resp = fake_response(status_code=status_code, json_body={"detail": detail})
    with pytest.raises(expected_exc) as exc_info:
        api_client._raise_for_status(resp)
    assert exc_info.value.detail == detail


def test_401_on_login_is_invalid_credentials(fake_response):
    resp = fake_response(
        status_code=401,
        json_body={"detail": "Usuário ou senha inválidos"},
        url="http://x/auth/login",
    )
    with pytest.raises(api_client.InvalidCredentialsError) as exc_info:
        api_client._raise_for_status(resp)
    assert exc_info.value.detail == "Usuário ou senha inválidos"


def test_401_elsewhere_is_session_expired(fake_response):
    resp = fake_response(
        status_code=401,
        json_body={"detail": "Sessão inválida ou expirada"},
        url="http://x/profile",
    )
    with pytest.raises(api_client.SessionExpiredError) as exc_info:
        api_client._raise_for_status(resp)
    assert exc_info.value.detail == "Sessão inválida ou expirada"


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_ok_response_does_not_raise(fake_response, status_code):
    resp = fake_response(status_code=status_code, json_body={})
    api_client._raise_for_status(resp)  # must not raise


def test_detail_passthrough_verbatim(fake_response):
    detail = "Muitas buscas em pouco tempo, aguarde um momento."
    resp = fake_response(status_code=429, json_body={"detail": detail})
    with pytest.raises(api_client.RateLimitedError) as exc_info:
        api_client._raise_for_status(resp)
    assert exc_info.value.detail == detail


# ---------------------------------------------------------------------------
# Task 2: request methods (auth, profile, search, admin) with token +
# connection handling
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_token():
    """Ensure module-level token state never leaks between tests."""
    api_client.set_token(None)
    yield
    api_client.set_token(None)


def test_login_success(fake_response):
    resp = fake_response(
        status_code=200,
        json_body={"token": "t", "user_id": "u", "username": "jonas", "is_admin": True},
        url=config.BACKEND_URL + "/auth/login",
    )
    with patch("app.api_client.requests.request", return_value=resp) as mock_request:
        result = api_client.login("jonas", "pw")

    assert result == {"token": "t", "user_id": "u", "username": "jonas", "is_admin": True}
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == config.BACKEND_URL + "/auth/login"
    assert kwargs["json"] == {"username": "jonas", "password": "pw"}


def test_login_invalid_credentials(fake_response):
    resp = fake_response(
        status_code=401,
        json_body={"detail": "Usuário ou senha inválidos"},
        url=config.BACKEND_URL + "/auth/login",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.InvalidCredentialsError) as exc_info:
            api_client.login("jonas", "wrong")
    assert exc_info.value.detail == "Usuário ou senha inválidos"


def test_search_parses_nested_result_shape(fake_response):
    search_response = {
        "results": [
            {
                "id": 920001,
                "titulo": "Concurso Prefeitura de Exemplo",
                "cargos": ["Técnico em Enfermagem"],
                "datas": {"aberto": True, "fim": "2026-08-15"},
                "noticia": {"link": "https://www.pciconcursos.com.br/x"},
                "is_new": True,
            }
        ],
        "count": 1,
        "is_empty": False,
        "message": None,
    }
    resp = fake_response(
        status_code=200,
        json_body=search_response,
        url=config.BACKEND_URL + "/search",
    )
    api_client.set_token("tok")
    with patch("app.api_client.requests.request", return_value=resp) as mock_request:
        result = api_client.search("saúde")

    assert result["results"][0]["datas"]["fim"] == "2026-08-15"
    assert result["results"][0]["is_new"] is True
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == config.BACKEND_URL + "/search"
    assert kwargs["json"] == {"query": "saúde"}
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_connection_error_becomes_typed():
    with patch(
        "app.api_client.requests.request", side_effect=requests.ConnectionError()
    ):
        with pytest.raises(api_client.ConnectionFailedError) as exc_info:
            api_client.login("jonas", "pw")
    assert exc_info.value.detail == (
        "Não foi possível conectar ao servidor. Verifique sua internet e tente novamente."
    )


def test_timeout_becomes_typed():
    with patch("app.api_client.requests.request", side_effect=requests.Timeout()):
        with pytest.raises(api_client.TimeoutFailedError) as exc_info:
            api_client.login("jonas", "pw")
    assert exc_info.value.detail == (
        "O servidor demorou demais para responder. Tente novamente em instantes."
    )


def test_admin_methods_target_correct_urls(fake_response):
    api_client.set_token("tok")

    list_resp = fake_response(status_code=200, json_body=[], url=config.BACKEND_URL + "/auth/users")
    with patch("app.api_client.requests.request", return_value=list_resp) as mock_request:
        api_client.list_users()
    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert args[1] == config.BACKEND_URL + "/auth/users"
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}

    create_resp = fake_response(
        status_code=201,
        json_body={"user_id": "u2", "username": "maria", "is_admin": False, "generated_password": "x"},
        url=config.BACKEND_URL + "/auth/users",
    )
    with patch("app.api_client.requests.request", return_value=create_resp) as mock_request:
        api_client.create_user("maria")
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == config.BACKEND_URL + "/auth/users"
    assert kwargs["json"] == {"username": "maria", "is_admin": False}

    deactivate_resp = fake_response(
        status_code=200,
        json_body={"user_id": "u2", "is_active": False},
        url=config.BACKEND_URL + "/auth/users/u2/deactivate",
    )
    with patch("app.api_client.requests.request", return_value=deactivate_resp) as mock_request:
        api_client.deactivate_user("u2")
    args, kwargs = mock_request.call_args
    assert args[0] == "PATCH"
    assert args[1] == config.BACKEND_URL + "/auth/users/u2/deactivate"

    reset_resp = fake_response(
        status_code=200,
        json_body={"user_id": "u2", "generated_password": "y"},
        url=config.BACKEND_URL + "/auth/users/u2/reset-password",
    )
    with patch("app.api_client.requests.request", return_value=reset_resp) as mock_request:
        api_client.reset_password("u2")
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == config.BACKEND_URL + "/auth/users/u2/reset-password"

    reactivate_resp = fake_response(
        status_code=200,
        json_body={"user_id": "u2", "is_active": True},
        url=config.BACKEND_URL + "/auth/users/u2/reactivate",
    )
    with patch("app.api_client.requests.request", return_value=reactivate_resp) as mock_request:
        api_client.reactivate_user("u2")
    args, kwargs = mock_request.call_args
    assert args[0] == "PATCH"
    assert args[1] == config.BACKEND_URL + "/auth/users/u2/reactivate"


# ---------------------------------------------------------------------------
# Task 2 (quick-260711-x4h): delete_user + typed 409 exceptions
# ---------------------------------------------------------------------------


def test_delete_user_issues_delete_and_returns_none_on_204(fake_response):
    api_client.set_token("tok")
    delete_resp = fake_response(
        status_code=204,
        json_body={},
        url=config.BACKEND_URL + "/auth/users/u2",
    )
    with patch("app.api_client.requests.request", return_value=delete_resp) as mock_request:
        result = api_client.delete_user("u2")

    assert result is None
    args, kwargs = mock_request.call_args
    assert args[0] == "DELETE"
    assert args[1] == config.BACKEND_URL + "/auth/users/u2"
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_delete_user_self_delete_409_raises_typed_exception(fake_response):
    api_client.set_token("tok")
    detail = "Você não pode excluir a sua própria conta."
    resp = fake_response(
        status_code=409,
        json_body={"detail": detail},
        url=config.BACKEND_URL + "/auth/users/u2",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.CannotDeleteSelfError) as exc_info:
            api_client.delete_user("u2")
    assert exc_info.value.detail == detail


def test_delete_user_last_admin_409_raises_typed_exception(fake_response):
    api_client.set_token("tok")
    detail = "Não é possível excluir o único administrador ativo do sistema."
    resp = fake_response(
        status_code=409,
        json_body={"detail": detail},
        url=config.BACKEND_URL + "/auth/users/u2",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.CannotDeleteLastAdminError) as exc_info:
            api_client.delete_user("u2")
    assert exc_info.value.detail == detail


def test_delete_user_404_raises_not_found_error(fake_response):
    api_client.set_token("tok")
    detail = "Usuário não encontrado"
    resp = fake_response(
        status_code=404,
        json_body={"detail": detail},
        url=config.BACKEND_URL + "/auth/users/u2",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.NotFoundError) as exc_info:
            api_client.delete_user("u2")
    assert exc_info.value.detail == detail


# ---------------------------------------------------------------------------
# Task 3 (quick-260712-1bx): rename_user
# ---------------------------------------------------------------------------


def test_rename_user_issues_patch_with_correct_url_body_and_headers(fake_response):
    api_client.set_token("tok")
    resp = fake_response(
        status_code=200,
        json_body={"user_id": "u2", "username": "novo_nome", "is_admin": False, "is_active": True},
        url=config.BACKEND_URL + "/auth/users/u2/username",
    )
    with patch("app.api_client.requests.request", return_value=resp) as mock_request:
        result = api_client.rename_user("u2", "novo_nome")

    assert result == {
        "user_id": "u2",
        "username": "novo_nome",
        "is_admin": False,
        "is_active": True,
    }
    args, kwargs = mock_request.call_args
    assert args[0] == "PATCH"
    assert args[1] == config.BACKEND_URL + "/auth/users/u2/username"
    assert kwargs["json"] == {"username": "novo_nome"}
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_rename_user_409_raises_username_taken_error(fake_response):
    api_client.set_token("tok")
    detail = "Nome de usuário já existe"
    resp = fake_response(
        status_code=409,
        json_body={"detail": detail},
        url=config.BACKEND_URL + "/auth/users/u2/username",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.UsernameTakenError) as exc_info:
            api_client.rename_user("u2", "maria")
    assert exc_info.value.detail == detail


def test_rename_user_404_raises_not_found_error(fake_response):
    api_client.set_token("tok")
    detail = "Usuário não encontrado"
    resp = fake_response(
        status_code=404,
        json_body={"detail": detail},
        url=config.BACKEND_URL + "/auth/users/u2/username",
    )
    with patch("app.api_client.requests.request", return_value=resp):
        with pytest.raises(api_client.NotFoundError) as exc_info:
            api_client.rename_user("u2", "maria")
    assert exc_info.value.detail == detail
