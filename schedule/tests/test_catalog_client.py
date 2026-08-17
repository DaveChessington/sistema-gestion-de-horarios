"""Pruebas del adaptador Catalog perteneciente a la capa de presentación."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from schedule.app import create_app
from schedule.app.clients.catalog_client import (
    CatalogAuthorizationError,
    CatalogClient,
    CatalogUnavailableError,
    CatalogValidationError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    CATALOG_API_BASE_URL = "http://catalog.test/api/v1"
    CATALOG_REQUEST_TIMEOUT = 1


def response_context(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response
    return context


def test_catalog_client_lists_all_planteles_from_contract():
    app = create_app(TestConfig)
    payload = [{"id": 1, "nombre": "Plantel León", "direccion": None, "activo": True}]

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.list_planteles(active_only=False)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/planteles?active_only=false"
    assert sent_request.method == "GET"


def test_catalog_client_creates_plantel_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"id": 8, "nombre": "Plantel Sur", "direccion": "Zona Sur", "activo": True}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.create_plantel("Plantel Sur", "Zona Sur", "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/planteles"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "nombre": "Plantel Sur",
        "direccion": "Zona Sur",
    }


def test_catalog_client_gets_plantel_by_id():
    app = create_app(TestConfig)
    payload = {"id": 8, "nombre": "Plantel Sur", "direccion": "Zona Sur", "activo": True}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.get_plantel(8)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/planteles/8"
    assert sent_request.method == "GET"


def test_catalog_client_updates_plantel_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"id": 8, "nombre": "Plantel Sur Actualizado", "direccion": None, "activo": True}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.update_plantel(
            8, "Plantel Sur Actualizado", "", "iam-token"
        )

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/planteles/8"
    assert sent_request.method == "PUT"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "nombre": "Plantel Sur Actualizado",
        "direccion": None,
    }


def test_catalog_client_deactivates_plantel_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"message": "Plantel 8 y sus recursos dependientes desactivados lógicamente."}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.deactivate_plantel(8, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/planteles/8"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


def test_catalog_client_lists_all_salones_from_contract():
    app = create_app(TestConfig)
    payload = [
        {
            "id_salon": 4,
            "numero": "Laboratorio 04",
            "descripcion": "Cómputo",
            "capacidad": 30,
            "id_plantel": 1,
            "activo": True,
        }
    ]

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.list_salones(active_only=False)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/salones?active_only=false"
    assert sent_request.method == "GET"


def test_catalog_client_creates_salon_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_salon": 4,
        "numero": "Laboratorio 04",
        "descripcion": "Cómputo",
        "capacidad": 30,
        "id_plantel": 1,
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.create_salon(
            "Laboratorio 04", "Cómputo", 30, 1, "iam-token"
        )

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/salones"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "numero": "Laboratorio 04",
        "descripcion": "Cómputo",
        "capacidad": 30,
        "id_plantel": 1,
    }


def test_catalog_client_gets_salon_by_id():
    app = create_app(TestConfig)
    payload = {
        "id_salon": 4,
        "numero": "Laboratorio 04",
        "descripcion": "Cómputo",
        "capacidad": 30,
        "id_plantel": 1,
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.get_salon(4)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/salones/4"
    assert sent_request.method == "GET"


def test_catalog_client_updates_salon_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_salon": 4,
        "numero": "Laboratorio 04A",
        "descripcion": None,
        "capacidad": 35,
        "id_plantel": 2,
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.update_salon(
            4, "Laboratorio 04A", "", 35, 2, "iam-token"
        )

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/salones/4"
    assert sent_request.method == "PUT"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "numero": "Laboratorio 04A",
        "descripcion": None,
        "capacidad": 35,
        "id_plantel": 2,
    }


def test_catalog_client_deactivates_salon_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"message": "Salón 4 y sus equipos asociados desactivados lógicamente."}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.deactivate_salon(4, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/salones/4"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


def test_catalog_client_lists_all_equipos_from_contract():
    app = create_app(TestConfig)
    payload = [
        {
            "id_equipo": 5,
            "numero": "PC-005",
            "descripcion": "Estación docente",
            "activo": True,
            "id_salon": 4,
            "programas": [],
        }
    ]

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.list_equipos(active_only=False)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos?active_only=false"
    assert sent_request.method == "GET"


def test_catalog_client_creates_equipo_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_equipo": 5,
        "numero": "PC-005",
        "descripcion": "Estación docente",
        "activo": True,
        "id_salon": 4,
        "programas": [],
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.create_equipo(
            "PC-005", "Estación docente", 4, "iam-token"
        )

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "numero": "PC-005",
        "descripcion": "Estación docente",
        "id_salon": 4,
    }


def test_catalog_client_gets_equipo_from_contract():
    app = create_app(TestConfig)
    payload = {
        "id_equipo": 5,
        "numero": "PC-005",
        "descripcion": "Estación docente",
        "activo": True,
        "id_salon": 4,
        "programas": [],
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.get_equipo(5)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos/5"
    assert sent_request.method == "GET"


def test_catalog_client_updates_equipo_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_equipo": 5,
        "numero": "PC-005A",
        "descripcion": None,
        "activo": True,
        "id_salon": None,
        "programas": [],
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.update_equipo(5, "PC-005A", "", None, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos/5"
    assert sent_request.method == "PUT"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "numero": "PC-005A",
        "descripcion": None,
        "id_salon": None,
    }


def test_catalog_client_deactivates_equipo_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"message": "Equipo 5 desactivado lógicamente."}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.deactivate_equipo(5, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos/5"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


def test_catalog_client_lists_all_programas_from_contract():
    app = create_app(TestConfig)
    payload = [
        {
            "id_programa": 6,
            "nombre": "Python",
            "descripcion": "Entorno académico",
            "activo": True,
        }
    ]

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.list_programas(active_only=False)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/programas?active_only=false"
    assert sent_request.method == "GET"


def test_catalog_client_creates_programa_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_programa": 6,
        "nombre": "Python",
        "descripcion": "Entorno académico",
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.create_programa(
            "Python", "Entorno académico", "iam-token"
        )

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/programas"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "nombre": "Python",
        "descripcion": "Entorno académico",
    }


def test_catalog_client_gets_programa_from_contract():
    app = create_app(TestConfig)
    payload = {
        "id_programa": 6,
        "nombre": "Python",
        "descripcion": "Entorno académico",
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.get_programa(6)

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/programas/6"
    assert sent_request.method == "GET"


def test_catalog_client_updates_programa_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_programa": 6,
        "nombre": "Python 3",
        "descripcion": None,
        "activo": True,
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.update_programa(6, "Python 3", "", "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/programas/6"
    assert sent_request.method == "PUT"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {
        "nombre": "Python 3",
        "descripcion": None,
    }


def test_catalog_client_deactivates_programa_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"message": "Programa 6 desactivado lógicamente."}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.deactivate_programa(6, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/programas/6"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


def test_catalog_client_assigns_programa_to_equipo_with_bearer_token():
    app = create_app(TestConfig)
    payload = {
        "id_equipo": 5,
        "numero": "PC-005",
        "activo": True,
        "id_salon": 4,
        "programas": [
            {"id_programa": 6, "nombre": "Python", "activo": True}
        ],
    }

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.assign_programa(5, 6, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos/5/software"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data) == {"id_programa": 6}


def test_catalog_client_removes_programa_from_equipo_with_bearer_token():
    app = create_app(TestConfig)
    payload = {"message": "Software 6 desinstalado del equipo 5 exitosamente."}

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        return_value=response_context(payload),
    ) as request_mock:
        result = CatalogClient.remove_programa(5, 6, "iam-token")

    assert result == payload
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://catalog.test/api/v1/equipos/5/software/6"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [(400, CatalogValidationError), (401, CatalogAuthorizationError), (403, CatalogAuthorizationError)],
)
def test_catalog_client_translates_controlled_http_errors(status_code, exception_type):
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://catalog.test/api/v1/planteles",
        code=status_code,
        msg="Error",
        hdrs=None,
        fp=BytesIO(b'{"error":"Solicitud rechazada"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        side_effect=error,
    ), pytest.raises(exception_type, match="Solicitud rechazada"):
        CatalogClient.create_plantel("Plantel Sur", "Zona Sur", "iam-token")


def test_catalog_client_translates_connection_failure():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.catalog_client.urlopen",
        side_effect=URLError("connection refused"),
    ), pytest.raises(CatalogUnavailableError, match="no está disponible"):
        CatalogClient.list_planteles()
