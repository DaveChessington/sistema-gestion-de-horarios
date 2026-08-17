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
        plantel = CampusService.create_plantel("Plantel X", direccion="Dirección X")
        assert plantel.id is not None
        assert plantel.nombre == "Plantel X"


def test_create_plantel_invalid_name(db_session, app):
    with app.app_context(), pytest.raises(InvalidDataException):
        CampusService.create_plantel("   ")


def test_create_salon_and_list(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel("Plantel Y")
        salon = CampusService.create_salon("101", "Aula 101", 25, plantel.id)
        assert salon.id_salon is not None
        assert any(
            item.id_salon == salon.id_salon
            for item in CampusService.list_salones(id_plantel=plantel.id)
        )


def test_create_equipment_duplicate(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel("Plantel Z")
        salon = CampusService.create_salon("201", "Aula 201", 20, plantel.id)
        EquipmentService.create_equipment("EQ-001", "Equipo 1", id_salon=salon.id_salon)
        with pytest.raises(DuplicateEntityException):
            EquipmentService.create_equipment("EQ-001", "Equipo duplicado")


def test_assign_and_remove_software(db_session, app):
    with app.app_context():
        programa = ProgramService.create_program("Programa A")
        plantel = CampusService.create_plantel("Plantel W")
        salon = CampusService.create_salon("301", "Aula 301", 15, plantel.id)
        equipo = EquipmentService.create_equipment("EQ-002", "Equipo 2", id_salon=salon.id_salon)
        equipo = EquipmentService.assign_software(equipo.id_equipo, programa.id_programa)
        assert any(item.id_programa == programa.id_programa for item in equipo.programas)
        result = EquipmentService.remove_software(equipo.id_equipo, programa.id_programa)
        assert "desinstalado" in result["message"]


def test_get_nonexistent_entities(db_session, app):
    with app.app_context():
        with pytest.raises(EntityNotFoundException):
            CampusService.get_plantel_by_id(999999)
        with pytest.raises(EntityNotFoundException):
            ProgramService.get_program_by_id(999999)


def test_public_get_endpoints_no_auth(db_session, app, client):
    with app.app_context():
        plantel = CampusService.create_plantel("Plantel Público")
        plantel_id = plantel.id
        salon = CampusService.create_salon("101", "Aula pública", 20, plantel.id)
        ProgramService.create_program("Programa Público")
        EquipmentService.create_equipment("EQ-100", "Equipo público", id_salon=salon.id_salon)
    assert client.get("/api/v1/planteles").status_code == 200
    assert client.get(f"/api/v1/planteles/{plantel_id}").status_code == 200
    assert client.get("/api/v1/salones").status_code == 200
    assert client.get("/api/v1/equipos").status_code == 200
    assert client.get("/api/v1/programas").status_code == 200


def test_scoped_plantel_permission_checks(db_session, app):
    with app.app_context():
        p1 = CampusService.create_plantel("Plantel A")
        p2 = CampusService.create_plantel("Plantel B")
        admin_p1 = {"id_usuario": 2, "rol": "ADMIN_PLANTEL", "id_plantel": p1.id}
        admin_p2 = {"id_usuario": 3, "rol": "ADMIN_PLANTEL", "id_plantel": p2.id}
        salon = CampusService.create_salon("S1", "Salon P1", 30, p1.id, current_user=admin_p1)
        with pytest.raises(PermissionDeniedException):
            CampusService.create_salon("S2", "Salon P2", 30, p2.id, current_user=admin_p1)
        CampusService.update_salon(salon.id_salon, "S1-Mod", "Salon P1 Mod", 35, p1.id, current_user=admin_p1)
        with pytest.raises(PermissionDeniedException):
            CampusService.update_salon(salon.id_salon, "Hack", "Hack", 35, p1.id, current_user=admin_p2)
        equipment = EquipmentService.create_equipment("EQ-P1", "PC P1", id_salon=salon.id_salon, current_user=admin_p1)
        with pytest.raises(PermissionDeniedException):
            EquipmentService.update_equipment(equipment.id_equipo, "EQ-P1-Mod", "Mod", id_salon=salon.id_salon, current_user=admin_p2)
