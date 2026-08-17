from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.utils.security import generate_token


REGISTER_URL = '/api/v1/auth/register'
VALID_USER_DATA = {
    'nombre': 'Usuario',
    'apellido': 'Nuevo',
    'correo': 'usuario.nuevo@udl.edu.mx',
    'password': 'Password123!',
    'rol': 'DOCENTE'
}


def _token_for_role(app, role, user_id=1, plantel_id=None):
    usuario = SimpleNamespace(
        id_usuario=user_id,
        correo=f'{role.lower()}@udl.edu.mx',
        rol=role,
        id_plantel_asignado=plantel_id
    )
    with app.app_context():
        return generate_token(usuario)


def test_register_requires_authentication(client):
    with patch('app.routes.auth_routes.AuthService.register_user') as register_user:
        response = client.post(REGISTER_URL, json=VALID_USER_DATA)

    assert response.status_code == 401
    register_user.assert_not_called()


def test_register_rejects_non_administrative_role(app, client):
    token = _token_for_role(app, 'DOCENTE')

    with patch('app.routes.auth_routes.AuthService.register_user') as register_user:
        response = client.post(
            REGISTER_URL,
            json=VALID_USER_DATA,
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 403
    register_user.assert_not_called()


@pytest.mark.parametrize('role', ['COORDINADOR', 'ADMIN_PLANTEL'])
def test_register_allows_administrative_roles(app, client, role):
    token = _token_for_role(app, role)
    service_result = {
        'success': True,
        'data': {
            'id_usuario': 2,
            'nombre': 'Usuario',
            'apellido': 'Nuevo',
            'correo': 'usuario.nuevo@udl.edu.mx',
            'rol': 'DOCENTE',
            'activo': True,
            'id_plantel_asignado': None
        },
        'status_code': 201
    }

    with patch(
        'app.routes.auth_routes.AuthService.register_user',
        return_value=service_result
    ) as register_user:
        response = client.post(
            REGISTER_URL,
            json=VALID_USER_DATA,
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 201
    register_user.assert_called_once()
    submitted_data, actor = register_user.call_args.args
    assert submitted_data == VALID_USER_DATA
    assert actor['id_usuario'] == 1
    assert actor['rol'] == role
