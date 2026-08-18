"""Pruebas unitarias del alcance de asociaciones de software por equipo."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from catalog.app.services.catalog_service import (
    EquipmentService,
    PermissionDeniedException,
)


@pytest.mark.parametrize("operation", ["assign_software", "remove_software"])
def test_scoped_role_cannot_manage_software_on_unassigned_equipment(operation):
    equipo = SimpleNamespace(id_salon=None, programas=[])
    current_user = {"rol": "ADMIN_PLANTEL", "id_plantel": 1}

    with patch.object(
        EquipmentService,
        "get_equipment_by_id",
        return_value=equipo,
    ), patch(
        "catalog.app.services.catalog_service.ProgramService.get_program_by_id"
    ) as program_mock, pytest.raises(
        PermissionDeniedException,
        match="Solo administradores globales",
    ):
        getattr(EquipmentService, operation)(1, 2, current_user=current_user)

    program_mock.assert_not_called()


def test_scoped_role_cannot_assign_software_outside_its_plantel():
    equipo = SimpleNamespace(id_salon=10, programas=[])
    foreign_salon = SimpleNamespace(id_plantel=2)
    current_user = {"rol": "ADMIN_PLANTEL", "id_plantel": 1}

    with patch.object(
        EquipmentService,
        "get_equipment_by_id",
        return_value=equipo,
    ), patch(
        "catalog.app.services.catalog_service.CampusService.get_salon_by_id",
        return_value=foreign_salon,
    ), patch(
        "catalog.app.services.catalog_service.ProgramService.get_program_by_id"
    ) as program_mock, pytest.raises(
        PermissionDeniedException,
        match="otro plantel",
    ):
        EquipmentService.assign_software(1, 2, current_user=current_user)

    program_mock.assert_not_called()


def test_global_role_can_assign_software_to_unassigned_equipment():
    equipo = SimpleNamespace(id_salon=None, programas=[])
    programa = SimpleNamespace(id_programa=2)
    current_user = {"rol": "COORDINADOR", "id_plantel": None}

    with patch.object(
        EquipmentService,
        "get_equipment_by_id",
        return_value=equipo,
    ), patch(
        "catalog.app.services.catalog_service.ProgramService.get_program_by_id",
        return_value=programa,
    ), patch("catalog.app.services.catalog_service.db.session.commit") as commit_mock:
        result = EquipmentService.assign_software(
            1, 2, current_user=current_user
        )

    assert result is equipo
    assert equipo.programas == [programa]
    commit_mock.assert_called_once_with()
