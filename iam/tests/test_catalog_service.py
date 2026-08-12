import pytest

from catalog.app.services.catalog_service import (
    CampusService,
    DuplicateEntityException,
    EntityNotFoundException,
    EquipmentService,
    InvalidDataException,
    PermissionDeniedException,
    ProgramService,
)


def test_create_plantel_success(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel X', direccion='Dirección X')
        assert plantel.id is not None
        assert plantel.nombre == 'Plantel X'


def test_create_plantel_invalid_name(db_session, app):
    with app.app_context():
        with pytest.raises(InvalidDataException):
            CampusService.create_plantel('   ')


def test_create_salon_and_list(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Y')
        salon = CampusService.create_salon('101', 'Aula 101', 25, plantel.id)
        assert salon.id_salon is not None
        assert salon.numero == '101'
        salones = CampusService.list_salones(id_plantel=plantel.id)
        assert any(s.id_salon == salon.id_salon for s in salones)


def test_create_equipment_duplicate(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Z')
        salon = CampusService.create_salon('201', 'Aula 201', 20, plantel.id)
        e1 = EquipmentService.create_equipment('EQ-001', 'Equipo 1', id_salon=salon.id_salon)
        assert e1.id_equipo is not None
        with pytest.raises(DuplicateEntityException):
            EquipmentService.create_equipment('EQ-001', 'Equipo duplicado')


def test_assign_and_remove_software(db_session, app):
    with app.app_context():
        programa = ProgramService.create_program('Programa A')
        plantel = CampusService.create_plantel('Plantel W')
        salon = CampusService.create_salon('301', 'Aula 301', 15, plantel.id)
        equipo = EquipmentService.create_equipment('EQ-002', 'Equipo 2', id_salon=salon.id_salon)

        equipo = EquipmentService.assign_software(equipo.id_equipo, programa.id_programa)
        assert any(p.id_programa == programa.id_programa for p in equipo.programas)

        res = EquipmentService.remove_software(equipo.id_equipo, programa.id_programa)
        assert 'desinstalado' in res['message']


def test_get_nonexistent_entities(db_session, app):
    with app.app_context():
        with pytest.raises(EntityNotFoundException):
            CampusService.get_plantel_by_id(999999)
        with pytest.raises(EntityNotFoundException):
            ProgramService.get_program_by_id(999999)


def test_public_get_endpoints_no_auth(db_session, app, client):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Público')
        plantel_id = plantel.id
        salon = CampusService.create_salon('101', 'Aula pública', 20, plantel_id)
        programa = ProgramService.create_program('Programa Público')
        EquipmentService.create_equipment('EQ-100', 'Equipo público', id_salon=salon.id_salon)

    response = client.get('/api/v1/planteles')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get(f'/api/v1/planteles/{plantel_id}')
    assert response.status_code == 200
    assert response.json['nombre'] == 'Plantel Público'

    response = client.get('/api/v1/salones')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get('/api/v1/equipos')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get('/api/v1/programas')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_encargado_plantel_permission_checks(db_session, app):
    with app.app_context():
        p1 = CampusService.create_plantel('Plantel A')
        p2 = CampusService.create_plantel('Plantel B')

        encargado_p1 = {'id_usuario': 2, 'rol': 'ENCARGADO', 'id_plantel': p1.id}
        encargado_p2 = {'id_usuario': 3, 'rol': 'ENCARGADO', 'id_plantel': p2.id}

        # Encargado de P1 crea salón en P1 -> Exitoso
        salon_p1 = CampusService.create_salon('S1', 'Salon P1', 30, p1.id, current_user=encargado_p1)
        assert salon_p1.id_salon is not None

        # Encargado de P1 intenta crear salón en P2 -> Denegado (403 PermissionDeniedException)
        with pytest.raises(PermissionDeniedException):
            CampusService.create_salon('S2', 'Salon P2', 30, p2.id, current_user=encargado_p1)

        # Encargado de P1 intenta actualizar salón de P1 -> Exitoso
        updated_s1 = CampusService.update_salon(salon_p1.id_salon, 'S1-Mod', 'Salon P1 Mod', 35, p1.id, current_user=encargado_p1)
        assert updated_s1.numero == 'S1-Mod'

        # Encargado de P2 intenta actualizar salón de P1 -> Denegado
        with pytest.raises(PermissionDeniedException):
            CampusService.update_salon(salon_p1.id_salon, 'Hack', 'Hack', 35, p1.id, current_user=encargado_p2)

        # Equipo en P1
        eq_p1 = EquipmentService.create_equipment('EQ-P1', 'PC P1', id_salon=salon_p1.id_salon, current_user=encargado_p1)
        assert eq_p1.id_equipo is not None

        # Encargado de P2 intenta modificar equipo en P1 -> Denegado
        with pytest.raises(PermissionDeniedException):
            EquipmentService.update_equipment(eq_p1.id_equipo, 'EQ-P1-Mod', 'Mod', id_salon=salon_p1.id_salon, current_user=encargado_p2)


