from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app.models.usuario import BCRYPT_ROUNDS, RolUsuario, Usuario
from app.services.auth_service import AuthService


def test_new_password_uses_bcrypt_cost_12(db_session, app):
    with app.app_context(), patch(
        "app.services.auth_service.CatalogClient.plantel_exists",
        return_value=True,
    ):
        result = AuthService.register_user({
            "nombre": "Usuario",
            "apellido": "Seguro",
            "correo": "seguro@udl.edu.mx",
            "password": "Password-Segura123!",
            "rol": "DOCENTE",
            "id_plantel_asignado": 1,
        })
        user = db_session.session.get(Usuario, result["data"]["id_usuario"])

    assert result["status_code"] == 201
    assert user.password_hash.startswith("$2b$12$")
    assert int(user.password_hash.split("$")[2]) == BCRYPT_ROUNDS
    assert user.check_password("Password-Segura123!") is True
    assert user.check_password("Password-Incorrecta123!") is False


@pytest.mark.parametrize(
    "password",
    [
        "Corta1!",
        "sin-mayuscula-123!",
        "SIN-MINUSCULA-123!",
        "SinNumero-Especial!",
        "SinCaracterEspecial123",
        "Contraseña1!" * 8,
    ],
)
def test_password_policy_rejects_weak_or_oversized_values(db_session, app, password):
    with app.app_context():
        result = AuthService.register_user({
            "nombre": "Usuario",
            "apellido": "Inseguro",
            "correo": "inseguro@udl.edu.mx",
            "password": password,
            "rol": "DOCENTE",
        })

    assert result["status_code"] == 400


def test_successful_login_migrates_legacy_werkzeug_hash(db_session, app):
    password = "Legacy-Password123!"
    with app.app_context():
        user = Usuario(
            nombre="Usuario",
            apellido="Heredado",
            correo="heredado@udl.edu.mx",
            password_hash=generate_password_hash(password),
            rol=RolUsuario.DOCENTE,
            activo=True,
        )
        db_session.session.add(user)
        db_session.session.commit()
        legacy_hash = user.password_hash

        result = AuthService.login(user.correo, password)
        migrated_hash = user.password_hash

    assert result["success"] is True
    assert not legacy_hash.startswith("$2")
    assert migrated_hash.startswith("$2b$12$")
    assert migrated_hash != legacy_hash
