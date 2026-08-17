"""Adaptador del frontend para consumir el contrato HTTP de Catalog."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


class CatalogClientError(Exception):
    """Error controlado al comunicarse con Catalog."""


class CatalogValidationError(CatalogClientError):
    """Catalog rechazó los datos enviados por el usuario."""


class CatalogAuthorizationError(CatalogClientError):
    """Catalog rechazó el JWT o los permisos del usuario."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class CatalogUnavailableError(CatalogClientError):
    """Catalog no respondió o devolvió una respuesta inválida."""


class CatalogClient:
    """Consume Catalog sin importar modelos ni acceder a su base de datos."""

    @staticmethod
    def list_planteles(active_only=False):
        query = urlencode({"active_only": str(active_only).lower()})
        result = CatalogClient._request_json(f"/planteles?{query}")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise CatalogUnavailableError("Catalog devolvió un listado de planteles inválido.")
        return result

    @staticmethod
    def create_plantel(nombre, direccion, token):
        result = CatalogClient._request_json(
            "/planteles",
            method="POST",
            payload={"nombre": nombre, "direccion": direccion or None},
            token=token,
        )
        if not isinstance(result, dict) or not result.get("id"):
            raise CatalogUnavailableError("Catalog devolvió un plantel incompleto.")
        return result

    @staticmethod
    def get_plantel(plantel_id):
        result = CatalogClient._request_json(f"/planteles/{plantel_id}")
        if (
            not isinstance(result, dict)
            or result.get("id") != plantel_id
            or not result.get("nombre")
        ):
            raise CatalogUnavailableError("Catalog devolvió un plantel incompleto.")
        return result

    @staticmethod
    def update_plantel(plantel_id, nombre, direccion, token):
        result = CatalogClient._request_json(
            f"/planteles/{plantel_id}",
            method="PUT",
            payload={"nombre": nombre, "direccion": direccion or None},
            token=token,
        )
        if (
            not isinstance(result, dict)
            or result.get("id") != plantel_id
            or not result.get("nombre")
        ):
            raise CatalogUnavailableError("Catalog devolvió un plantel actualizado incompleto.")
        return result

    @staticmethod
    def deactivate_plantel(plantel_id, token):
        result = CatalogClient._request_json(
            f"/planteles/{plantel_id}",
            method="DELETE",
            token=token,
        )
        if not isinstance(result, dict) or not result.get("message"):
            raise CatalogUnavailableError(
                "Catalog devolvió una confirmación de desactivación incompleta."
            )
        return result

    @staticmethod
    def list_salones(active_only=False):
        query = urlencode({"active_only": str(active_only).lower()})
        result = CatalogClient._request_json(f"/salones?{query}")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise CatalogUnavailableError("Catalog devolvió un listado de salones inválido.")
        return result

    @staticmethod
    def create_salon(numero, descripcion, capacidad, id_plantel, token):
        result = CatalogClient._request_json(
            "/salones",
            method="POST",
            payload={
                "numero": numero,
                "descripcion": descripcion or None,
                "capacidad": capacidad,
                "id_plantel": id_plantel,
            },
            token=token,
        )
        if not isinstance(result, dict) or not result.get("id_salon"):
            raise CatalogUnavailableError("Catalog devolvió un salón incompleto.")
        return result

    @staticmethod
    def get_salon(salon_id):
        result = CatalogClient._request_json(f"/salones/{salon_id}")
        if (
            not isinstance(result, dict)
            or result.get("id_salon") != salon_id
            or not result.get("numero")
        ):
            raise CatalogUnavailableError("Catalog devolvió un salón incompleto.")
        return result

    @staticmethod
    def update_salon(salon_id, numero, descripcion, capacidad, id_plantel, token):
        result = CatalogClient._request_json(
            f"/salones/{salon_id}",
            method="PUT",
            payload={
                "numero": numero,
                "descripcion": descripcion or None,
                "capacidad": capacidad,
                "id_plantel": id_plantel,
            },
            token=token,
        )
        if (
            not isinstance(result, dict)
            or result.get("id_salon") != salon_id
            or not result.get("numero")
        ):
            raise CatalogUnavailableError("Catalog devolvió un salón actualizado incompleto.")
        return result

    @staticmethod
    def deactivate_salon(salon_id, token):
        result = CatalogClient._request_json(
            f"/salones/{salon_id}",
            method="DELETE",
            token=token,
        )
        if not isinstance(result, dict) or not result.get("message"):
            raise CatalogUnavailableError(
                "Catalog devolvió una confirmación de desactivación incompleta."
            )
        return result

    @staticmethod
    def list_equipos(active_only=False):
        query = urlencode({"active_only": str(active_only).lower()})
        result = CatalogClient._request_json(f"/equipos?{query}")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise CatalogUnavailableError("Catalog devolvió un listado de equipos inválido.")
        return result

    @staticmethod
    def create_equipo(numero, descripcion, id_salon, token):
        result = CatalogClient._request_json(
            "/equipos",
            method="POST",
            payload={
                "numero": numero,
                "descripcion": descripcion or None,
                "id_salon": id_salon,
            },
            token=token,
        )
        if not isinstance(result, dict) or not result.get("id_equipo"):
            raise CatalogUnavailableError("Catalog devolvió un equipo incompleto.")
        return result

    @staticmethod
    def get_equipo(equipo_id):
        result = CatalogClient._request_json(f"/equipos/{equipo_id}")
        if (
            not isinstance(result, dict)
            or result.get("id_equipo") != equipo_id
            or not result.get("numero")
        ):
            raise CatalogUnavailableError("Catalog devolvió un equipo incompleto.")
        return result

    @staticmethod
    def update_equipo(equipo_id, numero, descripcion, id_salon, token):
        result = CatalogClient._request_json(
            f"/equipos/{equipo_id}",
            method="PUT",
            payload={
                "numero": numero,
                "descripcion": descripcion or None,
                "id_salon": id_salon,
            },
            token=token,
        )
        if (
            not isinstance(result, dict)
            or result.get("id_equipo") != equipo_id
            or not result.get("numero")
        ):
            raise CatalogUnavailableError("Catalog devolvió un equipo actualizado incompleto.")
        return result

    @staticmethod
    def deactivate_equipo(equipo_id, token):
        result = CatalogClient._request_json(
            f"/equipos/{equipo_id}",
            method="DELETE",
            token=token,
        )
        if not isinstance(result, dict) or not result.get("message"):
            raise CatalogUnavailableError(
                "Catalog devolvió una confirmación de desactivación incompleta."
            )
        return result

    @staticmethod
    def list_programas(active_only=False):
        query = urlencode({"active_only": str(active_only).lower()})
        result = CatalogClient._request_json(f"/programas?{query}")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise CatalogUnavailableError("Catalog devolvió un listado de programas inválido.")
        return result

    @staticmethod
    def create_programa(nombre, descripcion, token):
        result = CatalogClient._request_json(
            "/programas",
            method="POST",
            payload={"nombre": nombre, "descripcion": descripcion or None},
            token=token,
        )
        if not isinstance(result, dict) or not result.get("id_programa"):
            raise CatalogUnavailableError("Catalog devolvió un programa incompleto.")
        return result

    @staticmethod
    def get_programa(programa_id):
        result = CatalogClient._request_json(f"/programas/{programa_id}")
        if (
            not isinstance(result, dict)
            or result.get("id_programa") != programa_id
            or not result.get("nombre")
        ):
            raise CatalogUnavailableError("Catalog devolvió un programa incompleto.")
        return result

    @staticmethod
    def update_programa(programa_id, nombre, descripcion, token):
        result = CatalogClient._request_json(
            f"/programas/{programa_id}",
            method="PUT",
            payload={"nombre": nombre, "descripcion": descripcion or None},
            token=token,
        )
        if (
            not isinstance(result, dict)
            or result.get("id_programa") != programa_id
            or not result.get("nombre")
        ):
            raise CatalogUnavailableError("Catalog devolvió un programa actualizado incompleto.")
        return result

    @staticmethod
    def deactivate_programa(programa_id, token):
        result = CatalogClient._request_json(
            f"/programas/{programa_id}",
            method="DELETE",
            token=token,
        )
        if not isinstance(result, dict) or not result.get("message"):
            raise CatalogUnavailableError(
                "Catalog devolvió una confirmación de desactivación incompleta."
            )
        return result

    @staticmethod
    def assign_programa(equipo_id, programa_id, token):
        result = CatalogClient._request_json(
            f"/equipos/{equipo_id}/software",
            method="POST",
            payload={"id_programa": programa_id},
            token=token,
        )
        associated_ids = {
            programa.get("id_programa")
            for programa in result.get("programas", [])
            if isinstance(programa, dict)
        } if isinstance(result, dict) else set()
        if (
            not isinstance(result, dict)
            or result.get("id_equipo") != equipo_id
            or programa_id not in associated_ids
        ):
            raise CatalogUnavailableError(
                "Catalog devolvió una asociación de programa incompleta."
            )
        return result

    @staticmethod
    def remove_programa(equipo_id, programa_id, token):
        result = CatalogClient._request_json(
            f"/equipos/{equipo_id}/software/{programa_id}",
            method="DELETE",
            token=token,
        )
        if not isinstance(result, dict) or not result.get("message"):
            raise CatalogUnavailableError(
                "Catalog devolvió una confirmación de desvinculación incompleta."
            )
        return result

    @staticmethod
    def _request_json(path, method="GET", payload=None, token=None):
        base_url = current_app.config["CATALOG_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["CATALOG_REQUEST_TIMEOUT"]
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = Request(
            f"{base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                return CatalogClient._read_json(response)
        except HTTPError as error:
            result = CatalogClient._read_json(error)
            message = result.get("error", "Catalog rechazó la solicitud.")
            if error.code in {400, 404, 409}:
                raise CatalogValidationError(message) from error
            if error.code in {401, 403}:
                raise CatalogAuthorizationError(message, error.code) from error
            raise CatalogUnavailableError("Catalog no pudo procesar la solicitud.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise CatalogUnavailableError(
                "El servicio de catálogos no está disponible. Intenta nuevamente más tarde."
            ) from error

    @staticmethod
    def _read_json(response):
        try:
            body = response.read().decode("utf-8")
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
            raise CatalogUnavailableError(
                "Catalog devolvió una respuesta que no se pudo interpretar."
            ) from error
