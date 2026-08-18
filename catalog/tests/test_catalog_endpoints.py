import pytest

from catalog.app.services.catalog_service import (
    CampusService,
    EquipmentService,
    ProgramService,
)


def test_public_get_endpoints_no_auth(catalog_db, catalog_app, catalog_client):
    """Verifica que los endpoints GET públicos de catalog respondan 200 sin autenticación."""
    with catalog_app.app_context():
        plantel = CampusService.create_plantel('Plantel Público')
        plantel_id = plantel.id
        salon = CampusService.create_salon('101', 'Aula pública', 20, plantel_id)
        programa = ProgramService.create_program('Programa Público')
        EquipmentService.create_equipment('EQ-100', 'Equipo público', id_salon=salon.id_salon)

    response = catalog_client.get('/api/v1/planteles')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = catalog_client.get(f'/api/v1/planteles/{plantel_id}')
    assert response.status_code == 200
    assert response.json['nombre'] == 'Plantel Público'

    response = catalog_client.get('/api/v1/salones')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = catalog_client.get('/api/v1/equipos')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = catalog_client.get('/api/v1/programas')
    assert response.status_code == 200
    assert isinstance(response.json, list)
