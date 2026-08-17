from unittest.mock import patch

from app.models.usuario import Usuario
from app.services.auth_service import AuthService
from app.utils.security import generate_token


def _create_user(**overrides):
    data = {
        "nombre": "Usuario",
        "apellido": "Prueba",
        "correo": "usuario@udl.edu.mx",
        "password": "Password123!",
        "rol": "DOCENTE",
        "id_plantel_asignado": 1,
    }
    data.update(overrides)
    with patch("app.services.auth_service.CatalogClient.plantel_exists", return_value=True):
        result = AuthService.register_user(data)
    assert result["success"] is True
    return result["data"]


def _actor(user_id, role, plantel_id=None):
    return {
        "id_usuario": user_id,
        "correo": f"{role.lower()}@udl.edu.mx",
        "rol": role,
        "id_plantel_asignado": plantel_id,
    }


def test_admin_plantel_lists_only_users_from_assigned_plantel(db_session, app):
    with app.app_context():
        _create_user(correo="uno@udl.edu.mx", id_plantel_asignado=1)
        _create_user(correo="dos@udl.edu.mx", id_plantel_asignado=2)
        _create_user(
            correo="coordinador@udl.edu.mx",
            rol="COORDINADOR",
            id_plantel_asignado=1,
        )

        result = AuthService.list_users(_actor(20, "ADMIN_PLANTEL", 1))

        assert result["success"] is True
        assert [user["correo"] for user in result["data"]] == ["uno@udl.edu.mx"]


def test_admin_plantel_cannot_create_coordinator_or_cross_tenant_user(db_session, app):
    with app.app_context():
        actor = _actor(20, "ADMIN_PLANTEL", 1)
        coordinator = AuthService.register_user(
            {
                "nombre": "Nuevo", "apellido": "Coordinador",
                "correo": "coord@udl.edu.mx", "password": "Password123!",
                "rol": "COORDINADOR", "id_plantel_asignado": 1,
            },
            actor,
        )
        foreign = AuthService.register_user(
            {
                "nombre": "Docente", "apellido": "Foraneo",
                "correo": "foraneo@udl.edu.mx", "password": "Password123!",
                "rol": "DOCENTE", "id_plantel_asignado": 2,
            },
            actor,
        )

        assert coordinator["status_code"] == 403
        assert foreign["status_code"] == 403


def test_admin_plantel_can_read_own_user_but_not_foreign_user(db_session, app):
    with app.app_context():
        own = _create_user(correo="propio@udl.edu.mx", id_plantel_asignado=1)
        foreign = _create_user(correo="foraneo@udl.edu.mx", id_plantel_asignado=2)
        actor = _actor(20, "ADMIN_PLANTEL", 1)

        own_result = AuthService.get_user(own["id_usuario"], actor)
        foreign_result = AuthService.get_user(foreign["id_usuario"], actor)

        assert own_result["success"] is True
        assert foreign_result["status_code"] == 403


def test_update_changes_profile_and_only_replaces_password_when_supplied(db_session, app):
    with app.app_context():
        created = _create_user()
        actor = _actor(99, "COORDINADOR")
        user = db_session.session.get(Usuario, created["id_usuario"])
        original_hash = user.password_hash

        with patch("app.services.auth_service.CatalogClient.plantel_exists", return_value=True):
            result = AuthService.update_user(
                created["id_usuario"],
                {
                    "nombre": "Nombre actualizado", "apellido": "Prueba",
                    "correo": "actualizado@udl.edu.mx", "rol": "DOCENTE",
                    "id_plantel_asignado": 1,
                },
                actor,
            )

        assert result["success"] is True
        assert result["data"]["nombre"] == "Nombre actualizado"
        assert user.password_hash == original_hash


def test_user_routes_update_and_soft_delete_with_coordinator(db_session, app, client):
    with app.app_context():
        coordinator = _create_user(
            nombre="Admin", apellido="Global", correo="admin@udl.edu.mx",
            rol="COORDINADOR", id_plantel_asignado=None,
        )
        target = _create_user(correo="target@udl.edu.mx")
        token = generate_token(db_session.session.get(Usuario, coordinator["id_usuario"]))

        with patch("app.services.auth_service.CatalogClient.plantel_exists", return_value=True):
            update_response = client.put(
                f'/api/v1/auth/users/{target["id_usuario"]}',
                json={
                    "nombre": "Editado", "apellido": "Prueba",
                    "correo": "editado@udl.edu.mx", "rol": "DOCENTE",
                    "id_plantel_asignado": 1, "password": "NuevaClave123!",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        delete_response = client.delete(
            f'/api/v1/auth/users/{target["id_usuario"]}',
            headers={"Authorization": f"Bearer {token}"},
        )

        assert update_response.status_code == 200
        assert update_response.json["usuario"]["nombre"] == "Editado"
        assert delete_response.status_code == 200
        assert delete_response.json["usuario"]["activo"] is False


def test_cannot_deactivate_own_account(db_session, app):
    with app.app_context():
        created = _create_user(
            correo="admin@udl.edu.mx", rol="COORDINADOR", id_plantel_asignado=None,
        )
        result = AuthService.deactivate_user(
            created["id_usuario"],
            _actor(created["id_usuario"], "COORDINADOR"),
        )

        assert result["status_code"] == 403
        assert db_session.session.get(Usuario, created["id_usuario"]).activo is True
