"""Adaptador del frontend para consumir el contrato público de IAM."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


class IAMClientError(Exception):
    """Error controlado al comunicarse con IAM."""


class IAMAuthenticationError(IAMClientError):
    """IAM rechazó las credenciales o el estado de la cuenta."""


class IAMAuthorizationError(IAMClientError):
    """IAM rechazó el JWT o los permisos administrativos."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class IAMValidationError(IAMClientError):
    """IAM rechazó los datos de registro de un usuario."""


class IAMUnavailableError(IAMClientError):
    """IAM no respondió o devolvió una respuesta inválida."""


class IAMClient:
    """Consume IAM sin incorporar su lógica de autenticación al frontend."""

    @staticmethod
    def login(correo, password):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        payload = json.dumps({"correo": correo, "password": password}).encode("utf-8")
        request = Request(
            f"{base_url}/login",
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó la solicitud de acceso.")
            if error.code in {400, 401, 403}:
                raise IAMAuthenticationError(message) from error
            raise IAMUnavailableError("IAM no pudo procesar la solicitud.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError(
                "El servicio de identidad no está disponible. Intenta nuevamente más tarde."
            ) from error

        token = result.get("token")
        usuario = result.get("usuario")
        if not isinstance(token, str) or not token or not isinstance(usuario, dict):
            raise IAMUnavailableError("IAM devolvió una respuesta de acceso incompleta.")
        return {"token": token, "usuario": usuario}

    @staticmethod
    def list_users(token):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/users",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó la consulta de usuarios.")
            if error.code in {401, 403}:
                raise IAMAuthorizationError(message, error.code) from error
            raise IAMUnavailableError("IAM no pudo consultar los usuarios.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError(
                "El servicio de identidad no está disponible. Intenta nuevamente más tarde."
            ) from error

        usuarios = result.get("usuarios")
        if not isinstance(usuarios, list) or not all(isinstance(item, dict) for item in usuarios):
            raise IAMUnavailableError("IAM devolvió un listado de usuarios inválido.")
        return usuarios

    @staticmethod
    def register_user(user_data, token):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/register",
            data=json.dumps(user_data).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó el registro del usuario.")
            if error.code in {400, 409}:
                raise IAMValidationError(message) from error
            if error.code in {401, 403}:
                raise IAMAuthorizationError(message, error.code) from error
            raise IAMUnavailableError(message) from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError(
                "El servicio de identidad no está disponible. Intenta nuevamente más tarde."
            ) from error

        usuario = result.get("usuario")
        if not isinstance(usuario, dict) or not usuario.get("id_usuario"):
            raise IAMUnavailableError("IAM devolvió un usuario incompleto.")
        return usuario

    @staticmethod
    def get_user(user_id, token):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/users/{user_id}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó la consulta del usuario.")
            if error.code in {400, 404}:
                raise IAMValidationError(message) from error
            if error.code in {401, 403}:
                raise IAMAuthorizationError(message, error.code) from error
            raise IAMUnavailableError(message) from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError("El servicio de identidad no está disponible. Intenta nuevamente más tarde.") from error
        usuario = result.get("usuario")
        if not isinstance(usuario, dict) or not usuario.get("id_usuario"):
            raise IAMUnavailableError("IAM devolvió un usuario incompleto.")
        return usuario

    @staticmethod
    def update_user(user_id, user_data, token):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/users/{user_id}",
            data=json.dumps(user_data).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó la actualización del usuario.")
            if error.code in {400, 404, 409}:
                raise IAMValidationError(message) from error
            if error.code in {401, 403}:
                raise IAMAuthorizationError(message, error.code) from error
            raise IAMUnavailableError(message) from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError("El servicio de identidad no está disponible. Intenta nuevamente más tarde.") from error
        usuario = result.get("usuario")
        if not isinstance(usuario, dict) or not usuario.get("id_usuario"):
            raise IAMUnavailableError("IAM devolvió un usuario incompleto.")
        return usuario

    @staticmethod
    def deactivate_user(user_id, token):
        base_url = current_app.config["IAM_API_BASE_URL"].rstrip("/")
        timeout = current_app.config["IAM_REQUEST_TIMEOUT"]
        request = Request(
            f"{base_url}/users/{user_id}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                result = IAMClient._read_json(response)
        except HTTPError as error:
            result = IAMClient._read_json(error)
            message = result.get("error", "IAM rechazó la desactivación del usuario.")
            if error.code in {400, 404, 409}:
                raise IAMValidationError(message) from error
            if error.code in {401, 403}:
                raise IAMAuthorizationError(message, error.code) from error
            raise IAMUnavailableError(message) from error
        except (URLError, TimeoutError, OSError) as error:
            raise IAMUnavailableError("El servicio de identidad no está disponible. Intenta nuevamente más tarde.") from error
        usuario = result.get("usuario")
        if not isinstance(usuario, dict) or usuario.get("activo") is not False:
            raise IAMUnavailableError("IAM devolvió una desactivación incompleta.")
        return usuario

    @staticmethod
    def _read_json(response):
        try:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
            raise IAMUnavailableError("IAM devolvió una respuesta que no se pudo interpretar.") from error
        return parsed if isinstance(parsed, dict) else {}
