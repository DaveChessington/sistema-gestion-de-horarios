from unittest.mock import patch

from app.services.auth_service import AuthService


def test_register_user_with_valid_plantel(db_session, app):
    with app.app_context():
        with patch('app.services.catalog_client.CatalogClient.plantel_exists', return_value=True):
            resultado = AuthService.register_user({
                'nombre': 'Admin',
                'apellido': 'Plantel',
                'correo': 'adminplantel@udl.edu.mx',
                'password': 'password123',
                'rol': 'ADMIN_PLANTEL',
                'id_plantel_asignado': 1
            })

        assert resultado['success'] is True
        assert resultado['status_code'] == 201
        assert resultado['data']['id_plantel_asignado'] == 1


def test_register_user_with_invalid_plantel(db_session, app):
    with app.app_context():
        with patch('app.services.catalog_client.CatalogClient.plantel_exists', return_value=False):
            resultado = AuthService.register_user({
                'nombre': 'User',
                'apellido': 'Invalido',
                'correo': 'usuario_invalidoplantel@udl.edu.mx',
                'password': 'password123',
                'rol': 'DOCENTE',
                'id_plantel_asignado': 9999
            })

        assert resultado['success'] is False
        assert resultado['status_code'] == 400
        assert 'no existe en el catálogo' in resultado['error']


def test_users_endpoint_returns_list_for_admin(db_session, app, client):
    with app.app_context():
        with patch('app.services.catalog_client.CatalogClient.plantel_exists', return_value=True):
            AuthService.register_user({
                'nombre': 'Admin',
                'apellido': 'Sistema',
                'correo': 'admin@udl.edu.mx',
                'password': 'password123',
                'rol': 'COORDINADOR'
            })
            AuthService.register_user({
                'nombre': 'Docente',
                'apellido': 'Prueba',
                'correo': 'docente@udl.edu.mx',
                'password': 'password123',
                'rol': 'DOCENTE'
            })

        login_result = AuthService.login('admin@udl.edu.mx', 'password123')
        token = login_result['token']

        response = client.get(
            '/api/v1/auth/users',
            headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == 200
        assert 'usuarios' in response.json
        assert len(response.json['usuarios']) >= 2
