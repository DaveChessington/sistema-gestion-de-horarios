"""Pruebas del adaptador Booking perteneciente a la capa de presentación."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from schedule.app import create_app
from schedule.app.clients.booking_client import (
    BookingAuthorizationError,
    BookingClient,
    BookingUnavailableError,
    BookingValidationError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    BOOKING_API_BASE_URL = "http://booking.test/api/v1"
    BOOKING_REQUEST_TIMEOUT = 1


def response_context(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response
    return context


def schedule_record():
    return {
        "id_peticion": 4,
        "id_salon": 2,
        "fecha_reserva": "2026-08-17",
        "hora_inicio": "08:00:00",
        "hora_fin": "08:50:00",
        "estado": "APROBADA",
        "materia_nombre": "Redes",
        "id_programa": None,
        "id_usuario": 7,
        "prioridad_calculada": 90,
        "nombre_tipo_evento": "Clase Curricular",
    }


def test_booking_client_lists_public_schedule_from_contract():
    app = create_app(TestConfig)
    record = schedule_record()

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"total": 1, "grid": [record]}),
    ) as request_mock:
        result = BookingClient.list_schedule()

    assert result == [record]
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://booking.test/api/v1/schedule/grid"
    assert sent_request.method == "GET"


def test_booking_client_forwards_supported_filters():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"total": 0, "grid": []}),
    ) as request_mock:
        BookingClient.list_schedule(
            {
                "id_salon": "2",
                "fecha_reserva": "2026-08-17",
                "unsupported": "ignored",
            }
        )

    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == (
        "http://booking.test/api/v1/schedule/grid"
        "?id_salon=2&fecha_reserva=2026-08-17"
    )


def test_booking_client_rejects_invalid_contract():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"total": 2, "grid": [schedule_record()]}),
    ), pytest.raises(BookingUnavailableError, match="cuadrícula de horarios inválida"):
        BookingClient.list_schedule()


def test_booking_client_translates_http_error():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://booking.test/api/v1/schedule/grid",
        code=500,
        msg="Error",
        hdrs=None,
        fp=BytesIO(b'{"error":"Booking temporalmente no disponible"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=error,
    ), pytest.raises(BookingUnavailableError, match="temporalmente no disponible"):
        BookingClient.list_schedule()


def test_booking_client_translates_connection_failure():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=URLError("connection refused"),
    ), pytest.raises(BookingUnavailableError, match="servicio de horarios no está disponible"):
        BookingClient.list_schedule()


def test_booking_client_creates_authenticated_request_from_contract():
    app = create_app(TestConfig)
    payload = {
        "id_salon": 2,
        "id_programa": 3,
        "materia_nombre": "Redes",
        "fecha_reserva": "2026-08-17",
        "hora_inicio": "08:00",
        "hora_fin": "08:50",
        "id_tipo_evento": 1,
        "numero_alumnos": 20,
        "observaciones": "Laboratorio",
    }
    service_result = {
        "message": "Reserva aprobada y registrada exitosamente.",
        "peticion": {"id_peticion": 9, "estado": "APROBADA"},
    }

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context(service_result),
    ) as request_mock:
        result = BookingClient.create_booking(payload, "iam-token")

    assert result == service_result
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://booking.test/api/v1/booking/request"
    assert sent_request.method == "POST"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data.decode("utf-8")) == payload


def test_booking_client_exposes_conflict_reason_as_validation_error():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://booking.test/api/v1/booking/request",
        code=409,
        msg="Conflict",
        hdrs=None,
        fp=BytesIO(
            json.dumps(
                {
                    "error": "Conflicto de reserva.",
                    "motivo_rechazo": "Existe una solicitud de mayor prioridad.",
                }
            ).encode("utf-8")
        ),
    )

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=error,
    ), pytest.raises(BookingValidationError, match="mayor prioridad"):
        BookingClient.create_booking({}, "iam-token")


def test_booking_client_translates_booking_authorization_failure():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://booking.test/api/v1/booking/request",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=BytesIO(b'{"error":"Token expirado"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=error,
    ), pytest.raises(BookingAuthorizationError) as captured_error:
        BookingClient.create_booking({}, "iam-token")

    assert captured_error.value.status_code == 401


def test_booking_client_rejects_incomplete_created_request():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"message": "Creada", "peticion": {}}),
    ), pytest.raises(BookingUnavailableError, match="solicitud de reserva incompleta"):
        BookingClient.create_booking({}, "iam-token")


def test_booking_client_lists_authenticated_history_with_supported_filters():
    app = create_app(TestConfig)
    record = {
        **schedule_record(),
        "fecha_solicitud": "2026-08-16T10:00:00",
        "motivo_rechazo": None,
    }

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"total": 1, "peticiones": [record]}),
    ) as request_mock:
        result = BookingClient.list_history(
            {
                "estado": "APROBADA",
                "id_salon": 2,
                "id_usuario": 7,
                "unsupported": "ignored",
            },
            "iam-token",
        )

    assert result == [record]
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == (
        "http://booking.test/api/v1/booking/history"
        "?estado=APROBADA&id_salon=2&id_usuario=7"
    )
    assert sent_request.method == "GET"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"


def test_booking_client_rejects_invalid_history_contract():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"total": 2, "peticiones": [schedule_record()]}),
    ), pytest.raises(BookingUnavailableError, match="historial de reservas inválido"):
        BookingClient.list_history({}, "iam-token")


def test_booking_client_cancels_authenticated_request():
    app = create_app(TestConfig)
    service_result = {
        "message": "Reserva #9 cancelada exitosamente y espacio liberado.",
        "peticion": {"id_peticion": 9, "estado": "CANCELADA"},
    }

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context(service_result),
    ) as request_mock:
        result = BookingClient.cancel_booking(9, "iam-token")

    assert result == service_result
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://booking.test/api/v1/booking/request/9"
    assert sent_request.method == "DELETE"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert sent_request.data is None


def test_booking_client_translates_cancel_authorization_failure():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://booking.test/api/v1/booking/request/9",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=BytesIO(b'{"error":"Reserva fuera del plantel asignado"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=error,
    ), pytest.raises(BookingAuthorizationError, match="fuera del plantel") as captured_error:
        BookingClient.cancel_booking(9, "iam-token")

    assert captured_error.value.status_code == 403


def test_booking_client_rejects_incomplete_cancel_confirmation():
    app = create_app(TestConfig)

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context(
            {"message": "Procesada", "peticion": {"id_peticion": 9, "estado": "APROBADA"}}
        ),
    ), pytest.raises(BookingUnavailableError, match="confirmación de cancelación incompleta"):
        BookingClient.cancel_booking(9, "iam-token")


def test_booking_client_gets_authenticated_booking_detail():
    app = create_app(TestConfig)
    record = {**schedule_record(), "id_peticion": 9}

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context({"peticion": record}),
    ) as request_mock:
        result = BookingClient.get_booking(9, "iam-token")

    assert result == record
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://booking.test/api/v1/booking/request/9"
    assert sent_request.method == "GET"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"


def test_booking_client_updates_authenticated_booking():
    app = create_app(TestConfig)
    payload = {"id_salon": 3, "fecha_reserva": "2026-08-20"}
    service_result = {
        "message": "Reserva #9 actualizada exitosamente.",
        "peticion": {**schedule_record(), "id_peticion": 9, "id_salon": 3},
    }

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        return_value=response_context(service_result),
    ) as request_mock:
        result = BookingClient.update_booking(9, payload, "iam-token")

    assert result == service_result
    sent_request = request_mock.call_args.args[0]
    assert sent_request.full_url == "http://booking.test/api/v1/booking/request/9"
    assert sent_request.method == "PATCH"
    assert sent_request.get_header("Authorization") == "Bearer iam-token"
    assert json.loads(sent_request.data.decode("utf-8")) == payload


def test_booking_client_exposes_update_conflict_reason():
    app = create_app(TestConfig)
    error = HTTPError(
        url="http://booking.test/api/v1/booking/request/9",
        code=409,
        msg="Conflict",
        hdrs=None,
        fp=BytesIO(b'{"error":"Conflicto","motivo_rechazo":"Prioridad igual"}'),
    )

    with app.app_context(), patch(
        "schedule.app.clients.booking_client.urlopen",
        side_effect=error,
    ), pytest.raises(BookingValidationError, match="Prioridad igual"):
        BookingClient.update_booking(9, {}, "iam-token")
