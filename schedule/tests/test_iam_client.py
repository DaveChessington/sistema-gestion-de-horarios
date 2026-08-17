"""Pruebas del adaptador IAM perteneciente a la capa de presentación."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from schedule.app import create_app
from schedule.app.clients.iam_client import (
    IAMAuthenticationError,
    IAMAuthorizationError,
    IAMClient,
    IAMUnavailableError,
    IAMValidationError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    IAM_API_BASE_URL = "http://iam.test/api/v1/auth"
    IAM_REQUEST_TIMEOUT = 1


def test_iam_client_returns_token_and_user_from_contract():
    app = create_app(TestConfig)
    response = MagicMock()
    response.read.return_value = json.dumps(
        {
            "token": "iam-token",
            "usuario": {"id_usuario": 1, "rol": "COORDINADOR"},
        }
    ).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        return_value=context,
    ) as request_mock:
        result = IAMClient.login("admin@udl.edu.mx", "password123")

    assert result["token"] == "iam-token"
    assert result["usuario"]["rol"] == "COORDINADOR"
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://iam.test/api/v1/auth/login"
    assert json.loads(sent_request.data) == {
        "correo": "admin@udl.edu.mx",
        "password": "password123",
    }


def test_iam_client_preserves_controlled_authentication_error():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://iam.test/api/v1/auth/login",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=BytesIO(b'{"error":"Credenciales invalidas"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        side_effect=error,
    ), pytest.raises(IAMAuthenticationError, match="Credenciales invalidas"):
        IAMClient.login("admin@udl.edu.mx", "incorrecta")


def test_iam_client_translates_connection_failure():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        side_effect=URLError("connection refused"),
    ), pytest.raises(IAMUnavailableError, match="no está disponible"):
        IAMClient.login("admin@udl.edu.mx", "password123")


def test_iam_client_lists_users_with_bearer_token():
    app = create_app(TestConfig)
    response = MagicMock()
    response.read.return_value = json.dumps(
        {
            "usuarios": [
                {
                    "id_usuario": 1,
                    "correo": "admin@udl.edu.mx",
                    "rol": "COORDINADOR",
                }
            ]
        }
    ).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        return_value=context,
    ) as request_mock:
        result = IAMClient.list_users("iam-token")

    assert result[0]["id_usuario"] == 1
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://iam.test/api/v1/auth/users"
    assert sent_request.method == "GET"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"


def test_iam_client_registers_user_with_contract_and_bearer_token():
    app = create_app(TestConfig)
    user_data = {
        "nombre": "María",
        "apellido": "Docente",
        "correo": "maria@udl.edu.mx",
        "password": "segura123",
        "rol": "DOCENTE",
        "id_plantel_asignado": 1,
    }
    response = MagicMock()
    response.read.return_value = json.dumps(
        {
            "mensaje": "Usuario registrado exitosamente",
            "usuario": {
                "id_usuario": 2,
                "correo": "maria@udl.edu.mx",
                "rol": "DOCENTE",
            },
        }
    ).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        return_value=context,
    ) as request_mock:
        result = IAMClient.register_user(user_data, "iam-token")

    assert result["id_usuario"] == 2
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://iam.test/api/v1/auth/register"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == user_data


def test_iam_client_translates_duplicate_user_error():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://iam.test/api/v1/auth/register",
        code=409,
        msg="Conflict",
        hdrs=None,
        fp=BytesIO(b'{"error":"El correo ya esta registrado"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        side_effect=error,
    ), pytest.raises(IAMValidationError, match="correo ya esta registrado"):
        IAMClient.register_user({}, "iam-token")


def test_iam_client_translates_users_authorization_error():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://iam.test/api/v1/auth/users",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=BytesIO(b'{"error":"Token expirado"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen",
        side_effect=error,
    ), pytest.raises(IAMAuthorizationError, match="Token expirado"):
        IAMClient.list_users("expired-token")


@pytest.mark.parametrize(
    ("operation", "method", "response_payload"),
    [
        ("get", "GET", {"usuario": {"id_usuario": 7, "activo": True}}),
        ("update", "PUT", {"usuario": {"id_usuario": 7, "activo": True}}),
        ("deactivate", "DELETE", {"usuario": {"id_usuario": 7, "activo": False}}),
    ],
)
def test_iam_client_manages_user_with_expected_contract(operation, method, response_payload):
    app = create_app(TestConfig)
    response = MagicMock()
    response.read.return_value = json.dumps(response_payload).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response

    with app.app_context(), patch(
        "schedule.app.clients.iam_client.urlopen", return_value=context,
    ) as request_mock:
        if operation == "get":
            result = IAMClient.get_user(7, "iam-token")
        elif operation == "update":
            result = IAMClient.update_user(7, {"nombre": "Actualizado"}, "iam-token")
        else:
            result = IAMClient.deactivate_user(7, "iam-token")

    assert result["id_usuario"] == 7
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://iam.test/api/v1/auth/users/7"
    assert sent_request.method == method
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
