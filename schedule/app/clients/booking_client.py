"""Adaptador HTTP del frontend para consultar y solicitar reservas en Booking."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


class BookingClientError(Exception):
    """Error controlado al comunicarse con Booking."""


class BookingValidationError(BookingClientError):
    """Booking rechazó los datos o detectó un conflicto de horario."""


class BookingAuthorizationError(BookingClientError):
    """Booking rechazó el JWT o los permisos del usuario."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class BookingUnavailableError(BookingClientError):
    """Booking no respondió o devolvió un contrato inválido."""


class BookingClient:
    """Consume Booking sin importar modelos ni acceder a su base de datos."""

    FILTER_NAMES = (
        "id_plantel",
        "id_salon",
        "id_programa",
        "fecha",
        "fecha_reserva",
    )
    HISTORY_FILTER_NAMES = (
        "estado",
        "id_salon",
        "fecha",
        "fecha_reserva",
        "id_usuario",
    )

    @staticmethod
    def list_schedule(filters=None):
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        supplied_filters = filters or {}
        query = urlencode([
            (name, supplied_filters[name])
            for name in BookingClient.FILTER_NAMES
            if supplied_filters.get(name) not in {None, ""}
        ])
        url = f"{base_url}/schedule/grid"
        if query:
            url = f"{url}?{query}"

        request = Request(url, headers={"Accept": "application/json"}, method="GET")

        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking no pudo consultar los horarios.")
            raise BookingUnavailableError(message) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError(
                "El servicio de horarios no está disponible. Intenta nuevamente más tarde."
            ) from error

        records = result.get("grid")
        total = result.get("total")
        if (
            not isinstance(records, list)
            or not all(isinstance(item, dict) for item in records)
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total != len(records)
        ):
            raise BookingUnavailableError(
                "Booking devolvió una cuadrícula de horarios inválida."
            )
        return records

    @staticmethod
    def create_booking(payload, token):
        """Envía una solicitud autenticada y valida la respuesta de Booking."""
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/booking/request",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking rechazó la solicitud de reserva.")
            if result.get("motivo_rechazo"):
                message = f"{message} {result['motivo_rechazo']}"
            if error.code in {400, 404, 409}:
                raise BookingValidationError(message) from error
            if error.code in {401, 403}:
                raise BookingAuthorizationError(message, error.code) from error
            raise BookingUnavailableError(
                "Booking no pudo procesar la solicitud de reserva."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError(
                "El servicio de reservas no está disponible. Intenta nuevamente más tarde."
            ) from error

        booking = result.get("peticion")
        if not isinstance(booking, dict) or not booking.get("id_peticion"):
            raise BookingUnavailableError(
                "Booking devolvió una solicitud de reserva incompleta."
            )
        return result

    @staticmethod
    def list_history(filters, token):
        """Consulta el historial autenticado y valida el contrato de respuesta."""
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        supplied_filters = filters or {}
        query = urlencode([
            (name, supplied_filters[name])
            for name in BookingClient.HISTORY_FILTER_NAMES
            if supplied_filters.get(name) not in {None, ""}
        ])
        url = f"{base_url}/booking/history"
        if query:
            url = f"{url}?{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking rechazó la consulta del historial.")
            if error.code in {400, 404, 409}:
                raise BookingValidationError(message) from error
            if error.code in {401, 403}:
                raise BookingAuthorizationError(message, error.code) from error
            raise BookingUnavailableError(
                "Booking no pudo consultar el historial de reservas."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError(
                "El historial de reservas no está disponible. Intenta nuevamente más tarde."
            ) from error

        records = result.get("peticiones")
        total = result.get("total")
        if (
            not isinstance(records, list)
            or not all(isinstance(item, dict) for item in records)
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total != len(records)
        ):
            raise BookingUnavailableError(
                "Booking devolvió un historial de reservas inválido."
            )
        return records

    @staticmethod
    def get_booking(booking_id, token):
        """Consulta una reserva individual autenticada."""
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/booking/request/{booking_id}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking rechazó la consulta de la reserva.")
            if error.code in {400, 404, 409}:
                raise BookingValidationError(message) from error
            if error.code in {401, 403}:
                raise BookingAuthorizationError(message, error.code) from error
            raise BookingUnavailableError("Booking no pudo consultar la reserva.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError("La reserva no está disponible temporalmente.") from error
        booking = result.get("peticion")
        if not isinstance(booking, dict) or booking.get("id_peticion") != booking_id:
            raise BookingUnavailableError("Booking devolvió una reserva incompleta.")
        return booking

    @staticmethod
    def update_booking(booking_id, payload, token):
        """Actualiza una reserva mediante el contrato PATCH de Booking."""
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/booking/request/{booking_id}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking rechazó la actualización.")
            if result.get("motivo_rechazo"):
                message = f"{message} {result['motivo_rechazo']}"
            if error.code in {400, 404, 409}:
                raise BookingValidationError(message) from error
            if error.code in {401, 403}:
                raise BookingAuthorizationError(message, error.code) from error
            raise BookingUnavailableError("Booking no pudo actualizar la reserva.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError(
                "El servicio de reservas no está disponible. Intenta nuevamente más tarde."
            ) from error
        booking = result.get("peticion")
        if not isinstance(booking, dict) or booking.get("id_peticion") != booking_id:
            raise BookingUnavailableError("Booking devolvió una reserva actualizada incompleta.")
        return result

    @staticmethod
    def cancel_booking(booking_id, token):
        """Cancela una reserva mediante el endpoint autenticado de Booking."""
        base_url = current_app.config["BOOKING_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["BOOKING_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/booking/request/{booking_id}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="DELETE",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = BookingClient._read_json(response)
        except HTTPError as error:
            result = BookingClient._read_json(error)
            message = result.get("error", "Booking rechazó la cancelación de la reserva.")
            if error.code in {400, 404, 409}:
                raise BookingValidationError(message) from error
            if error.code in {401, 403}:
                raise BookingAuthorizationError(message, error.code) from error
            raise BookingUnavailableError(
                "Booking no pudo cancelar la reserva."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BookingUnavailableError(
                "El servicio de reservas no está disponible. Intenta nuevamente más tarde."
            ) from error

        booking = result.get("peticion")
        if (
            not isinstance(booking, dict)
            or booking.get("id_peticion") != booking_id
            or booking.get("estado") != "CANCELADA"
        ):
            raise BookingUnavailableError(
                "Booking devolvió una confirmación de cancelación incompleta."
            )
        return result

    @staticmethod
    def _read_json(response):
        try:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
            raise BookingUnavailableError(
                "Booking devolvió una respuesta que no se pudo interpretar."
            ) from error
        return parsed if isinstance(parsed, dict) else {}
