"""Pruebas básicas del contenedor administrativo visual."""

import json
import re

from unittest.mock import patch

import pytest

from schedule.app import create_app
from schedule.app.clients.booking_client import (
    BookingAuthorizationError,
    BookingUnavailableError,
    BookingValidationError,
)
from schedule.app.clients.catalog_client import (
    CatalogAuthorizationError,
    CatalogUnavailableError,
)
from schedule.app.clients.iam_client import (
    IAMAuthorizationError,
    IAMUnavailableError,
    IAMValidationError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    CATALOG_API_BASE_URL = "http://catalog.test/api/v1"
    CATALOG_REQUEST_TIMEOUT = 1
    IAM_API_BASE_URL = "http://iam.test/api/v1/auth"
    IAM_REQUEST_TIMEOUT = 1
    BOOKING_API_BASE_URL = "http://booking.test/api/v1"
    BOOKING_REQUEST_TIMEOUT = 1


PLANTELES = [
    {"id": 1, "nombre": "Plantel León", "direccion": "León, Guanajuato", "activo": True},
    {"id": 2, "nombre": "Plantel Centro", "direccion": "Zona Centro", "activo": True},
    {"id": 3, "nombre": "Plantel Norte", "direccion": "Zona Norte", "activo": False},
]

SALONES = [
    {
        "id_salon": 101,
        "numero": "Laboratorio 01",
        "descripcion": "Cómputo general",
        "capacidad": 30,
        "id_plantel": 1,
        "activo": True,
    },
    {
        "id_salon": 102,
        "numero": "Aula 02",
        "descripcion": "Aula teórica",
        "capacidad": 25,
        "id_plantel": 2,
        "activo": False,
    },
]

EQUIPOS = [
    {
        "id_equipo": 201,
        "numero": "PC-001",
        "descripcion": "Estación de trabajo",
        "activo": True,
        "id_salon": 101,
        "programas": [
            {
                "id_programa": 1,
                "nombre": "Editor académico",
                "descripcion": None,
                "activo": True,
            }
        ],
    }
]

PROGRAMAS = [
    {
        "id_programa": 1,
        "nombre": "Python",
        "descripcion": "Entorno académico",
        "activo": True,
    },
    {
        "id_programa": 2,
        "nombre": "Docker Desktop",
        "descripcion": "Contenedores",
        "activo": False,
    },
]

USUARIOS = [
    {
        "id_usuario": 1,
        "nombre": "Ana",
        "apellido": "Coordinadora",
        "correo": "ana@udl.edu.mx",
        "rol": "COORDINADOR",
        "prioridad": 4,
        "activo": True,
        "id_plantel_asignado": None,
    },
    {
        "id_usuario": 2,
        "nombre": "Luis",
        "apellido": "Docente",
        "correo": "luis@udl.edu.mx",
        "rol": "DOCENTE",
        "prioridad": 2,
        "activo": False,
        "id_plantel_asignado": 1,
    },
]


def authenticated_client(role="COORDINADOR"):
    app = create_app(TestConfig)
    client = app.test_client()
    with client.session_transaction() as frontend_session:
        frontend_session["iam_token"] = "test-token"
        frontend_session["iam_user"] = {
            "id_usuario": 1,
            "nombre": "Usuario",
            "apellido": "Prueba",
            "correo": "usuario@udl.edu.mx",
            "rol": role,
            "id_plantel_asignado": 1,
        }
    return client


def test_admin_dashboard_is_rendered():
    client = authenticated_client()
    bookings = [
        {"id_peticion": 1, "id_salon": 101, "estado": "APROBADA"},
        {"id_peticion": 2, "id_salon": 102, "estado": "PENDIENTE"},
    ]

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ) as plantel_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=EQUIPOS,
    ) as equipment_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ) as program_mock, patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        return_value=USUARIOS,
    ) as user_mock, patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=bookings,
    ) as booking_mock:
        response = client.get("/admin")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel administrativo" in html
    assert "Resumen general del sistema" in html
    assert 'href="/css/schedule.css"' in html
    assert 'id="dashboardPlantelCount"' in html
    assert 'id="dashboardUsuarioCount"' in html
    assert 'id="dashboardRecordCount"' in html
    assert 'id="dashboardBookingCount"' in html
    assert 'id="dashboardData"' in html
    assert 'href="/admin/planteles"' in html
    assert 'src="/js/dashboard.js"' in html
    assert 'src="/js/mock-data.js"' not in html
    assert "Usuario Prueba" in html
    assert 'action="/logout"' in html
    assert "admin-session.js" not in html
    plantel_mock.assert_called_once_with(active_only=False)
    salon_mock.assert_called_once_with(active_only=False)
    equipment_mock.assert_called_once_with(active_only=False)
    program_mock.assert_called_once_with(active_only=False)
    user_mock.assert_called_once_with("test-token")
    booking_mock.assert_called_once_with({}, "test-token")
    dashboard_match = re.search(
        r'<script id="dashboardData" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    dashboard_data = json.loads(dashboard_match.group(1))
    assert dashboard_data["collections"]["planteles"] == {
        "active": 2,
        "inactive": 1,
        "total": 3,
    }
    assert dashboard_data["totals"] == {
        "active": 6,
        "inactive": 4,
        "records": 10,
        "unassigned_equipment": 0,
    }
    assert dashboard_data["booking"] == {
        "approved": 1,
        "pending": 1,
        "total": 2,
    }
    assert dashboard_data["services"] == {
        "booking": True,
        "catalog": True,
        "iam": True,
    }
    assert dashboard_data["scope"] == "global"


def test_admin_dashboard_redirects_without_iam_session():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_public_role_cannot_open_admin_dashboard():
    client = authenticated_client(role="DOCENTE")

    response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/horarios")


def test_admin_dashboard_accepts_trailing_slash():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=[],
    ):
        response = client.get("/admin/")

    assert response.status_code == 200


def test_admin_plantel_dashboard_filters_all_scoped_metrics():
    client = authenticated_client(role="ADMIN_PLANTEL")
    foreign_equipment = {
        **EQUIPOS[0],
        "id_equipo": 202,
        "numero": "PC-FOREIGN",
        "id_salon": 102,
    }
    unassigned_equipment = {
        **EQUIPOS[0],
        "id_equipo": 203,
        "numero": "PC-UNASSIGNED",
        "id_salon": None,
    }
    users = [
        {**USUARIOS[0], "rol": "ADMIN_PLANTEL", "id_plantel_asignado": 1},
        {**USUARIOS[1], "id_plantel_asignado": 2},
    ]
    bookings = [
        {"id_peticion": 1, "id_salon": 101, "estado": "APROBADA"},
        {"id_peticion": 2, "id_salon": 102, "estado": "PENDIENTE"},
    ]

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[EQUIPOS[0], foreign_equipment, unassigned_equipment],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        return_value=users,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=bookings,
    ):
        response = client.get("/admin")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    dashboard_match = re.search(
        r'<script id="dashboardData" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    dashboard_data = json.loads(dashboard_match.group(1))
    assert dashboard_data["collections"]["planteles"]["total"] == 1
    assert dashboard_data["collections"]["salones"]["total"] == 1
    assert dashboard_data["collections"]["equipos"]["total"] == 1
    assert dashboard_data["collections"]["programas"]["total"] == 2
    assert dashboard_data["collections"]["usuarios"]["total"] == 1
    assert dashboard_data["totals"]["unassigned_equipment"] == 0
    assert dashboard_data["booking"]["total"] == 1
    assert dashboard_data["scope"] == "plantel"


def test_dashboard_keeps_partial_data_when_services_fail():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=EQUIPOS,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        side_effect=CatalogUnavailableError("Programas no disponibles."),
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        side_effect=IAMUnavailableError("IAM no disponible."),
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        side_effect=BookingUnavailableError("Booking no disponible."),
    ):
        response = client.get("/admin")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "El resumen contiene información parcial" in html
    assert "Programas no disponibles" in html
    assert "IAM no disponible" in html
    assert "Booking no disponible" in html
    dashboard_match = re.search(
        r'<script id="dashboardData" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    dashboard_data = json.loads(dashboard_match.group(1))
    assert dashboard_data["collections"]["planteles"]["total"] == 3
    assert dashboard_data["collections"]["programas"]["total"] == 0
    assert dashboard_data["services"] == {
        "booking": False,
        "catalog": False,
        "iam": False,
    }


def test_expired_iam_token_clears_session_from_dashboard():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        side_effect=IAMAuthorizationError("Token expirado", 401),
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
    ) as booking_mock:
        response = client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    booking_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_legacy_admin_url_redirects_to_new_route():
    client = authenticated_client()

    response = client.get("/templates/admin.html")

    assert response.status_code == 302
    assert response.headers["Location"].rstrip("/").endswith("/admin")


def test_planteles_catalog_is_rendered():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ) as list_mock:
        response = client.get("/admin/planteles")

    assert response.status_code == 200
    list_mock.assert_called_once_with(active_only=False)
    html = response.get_data(as_text=True)
    assert "Gestión de planteles" in html
    assert "Plantel Le\\u00f3n" in html
    assert "Plantel Centro" in html
    assert "Plantel Norte" in html
    assert 'aria-current="page"' in html
    assert 'id="plantelSearch"' in html
    assert 'id="plantelData"' in html
    assert 'id="plantelActionData"' in html
    assert "/admin/planteles/0/editar" in html
    assert "/admin/planteles/0/desactivar" in html
    assert 'src="/js/planteles.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_planteles_catalog_failure_is_rendered_without_breaking_view():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ):
        response = client.get("/admin/planteles")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No fue posible consultar los planteles" in html
    assert "Catalog temporalmente no disponible" in html


def test_legacy_planteles_url_redirects_to_new_route():
    client = authenticated_client()

    response = client.get("/templates/planteles.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")


def test_new_plantel_form_posts_to_catalog_adapter():
    client = authenticated_client()

    response = client.get("/admin/planteles/nuevo")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Registrar plantel" in html
    assert "Nombre del plantel" in html
    assert "Dirección" in html
    assert "Catalog conectado" in html
    assert 'id="plantelForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/planteles/nuevo"' in html
    assert 'src="/js/plantel-form.js"' in html
    assert 'src="/js/mock-data.js"' not in html
    assert 'href="/admin/planteles"' in html


def test_new_plantel_is_created_with_iam_token():
    client = authenticated_client()
    created = {
        "id": 9,
        "nombre": "Plantel Sur",
        "direccion": "Zona Sur",
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_plantel",
        return_value=created,
    ) as create_mock:
        response = client.post(
            "/admin/planteles/nuevo",
            data={"nombre": " Plantel Sur ", "direccion": " Zona Sur "},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")
    create_mock.assert_called_once_with("Plantel Sur", "Zona Sur", "test-token")


def test_new_plantel_requires_name_before_calling_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_plantel",
    ) as create_mock:
        response = client.post(
            "/admin/planteles/nuevo",
            data={"nombre": " ", "direccion": "Zona Sur"},
        )

    assert response.status_code == 200
    assert "El nombre del plantel es obligatorio" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_expired_catalog_token_clears_frontend_session():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_plantel",
        side_effect=CatalogAuthorizationError("Token expirado", 401),
    ):
        response = client.post(
            "/admin/planteles/nuevo",
            data={"nombre": "Plantel Sur", "direccion": "Zona Sur"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_catalog_permission_error_preserves_plantel_form_values():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_plantel",
        side_effect=CatalogAuthorizationError("Solo administradores globales.", 403),
    ):
        response = client.post(
            "/admin/planteles/nuevo",
            data={"nombre": "Plantel Sur", "direccion": "Zona Sur"},
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Solo administradores globales" in html
    assert 'value="Plantel Sur"' in html


def test_edit_plantel_form_loads_catalog_record():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
        return_value=PLANTELES[0],
    ) as get_mock:
        response = client.get("/admin/planteles/1/editar")

    assert response.status_code == 200
    get_mock.assert_called_once_with(1)
    html = response.get_data(as_text=True)
    assert "Editar plantel" in html
    assert 'action="/admin/planteles/1/editar"' in html
    assert 'value="Plantel León"' in html
    assert 'value="León, Guanajuato"' in html
    assert "Guardar cambios" in html


def test_edit_plantel_updates_catalog_with_iam_token():
    client = authenticated_client()
    updated = {
        "id": 1,
        "nombre": "Plantel León Norte",
        "direccion": "Zona Norte",
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
        return_value=PLANTELES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_plantel",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/planteles/1/editar",
            data={"nombre": " Plantel León Norte ", "direccion": " Zona Norte "},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")
    update_mock.assert_called_once_with(
        1, "Plantel León Norte", "Zona Norte", "test-token"
    )


def test_edit_plantel_requires_name_before_catalog_update():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
        return_value=PLANTELES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_plantel",
    ) as update_mock:
        response = client.post(
            "/admin/planteles/1/editar",
            data={"nombre": " ", "direccion": "Zona Norte"},
        )

    assert response.status_code == 200
    assert "El nombre del plantel es obligatorio" in response.get_data(as_text=True)
    update_mock.assert_not_called()


def test_admin_plantel_cannot_edit_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
    ) as get_mock:
        response = client.get("/admin/planteles/2/editar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")
    get_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para editar ese plantel.") in frontend_session["_flashes"]


def test_admin_plantel_can_edit_assigned_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")
    updated = {
        "id": 1,
        "nombre": "Plantel León Actualizado",
        "direccion": "Zona Norte",
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
        return_value=PLANTELES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_plantel",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/planteles/1/editar",
            data={"nombre": "Plantel León Actualizado", "direccion": "Zona Norte"},
        )

    assert response.status_code == 302
    update_mock.assert_called_once_with(
        1, "Plantel León Actualizado", "Zona Norte", "test-token"
    )


def test_deactivate_plantel_delegates_to_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_plantel",
        return_value={"message": "Plantel desactivado."},
    ) as deactivate_mock:
        response = client.post("/admin/planteles/2/desactivar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")
    deactivate_mock.assert_called_once_with(2, "test-token")
    with client.session_transaction() as frontend_session:
        assert (
            "success",
            "El plantel y sus recursos dependientes se desactivaron correctamente.",
        ) in frontend_session["_flashes"]


def test_admin_plantel_cannot_deactivate_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_plantel",
    ) as deactivate_mock:
        response = client.post("/admin/planteles/2/desactivar")

    assert response.status_code == 302
    deactivate_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para desactivar ese plantel.") in frontend_session["_flashes"]


def test_expired_catalog_token_clears_session_when_editing_plantel():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_plantel",
        return_value=PLANTELES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_plantel",
        side_effect=CatalogAuthorizationError("Token expirado", 401),
    ):
        response = client.post(
            "/admin/planteles/1/editar",
            data={"nombre": "Plantel León", "direccion": "Zona Norte"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


@pytest.mark.parametrize(
    "script_name",
    [
        "planteles.js",
        "plantel-form.js",
        "salones.js",
        "salon-form.js",
        "programas.js",
        "programa-form.js",
        "equipos.js",
        "equipo-form.js",
        "usuarios.js",
        "usuario-form.js",
        "horario-form.js",
        "horario-history.js",
        "dashboard.js",
    ],
)
def test_frontend_scripts_are_served(script_name):
    client = authenticated_client()

    response = client.get(f"/js/{script_name}")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


def test_legacy_plantel_form_url_redirects_to_new_route():
    client = authenticated_client()

    response = client.get("/templates/plantel-formulario.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles/nuevo")


@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/admin/salones", "Gestión de salones"),
        ("/admin/salones/nuevo", "Registrar salón"),
        ("/admin/equipos", "Inventario de equipos"),
        ("/admin/equipos/nuevo", "Registrar equipo"),
        ("/admin/programas", "Catálogo de programas"),
        ("/admin/programas/nuevo", "Registrar programa"),
        ("/admin/usuarios", "Gestión de usuarios"),
        ("/admin/usuarios/nuevo", "Registrar usuario"),
        ("/admin/horarios", "Gestión de horarios"),
        ("/admin/horarios/nuevo", "Registrar reserva"),
        ("/admin/horarios/historial", "Historial de reservas"),
    ],
)
def test_remaining_admin_views_are_rendered(path, expected_text):
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
        return_value=[],
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=[],
    ):
        response = client.get(path)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert expected_text in html
    assert 'href="/css/schedule.css"' in html


@pytest.mark.parametrize(
    ("legacy_page", "new_path"),
    [
        ("salones.html", "/admin/salones"),
        ("salon-formulario.html", "/admin/salones/nuevo"),
        ("equipos.html", "/admin/equipos"),
        ("equipo-formulario.html", "/admin/equipos/nuevo"),
        ("programas.html", "/admin/programas"),
        ("programa-formulario.html", "/admin/programas/nuevo"),
        ("usuarios.html", "/admin/usuarios"),
        ("usuario-formulario.html", "/admin/usuarios/nuevo"),
        ("horarios-admin.html", "/admin/horarios"),
    ],
)
def test_remaining_legacy_urls_redirect(legacy_page, new_path):
    client = authenticated_client()

    response = client.get(f"/templates/{legacy_page}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(new_path)


def test_admin_schedule_keeps_visual_period_switcher():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        response = client.get("/admin/horarios")

    html = response.get_data(as_text=True)
    assert 'data-schedule-view="admin"' in html
    assert "Turno Matutino" in html
    assert "Turno Vespertino" in html
    assert 'src="/js/schedule-view.js"' in html


def test_admin_schedule_uses_booking_records_filters_and_real_metrics():
    client = authenticated_client()
    records = [
        {
            "id_peticion": 1,
            "id_salon": 101,
            "fecha_reserva": "2026-08-17",
            "hora_inicio": "08:00:00",
            "hora_fin": "08:50:00",
            "estado": "APROBADA",
            "materia_nombre": "Redes",
            "nombre_tipo_evento": "Clase Curricular",
        },
        {
            "id_peticion": 2,
            "id_salon": 102,
            "fecha_reserva": "2026-08-18",
            "hora_inicio": "16:00:00",
            "hora_fin": "16:50:00",
            "estado": "APROBADA",
            "materia_nombre": "Bases de Datos",
            "nombre_tipo_evento": "Clase Curricular",
        },
    ]

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
        return_value=records,
    ) as list_mock:
        response = client.get(
            "/admin/horarios?id_salon=101&fecha_reserva=2026-08-17"
        )

    assert response.status_code == 200
    list_mock.assert_called_once_with(
        {"id_salon": "101", "fecha_reserva": "2026-08-17"}
    )
    html = response.get_data(as_text=True)
    assert "Booking conectado" in html
    assert "Redes" in html
    assert "Bases de Datos" in html
    assert "Docente de muestra" not in html
    assert "Conflictos detectados" not in html
    assert 'data-schedule-body' in html
    assert 'id="bookingScheduleData"' in html


def test_admin_schedule_renders_controlled_booking_failure():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
        side_effect=BookingUnavailableError("Booking temporalmente no disponible."),
    ):
        response = client.get("/admin/horarios")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="adminBookingScheduleError"' in html
    assert "Booking temporalmente no disponible" in html
    assert 'data-schedule-body' in html
    assert 'data-schedule-filters' in html


def test_admin_plantel_schedule_forces_assigned_plantel_filter():
    client = authenticated_client(role="ADMIN_PLANTEL")
    records = [
        {
            "id_salon": 101,
            "fecha_reserva": "2026-08-17",
            "hora_inicio": "08:00:00",
            "hora_fin": "08:50:00",
            "materia_nombre": "Reserva permitida",
        },
        {
            "id_salon": 102,
            "fecha_reserva": "2026-08-17",
            "hora_inicio": "09:00:00",
            "hora_fin": "09:50:00",
            "materia_nombre": "Reserva fuera de alcance",
        },
    ]

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
        return_value=records,
    ) as list_mock:
        response = client.get("/admin/horarios?id_plantel=999&id_salon=101")

    assert response.status_code == 200
    salon_list_mock.assert_called_once_with(active_only=False)
    list_mock.assert_called_once_with({"id_plantel": 1, "id_salon": "101"})
    html = response.get_data(as_text=True)
    assert "Reserva permitida" in html
    assert "Reserva fuera de alcance" not in html


def test_admin_plantel_schedule_fails_closed_when_catalog_is_unavailable():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_schedule",
    ) as list_mock:
        response = client.get("/admin/horarios")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="adminBookingScheduleError"' in html
    assert "No se pudo validar el alcance del plantel" in html
    assert "Catalog temporalmente no disponible" in html
    list_mock.assert_not_called()


def test_schedule_history_uses_authenticated_booking_filters_and_catalog_names():
    client = authenticated_client()
    records = [
        {
            "id_peticion": 10,
            "id_salon": 101,
            "id_usuario": 2,
            "fecha_reserva": "2026-08-24",
            "hora_inicio": "08:00:00",
            "hora_fin": "08:50:00",
            "estado": "RECHAZADA",
            "materia_nombre": "Redes",
            "nombre_tipo_evento": "Clase Curricular",
            "prioridad_calculada": 90,
            "motivo_rechazo": "Conflicto FIFO",
        }
    ]

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=records,
    ) as history_mock:
        response = client.get(
            "/admin/horarios/historial"
            "?estado=RECHAZADA&id_salon=101&fecha_reserva=2026-08-24&id_usuario=2"
        )

    assert response.status_code == 200
    plantel_list_mock.assert_called_once_with(active_only=False)
    salon_list_mock.assert_called_once_with(active_only=False)
    history_mock.assert_called_once_with(
        {
            "estado": "RECHAZADA",
            "id_salon": 101,
            "id_usuario": 2,
            "fecha_reserva": "2026-08-24",
        },
        "test-token",
    )
    html = response.get_data(as_text=True)
    assert 'id="bookingHistoryData"' in html
    assert 'id="historyConfigData"' in html
    assert "/admin/horarios/0/cancelar" in html
    assert "Redes" in html
    assert "Laboratorio 01" in html
    assert 'src="/js/horario-history.js"' in html
    assert "las cancelaciones se procesan mediante Booking" in html


def test_admin_plantel_history_excludes_rooms_outside_assigned_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")
    records = [
        {
            "id_peticion": 10,
            "id_salon": 101,
            "estado": "APROBADA",
            "materia_nombre": "Reserva permitida",
        },
        {
            "id_peticion": 11,
            "id_salon": 102,
            "estado": "APROBADA",
            "materia_nombre": "Reserva fuera de alcance",
        },
    ]

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        return_value=records,
    ) as history_mock:
        response = client.get("/admin/horarios/historial")

    assert response.status_code == 200
    history_mock.assert_called_once_with({}, "test-token")
    html = response.get_data(as_text=True)
    assert "Reserva permitida" in html
    assert "Reserva fuera de alcance" not in html
    assert "Laboratorio 01" in html
    assert "Aula 02" not in html
    assert "Plantel Centro" not in html


def test_admin_plantel_history_fails_closed_without_catalog_scope():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
    ) as history_mock:
        response = client.get("/admin/horarios/historial")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Catalog temporalmente no disponible" in html
    assert "No se pudo validar el alcance del plantel" in html
    assert "bookingHistoryData" in html
    history_mock.assert_not_called()


def test_schedule_history_renders_controlled_booking_failure():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        side_effect=BookingUnavailableError("Historial temporalmente no disponible."),
    ):
        response = client.get("/admin/horarios/historial")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Historial temporalmente no disponible" in html
    assert 'type="application/json">[]</script>' in html


def test_expired_booking_token_clears_session_from_history():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
        side_effect=BookingAuthorizationError("Token expirado", 401),
    ):
        response = client.get("/admin/horarios/historial")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_schedule_history_rejects_invalid_filter_before_booking_call():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.list_history",
    ) as history_mock:
        response = client.get("/admin/horarios/historial?estado=DESCONOCIDO")

    assert response.status_code == 200
    assert "El estado seleccionado no es válido" in response.get_data(as_text=True)
    history_mock.assert_not_called()


def test_schedule_cancellation_delegates_to_booking_and_preserves_filters():
    client = authenticated_client()
    service_result = {
        "message": "Reserva #10 cancelada exitosamente y espacio liberado.",
        "peticion": {"id_peticion": 10, "estado": "CANCELADA"},
    }

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.cancel_booking",
        return_value=service_result,
    ) as cancel_mock:
        response = client.post(
            "/admin/horarios/10/cancelar?estado=APROBADA&id_salon=101"
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/admin/horarios/historial?estado=APROBADA&id_salon=101"
    )
    cancel_mock.assert_called_once_with(10, "test-token")
    with client.session_transaction() as frontend_session:
        assert (
            "success",
            "Reserva #10 cancelada exitosamente y espacio liberado.",
        ) in frontend_session["_flashes"]


def test_schedule_cancellation_keeps_session_when_booking_denies_scope():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.cancel_booking",
        side_effect=BookingAuthorizationError("Reserva fuera del plantel asignado.", 403),
    ):
        response = client.post("/admin/horarios/10/cancelar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/horarios/historial")
    with client.session_transaction() as frontend_session:
        assert frontend_session["iam_token"] == "test-token"
        assert (
            "error",
            "Reserva fuera del plantel asignado.",
        ) in frontend_session["_flashes"]


def test_expired_booking_token_clears_session_from_cancellation():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.cancel_booking",
        side_effect=BookingAuthorizationError("Token expirado", 401),
    ):
        response = client.post("/admin/horarios/10/cancelar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_schedule_cancellation_rejects_get_requests():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.BookingClient.cancel_booking",
    ) as cancel_mock:
        response = client.get("/admin/horarios/10/cancelar")

    assert response.status_code in {404, 405}
    cancel_mock.assert_not_called()


def test_new_schedule_form_uses_active_catalogs_and_booking_contract_fields():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ) as program_list_mock:
        response = client.get("/admin/horarios/nuevo")

    assert response.status_code == 200
    plantel_list_mock.assert_called_once_with(active_only=True)
    salon_list_mock.assert_called_once_with(active_only=True)
    program_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert 'id="scheduleForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/horarios/nuevo"' in html
    assert 'name="fecha_reserva"' in html
    assert 'name="id_tipo_evento"' in html
    assert 'name="numero_alumnos"' in html
    assert "07:00 – 07:50" in html
    assert "21:00 – 21:50" in html
    assert 'id="scheduleSalonData"' in html
    assert 'src="/js/horario-form.js"' in html
    assert "iam-token" not in html


def test_new_schedule_request_is_sent_to_booking_with_iam_token():
    client = authenticated_client()
    service_result = {
        "message": "Reserva aprobada y registrada exitosamente.",
        "peticion": {"id_peticion": 9, "estado": "APROBADA"},
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
        return_value=service_result,
    ) as create_mock:
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "1",
                "id_salon": "101",
                "id_programa": "1",
                "materia_nombre": " Redes ",
                "fecha_reserva": "2026-08-24",
                "bloque": "08:00|08:50",
                "id_tipo_evento": "1",
                "numero_alumnos": "20",
                "observaciones": " Laboratorio ",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/horarios")
    create_mock.assert_called_once_with(
        {
            "id_salon": 101,
            "id_programa": 1,
            "materia_nombre": "Redes",
            "fecha_reserva": "2026-08-24",
            "hora_inicio": "08:00",
            "hora_fin": "08:50",
            "id_tipo_evento": 1,
            "numero_alumnos": 20,
            "observaciones": "Laboratorio",
        },
        "test-token",
    )


def test_edit_schedule_form_loads_existing_booking():
    client = authenticated_client()
    booking = {
        "id_peticion": 9,
        "id_salon": 101,
        "id_programa": 1,
        "materia_nombre": "Redes",
        "fecha_reserva": "2026-08-24",
        "hora_inicio": "08:00:00",
        "hora_fin": "08:50:00",
        "id_tipo_evento": 1,
        "numero_alumnos": 20,
        "observaciones": "Laboratorio",
        "estado": "APROBADA",
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.get_booking",
        return_value=booking,
    ) as get_mock:
        response = client.get("/admin/horarios/9/editar")

    assert response.status_code == 200
    get_mock.assert_called_once_with(9, "test-token")
    html = response.get_data(as_text=True)
    assert "Editar reserva" in html
    assert 'action="/admin/horarios/9/editar"' in html
    assert 'value="2026-08-24"' in html
    assert 'value="08:00|08:50" selected' in html
    assert 'value="Redes"' in html


def test_edit_schedule_request_is_sent_to_booking_with_iam_token():
    client = authenticated_client()
    service_result = {
        "message": "Reserva #9 actualizada exitosamente.",
        "peticion": {"id_peticion": 9, "estado": "APROBADA"},
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.update_booking",
        return_value=service_result,
    ) as update_mock:
        response = client.post(
            "/admin/horarios/9/editar",
            data={
                "id_plantel": "1",
                "id_salon": "101",
                "id_programa": "1",
                "materia_nombre": " Redes actualizadas ",
                "fecha_reserva": "2026-08-25",
                "bloque": "09:00|09:50",
                "id_tipo_evento": "1",
                "numero_alumnos": "20",
                "observaciones": " Reprogramada ",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/horarios/historial")
    update_mock.assert_called_once_with(
        9,
        {
            "id_salon": 101,
            "id_programa": 1,
            "materia_nombre": "Redes actualizadas",
            "fecha_reserva": "2026-08-25",
            "hora_inicio": "09:00",
            "hora_fin": "09:50",
            "id_tipo_evento": 1,
            "numero_alumnos": 20,
            "observaciones": "Reprogramada",
        },
        "test-token",
    )


def test_new_schedule_rejects_unknown_salon_before_calling_booking():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
    ) as create_mock:
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "1",
                "id_salon": "999",
                "fecha_reserva": "2026-08-24",
                "bloque": "08:00|08:50",
                "id_tipo_evento": "1",
            },
        )

    assert response.status_code == 200
    assert "Selecciona un salón activo" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_new_schedule_rejects_capacity_excess_before_calling_booking():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
    ) as create_mock:
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "1",
                "id_salon": "101",
                "fecha_reserva": "2026-08-24",
                "bloque": "08:00|08:50",
                "id_tipo_evento": "1",
                "numero_alumnos": "31",
            },
        )

    assert response.status_code == 200
    assert "excede la capacidad del salón (30)" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_admin_plantel_cannot_book_room_from_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
    ) as create_mock:
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "2",
                "id_salon": "102",
                "fecha_reserva": "2026-08-24",
                "bloque": "16:00|16:50",
                "id_tipo_evento": "2",
            },
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Selecciona un plantel activo permitido" in html
    assert "Plantel Centro" not in html
    assert "Aula 02" not in html
    create_mock.assert_not_called()


def test_booking_conflict_preserves_schedule_form_values():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
        side_effect=BookingValidationError("Conflicto de reserva por prioridad."),
    ):
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "1",
                "id_salon": "101",
                "materia_nombre": "Redes",
                "fecha_reserva": "2026-08-24",
                "bloque": "08:00|08:50",
                "id_tipo_evento": "1",
            },
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Conflicto de reserva por prioridad" in html
    assert 'value="Redes"' in html
    assert 'value="2026-08-24"' in html
    assert 'value="08:00|08:50" selected' in html


def test_expired_booking_token_clears_frontend_session():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ), patch(
        "schedule.app.routes.admin_routes.BookingClient.create_booking",
        side_effect=BookingAuthorizationError("Token expirado", 401),
    ):
        response = client.post(
            "/admin/horarios/nuevo",
            data={
                "id_plantel": "1",
                "id_salon": "101",
                "fecha_reserva": "2026-08-24",
                "bloque": "08:00|08:50",
                "id_tipo_evento": "1",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_salones_catalog_uses_real_service_payload():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ) as plantel_list_mock:
        response = client.get("/admin/salones")

    assert response.status_code == 200
    salon_list_mock.assert_called_once_with(active_only=False)
    plantel_list_mock.assert_called_once_with(active_only=False)
    html = response.get_data(as_text=True)
    assert 'id="salonSearch"' in html
    assert 'id="salonPlantelFilter"' in html
    assert 'id="salonStatusFilter"' in html
    assert 'id="salonData"' in html
    assert 'id="salonActionData"' in html
    assert "/admin/salones/0/editar" in html
    assert "/admin/salones/0/desactivar" in html
    assert "Laboratorio 01" in html
    assert 'src="/js/salones.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_salones_catalog_failure_is_rendered_without_breaking_view():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ):
        response = client.get("/admin/salones")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No fue posible consultar los salones" in html
    assert "Catalog temporalmente no disponible" in html


def test_salon_form_uses_active_planteles_from_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock:
        response = client.get("/admin/salones/nuevo")

    assert response.status_code == 200
    plantel_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert 'id="salonForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/salones/nuevo"' in html
    assert 'id="salonPlantel"' in html
    assert "Plantel Centro" in html
    assert 'type="submit"' in html
    assert 'src="/js/salon-form.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_new_salon_is_created_with_iam_token_and_catalog_fields():
    client = authenticated_client()
    created = {
        "id_salon": 109,
        "numero": "Laboratorio 09",
        "descripcion": "Cómputo",
        "capacidad": 32,
        "id_plantel": 1,
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_salon",
        return_value=created,
    ) as create_mock:
        response = client.post(
            "/admin/salones/nuevo",
            data={
                "numero": " Laboratorio 09 ",
                "descripcion": " Cómputo ",
                "capacidad": "32",
                "id_plantel": "1",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/salones")
    create_mock.assert_called_once_with(
        "Laboratorio 09", "Cómputo", 32, 1, "test-token"
    )


def test_new_salon_validates_capacity_before_calling_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_salon",
    ) as create_mock:
        response = client.post(
            "/admin/salones/nuevo",
            data={
                "numero": "Laboratorio 09",
                "descripcion": "Cómputo",
                "capacidad": "0",
                "id_plantel": "1",
            },
        )

    assert response.status_code == 200
    assert "debe ser mayor a cero" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_admin_plantel_can_only_select_assigned_plantel_for_new_salon():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ):
        response = client.get("/admin/salones/nuevo")

    html = response.get_data(as_text=True)
    assert "Plantel Le\\u00f3n" not in html
    assert "Plantel León" in html
    assert "Plantel Centro" not in html


def test_edit_salon_form_loads_catalog_record_and_active_planteles():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ) as get_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock:
        response = client.get("/admin/salones/101/editar")

    assert response.status_code == 200
    get_mock.assert_called_once_with(101)
    plantel_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert "Editar salón" in html
    assert 'action="/admin/salones/101/editar"' in html
    assert 'value="Laboratorio 01"' in html
    assert 'value="30"' in html
    assert "Guardar cambios" in html


def test_edit_salon_updates_catalog_with_valid_relationship():
    client = authenticated_client()
    updated = {
        "id_salon": 101,
        "numero": "Laboratorio 01A",
        "descripcion": "Cómputo actualizado",
        "capacidad": 35,
        "id_plantel": 2,
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_salon",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/salones/101/editar",
            data={
                "numero": " Laboratorio 01A ",
                "descripcion": " Cómputo actualizado ",
                "capacidad": "35",
                "id_plantel": "2",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/salones")
    update_mock.assert_called_once_with(
        101, "Laboratorio 01A", "Cómputo actualizado", 35, 2, "test-token"
    )


def test_edit_salon_validates_capacity_before_catalog_update():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_salon",
    ) as update_mock:
        response = client.post(
            "/admin/salones/101/editar",
            data={
                "numero": "Laboratorio 01",
                "descripcion": "Cómputo",
                "capacidad": "0",
                "id_plantel": "1",
            },
        )

    assert response.status_code == 200
    assert "debe ser mayor a cero" in response.get_data(as_text=True)
    update_mock.assert_not_called()


def test_admin_plantel_cannot_edit_salon_from_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
    ) as plantel_list_mock:
        response = client.get("/admin/salones/102/editar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/salones")
    plantel_list_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para editar ese salón.") in frontend_session["_flashes"]


def test_admin_plantel_can_edit_salon_from_assigned_plantel_only():
    client = authenticated_client(role="ADMIN_PLANTEL")
    updated = {**SALONES[0], "numero": "Laboratorio 01A"}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_salon",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/salones/101/editar",
            data={
                "numero": "Laboratorio 01A",
                "descripcion": "Cómputo",
                "capacidad": "30",
                "id_plantel": "1",
            },
        )

    assert response.status_code == 302
    update_mock.assert_called_once_with(
        101, "Laboratorio 01A", "Cómputo", 30, 1, "test-token"
    )


def test_deactivate_salon_delegates_to_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_salon",
        return_value={"message": "Salón desactivado."},
    ) as deactivate_mock:
        response = client.post("/admin/salones/101/desactivar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/salones")
    deactivate_mock.assert_called_once_with(101, "test-token")
    with client.session_transaction() as frontend_session:
        assert (
            "success",
            "El salón y sus equipos asociados se desactivaron correctamente.",
        ) in frontend_session["_flashes"]


def test_admin_plantel_cannot_deactivate_salon_from_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_salon",
    ) as deactivate_mock:
        response = client.post("/admin/salones/102/desactivar")

    assert response.status_code == 302
    deactivate_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para desactivar ese salón.") in frontend_session["_flashes"]


def test_expired_catalog_token_clears_session_when_editing_salon():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_salon",
        return_value=SALONES[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_salon",
        side_effect=CatalogAuthorizationError("Token expirado", 401),
    ):
        response = client.post(
            "/admin/salones/101/editar",
            data={
                "numero": "Laboratorio 01",
                "descripcion": "Cómputo",
                "capacidad": "30",
                "id_plantel": "1",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_programas_catalog_uses_real_service_payload_and_equipment_relations():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        return_value=PROGRAMAS,
    ) as program_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=EQUIPOS,
    ) as equipment_list_mock:
        response = client.get("/admin/programas")

    assert response.status_code == 200
    program_list_mock.assert_called_once_with(active_only=False)
    equipment_list_mock.assert_called_once_with(active_only=False)
    html = response.get_data(as_text=True)
    assert 'id="programSearch"' in html
    assert 'id="programStatusFilter"' in html
    assert 'id="programCardGrid"' in html
    assert 'id="programData"' in html
    assert 'id="programEquipmentData"' in html
    assert 'id="programActionData"' in html
    assert "/admin/programas/0/equipos" in html
    assert "/admin/programas/0/editar" in html
    assert "/admin/programas/0/desactivar" in html
    assert "Python" in html
    assert 'src="/js/programas.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_programas_catalog_failure_is_rendered_without_breaking_view():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_programas",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ):
        response = client.get("/admin/programas")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No fue posible consultar los programas" in html
    assert "Catalog temporalmente no disponible" in html


def test_program_form_posts_to_catalog_adapter():
    client = authenticated_client()

    response = client.get("/admin/programas/nuevo")

    html = response.get_data(as_text=True)
    assert 'id="programForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/programas/nuevo"' in html
    assert 'id="programName"' in html
    assert 'id="programDescription"' in html
    assert 'id="programPreviewName"' in html
    assert 'type="submit"' in html
    assert 'src="/js/programa-form.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_new_program_is_created_with_iam_token():
    client = authenticated_client()
    created = {
        "id_programa": 9,
        "nombre": "Herramienta académica",
        "descripcion": "Prácticas",
        "activo": True,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_programa",
        return_value=created,
    ) as create_mock:
        response = client.post(
            "/admin/programas/nuevo",
            data={
                "nombre": " Herramienta académica ",
                "descripcion": " Prácticas ",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/programas")
    create_mock.assert_called_once_with(
        "Herramienta académica", "Prácticas", "test-token"
    )


def test_new_program_requires_name_before_calling_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_programa",
    ) as create_mock:
        response = client.post(
            "/admin/programas/nuevo",
            data={"nombre": " ", "descripcion": "Prácticas"},
        )

    assert response.status_code == 200
    assert "El nombre del programa es obligatorio" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_edit_program_form_loads_catalog_record():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ) as get_mock:
        response = client.get("/admin/programas/1/editar")

    assert response.status_code == 200
    get_mock.assert_called_once_with(1)
    html = response.get_data(as_text=True)
    assert "Editar programa" in html
    assert 'action="/admin/programas/1/editar"' in html
    assert 'value="Python"' in html
    assert "Entorno académico" in html
    assert "Guardar cambios" in html
    assert "Los equipos vinculados permanecerán sin cambios" in html


def test_edit_program_updates_catalog_with_iam_token():
    client = authenticated_client()
    updated = {
        **PROGRAMAS[0],
        "nombre": "Python 3",
        "descripcion": "Entorno actualizado",
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_programa",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/programas/1/editar",
            data={
                "nombre": " Python 3 ",
                "descripcion": " Entorno actualizado ",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/programas")
    update_mock.assert_called_once_with(
        1, "Python 3", "Entorno actualizado", "test-token"
    )


def test_edit_program_rejects_empty_name_before_catalog_update():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_programa",
    ) as update_mock:
        response = client.post(
            "/admin/programas/1/editar",
            data={"nombre": " ", "descripcion": "Entorno académico"},
        )

    assert response.status_code == 200
    assert "El nombre del programa es obligatorio" in response.get_data(as_text=True)
    update_mock.assert_not_called()


def test_admin_plantel_can_edit_global_program_catalog():
    client = authenticated_client(role="ADMIN_PLANTEL")
    updated = {**PROGRAMAS[0], "nombre": "Python Institucional"}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_programa",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/programas/1/editar",
            data={"nombre": "Python Institucional", "descripcion": "Entorno"},
        )

    assert response.status_code == 302
    update_mock.assert_called_once_with(
        1, "Python Institucional", "Entorno", "test-token"
    )


def test_deactivate_program_delegates_to_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_programa",
        return_value={"message": "Programa desactivado."},
    ) as deactivate_mock:
        response = client.post("/admin/programas/1/desactivar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/programas")
    deactivate_mock.assert_called_once_with(1, "test-token")
    with client.session_transaction() as frontend_session:
        assert ("success", "El programa se desactivó correctamente.") in frontend_session["_flashes"]


def test_expired_catalog_token_clears_session_when_editing_program():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_programa",
        side_effect=CatalogAuthorizationError("Token expirado", 401),
    ):
        response = client.post(
            "/admin/programas/1/editar",
            data={"nombre": "Python 3", "descripcion": "Entorno"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_program_equipment_view_loads_active_catalog_relations():
    client = authenticated_client()
    unassigned = {
        **EQUIPOS[0],
        "id_equipo": 202,
        "numero": "PC-002",
        "id_salon": None,
        "programas": [],
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ) as get_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[EQUIPOS[0], unassigned],
    ) as equipment_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock:
        response = client.get("/admin/programas/1/equipos")

    assert response.status_code == 200
    get_mock.assert_called_once_with(1)
    equipment_list_mock.assert_called_once_with(active_only=True)
    salon_list_mock.assert_called_once_with(active_only=True)
    plantel_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert "Equipos de Python" in html
    assert "PC-001" in html
    assert "PC-002" in html
    assert "Laboratorio 01" in html
    assert "Sin salón asignado" in html
    assert "/admin/programas/1/equipos/201/desvincular" in html
    assert "/admin/programas/1/equipos/202/asociar" in html
    assert 'src="/js/programa-equipos.js"' in html


def test_admin_plantel_program_equipment_view_only_shows_own_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")
    foreign_equipment = {
        **EQUIPOS[0],
        "id_equipo": 202,
        "numero": "PC-FOREIGN",
        "id_salon": 102,
        "programas": [],
    }
    unassigned = {
        **EQUIPOS[0],
        "id_equipo": 203,
        "numero": "PC-UNASSIGNED",
        "id_salon": None,
        "programas": [],
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=[EQUIPOS[0], foreign_equipment, unassigned],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ):
        response = client.get("/admin/programas/1/equipos")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "PC-001" in html
    assert "PC-FOREIGN" not in html
    assert "PC-UNASSIGNED" not in html


def test_program_can_be_assigned_to_allowed_equipment():
    client = authenticated_client()
    equipment = {**EQUIPOS[0], "programas": []}
    associated = {**equipment, "programas": [PROGRAMAS[0]]}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=equipment,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.assign_programa",
        return_value=associated,
    ) as assign_mock:
        response = client.post("/admin/programas/1/equipos/201/asociar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/programas/1/equipos")
    assign_mock.assert_called_once_with(201, 1, "test-token")
    with client.session_transaction() as frontend_session:
        assert (
            "success",
            "El equipo PC-001 se vinculó con Python correctamente.",
        ) in frontend_session["_flashes"]


def test_program_can_be_removed_from_allowed_equipment():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.remove_programa",
        return_value={"message": "Programa desvinculado."},
    ) as remove_mock:
        response = client.post("/admin/programas/1/equipos/201/desvincular")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/programas/1/equipos")
    remove_mock.assert_called_once_with(201, 1, "test-token")
    with client.session_transaction() as frontend_session:
        assert (
            "success",
            "El equipo PC-001 se desvinculó de Python correctamente.",
        ) in frontend_session["_flashes"]


def test_admin_plantel_cannot_assign_program_to_unassigned_equipment():
    client = authenticated_client(role="ADMIN_PLANTEL")
    unassigned = {**EQUIPOS[0], "id_salon": None, "programas": []}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=unassigned,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.assign_programa",
    ) as assign_mock:
        response = client.post("/admin/programas/1/equipos/201/asociar")

    assert response.status_code == 302
    assign_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert (
            "error",
            "No tienes permisos para administrar programas en ese equipo.",
        ) in frontend_session["_flashes"]


def test_expired_catalog_token_clears_session_when_assigning_program():
    client = authenticated_client()
    equipment = {**EQUIPOS[0], "programas": []}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_programa",
        return_value=PROGRAMAS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=equipment,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.assign_programa",
        side_effect=CatalogAuthorizationError("Token expirado", 401),
    ):
        response = client.post("/admin/programas/1/equipos/201/asociar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_equipos_catalog_uses_real_service_payload():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        return_value=EQUIPOS,
    ) as equipo_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ) as salon_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ) as plantel_list_mock:
        response = client.get("/admin/equipos")

    assert response.status_code == 200
    equipo_list_mock.assert_called_once_with(active_only=False)
    salon_list_mock.assert_called_once_with(active_only=False)
    plantel_list_mock.assert_called_once_with(active_only=False)
    html = response.get_data(as_text=True)
    assert 'id="equipmentSearch"' in html
    assert 'id="equipmentPlantelFilter"' in html
    assert 'id="equipmentSalonFilter"' in html
    assert 'id="equipmentStatusFilter"' in html
    assert 'id="equipmentTableBody"' in html
    assert 'id="equipmentMobileGrid"' in html
    assert 'id="equipmentData"' in html
    assert 'id="equipmentActionData"' in html
    assert "/admin/equipos/0/editar" in html
    assert "/admin/equipos/0/desactivar" in html
    assert "PC-001" in html
    assert "Editor acad\\u00e9mico" in html
    assert 'src="/js/equipos.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_equipos_catalog_failure_is_rendered_without_breaking_view():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_equipos",
        side_effect=CatalogUnavailableError("Catalog temporalmente no disponible."),
    ):
        response = client.get("/admin/equipos")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No fue posible consultar los equipos" in html
    assert "Catalog temporalmente no disponible" in html


def test_equipment_form_uses_active_locations_from_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ) as salon_list_mock:
        response = client.get("/admin/equipos/nuevo")

    assert response.status_code == 200
    plantel_list_mock.assert_called_once_with(active_only=True)
    salon_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert 'id="equipmentForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/equipos/nuevo"' in html
    assert 'id="equipmentName"' in html
    assert 'id="equipmentPlantel"' in html
    assert 'id="equipmentSalon"' in html
    assert 'id="equipmentFormSalonData"' in html
    assert "Plantel Centro" in html
    assert 'id="equipmentPreviewName"' in html
    assert 'type="submit"' in html
    assert 'src="/js/equipo-form.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_new_equipment_is_created_with_iam_token_and_catalog_fields():
    client = authenticated_client()
    created = {
        "id_equipo": 209,
        "numero": "PC-009",
        "descripcion": "Estación docente",
        "activo": True,
        "id_salon": 101,
        "programas": [],
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_equipo",
        return_value=created,
    ) as create_mock:
        response = client.post(
            "/admin/equipos/nuevo",
            data={
                "numero": " PC-009 ",
                "descripcion": " Estación docente ",
                "id_salon": "101",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/equipos")
    create_mock.assert_called_once_with(
        "PC-009", "Estación docente", 101, "test-token"
    )


def test_new_equipment_can_be_created_without_salon():
    client = authenticated_client()
    created = {
        "id_equipo": 210,
        "numero": "PC-010",
        "descripcion": None,
        "activo": True,
        "id_salon": None,
        "programas": [],
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_equipo",
        return_value=created,
    ) as create_mock:
        response = client.post(
            "/admin/equipos/nuevo",
            data={"numero": "PC-010", "descripcion": "", "id_salon": ""},
        )

    assert response.status_code == 302
    create_mock.assert_called_once_with("PC-010", "", None, "test-token")


def test_new_equipment_rejects_unknown_salon_before_calling_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_equipo",
    ) as create_mock:
        response = client.post(
            "/admin/equipos/nuevo",
            data={"numero": "PC-011", "descripcion": "", "id_salon": "999"},
        )

    assert response.status_code == 200
    assert "Selecciona un salón activo" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_admin_plantel_only_receives_assigned_locations_for_equipment_form():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ):
        response = client.get("/admin/equipos/nuevo")

    html = response.get_data(as_text=True)
    assert "Plantel León" in html
    assert "Plantel Centro" not in html
    assert "Laboratorio 01" in html
    assert "Aula 02" not in html


def test_admin_plantel_must_assign_new_equipment_to_own_salon():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.create_equipo",
    ) as create_mock:
        response = client.post(
            "/admin/equipos/nuevo",
            data={"numero": "PC-012", "descripcion": "", "id_salon": ""},
        )

    assert response.status_code == 200
    assert "conservar el alcance del equipo" in response.get_data(as_text=True)
    create_mock.assert_not_called()


def test_edit_equipment_form_loads_catalog_record_and_active_locations():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ) as get_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ) as salon_list_mock:
        response = client.get("/admin/equipos/201/editar")

    assert response.status_code == 200
    get_mock.assert_called_once_with(201)
    plantel_list_mock.assert_called_once_with(active_only=True)
    salon_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert "Editar equipo" in html
    assert 'action="/admin/equipos/201/editar"' in html
    assert 'value="PC-001"' in html
    assert 'data-selected-salon="101"' in html
    assert "Guardar cambios" in html
    assert "Las asociaciones actuales permanecen intactas" in html


def test_edit_equipment_updates_catalog_without_changing_programs():
    client = authenticated_client()
    updated = {
        **EQUIPOS[0],
        "numero": "PC-001A",
        "descripcion": "Estación actualizada",
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_equipo",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/equipos/201/editar",
            data={
                "numero": " PC-001A ",
                "descripcion": " Estación actualizada ",
                "id_salon": "101",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/equipos")
    update_mock.assert_called_once_with(
        201, "PC-001A", "Estación actualizada", 101, "test-token"
    )


def test_coordinator_can_remove_equipment_salon_assignment():
    client = authenticated_client()
    updated = {**EQUIPOS[0], "id_salon": None}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_equipo",
        return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/equipos/201/editar",
            data={"numero": "PC-001", "descripcion": "", "id_salon": ""},
        )

    assert response.status_code == 302
    update_mock.assert_called_once_with(201, "PC-001", "", None, "test-token")


def test_admin_plantel_cannot_edit_equipment_from_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")
    foreign_equipment = {**EQUIPOS[0], "id_equipo": 202, "id_salon": 102}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=foreign_equipment,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_equipo",
    ) as update_mock:
        response = client.post(
            "/admin/equipos/202/editar",
            data={"numero": "PC-002", "descripcion": "", "id_salon": "102"},
        )

    assert response.status_code == 302
    update_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para editar ese equipo.") in frontend_session["_flashes"]


def test_admin_plantel_cannot_leave_equipment_without_salon():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.update_equipo",
    ) as update_mock:
        response = client.post(
            "/admin/equipos/201/editar",
            data={"numero": "PC-001", "descripcion": "", "id_salon": ""},
        )

    assert response.status_code == 200
    assert "conservar el alcance del equipo" in response.get_data(as_text=True)
    update_mock.assert_not_called()


def test_deactivate_equipment_delegates_to_catalog():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=EQUIPOS[0],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES[:1],
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_equipo",
        return_value={"message": "Equipo desactivado."},
    ) as deactivate_mock:
        response = client.post("/admin/equipos/201/desactivar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/equipos")
    deactivate_mock.assert_called_once_with(201, "test-token")
    with client.session_transaction() as frontend_session:
        assert ("success", "El equipo se desactivó correctamente.") in frontend_session["_flashes"]


def test_admin_plantel_cannot_deactivate_equipment_from_another_plantel():
    client = authenticated_client(role="ADMIN_PLANTEL")
    foreign_equipment = {**EQUIPOS[0], "id_equipo": 202, "id_salon": 102}

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.get_equipo",
        return_value=foreign_equipment,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_salones",
        return_value=SALONES,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.deactivate_equipo",
    ) as deactivate_mock:
        response = client.post("/admin/equipos/202/desactivar")

    assert response.status_code == 302
    deactivate_mock.assert_not_called()
    with client.session_transaction() as frontend_session:
        assert ("error", "No tienes permisos para desactivar ese equipo.") in frontend_session["_flashes"]


def test_usuarios_view_uses_iam_and_catalog_payloads():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        return_value=USUARIOS,
    ) as user_list_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ) as plantel_list_mock:
        response = client.get("/admin/usuarios")

    assert response.status_code == 200
    user_list_mock.assert_called_once_with("test-token")
    plantel_list_mock.assert_called_once_with(active_only=False)
    html = response.get_data(as_text=True)
    assert 'id="userSearch"' in html
    assert 'id="userRoleFilter"' in html
    assert 'id="userPlantelFilter"' in html
    assert 'id="userStatusFilter"' in html
    assert 'id="userTableBody"' in html
    assert 'id="userMobileGrid"' in html
    assert 'id="userData"' in html
    assert 'id="userPlantelData"' in html
    assert "ana@udl.edu.mx" in html
    assert 'src="/js/usuarios.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_usuarios_iam_failure_is_rendered_without_breaking_view():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        side_effect=IAMUnavailableError("IAM temporalmente no disponible."),
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES,
    ):
        response = client.get("/admin/usuarios")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No fue posible completar la consulta" in html
    assert "IAM temporalmente no disponible" in html


def test_expired_iam_token_clears_session_when_listing_users():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users",
        side_effect=IAMAuthorizationError("Token expirado", 401),
    ):
        response = client.get("/admin/usuarios")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session


def test_user_form_uses_real_planteles_and_native_submission():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ) as plantel_list_mock:
        response = client.get("/admin/usuarios/nuevo")

    assert response.status_code == 200
    plantel_list_mock.assert_called_once_with(active_only=True)
    html = response.get_data(as_text=True)
    assert 'id="userForm"' in html
    assert 'method="post"' in html
    assert 'action="/admin/usuarios/nuevo"' in html
    assert 'id="userEmail"' in html
    assert 'id="userPassword" name="password"' in html
    assert 'name="password_confirmation"' in html
    assert 'id="userRole"' in html
    assert 'id="userPlantel"' in html
    assert 'name="id_plantel_asignado"' in html
    assert "bcrypt con costo 12 en IAM" in html
    assert "Plantel Centro" in html
    assert 'type="submit"' in html
    assert 'src="/js/usuario-form.js"' in html
    assert 'src="/js/mock-data.js"' not in html


def test_new_user_is_registered_with_iam_token_and_expected_contract():
    client = authenticated_client()
    created = {
        "id_usuario": 9,
        "nombre": "María",
        "apellido": "Docente",
        "correo": "maria@udl.edu.mx",
        "rol": "DOCENTE",
        "activo": True,
        "id_plantel_asignado": 1,
    }

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.register_user",
        return_value=created,
    ) as register_mock:
        response = client.post(
            "/admin/usuarios/nuevo",
            data={
                "nombre": " María ",
                "apellido": " Docente ",
                "correo": " MARIA@UDL.EDU.MX ",
                "password": "Segura-Prueba123",
                "password_confirmation": "Segura-Prueba123",
                "rol": "DOCENTE",
                "id_plantel_asignado": "1",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/usuarios")
    register_mock.assert_called_once_with(
        {
            "nombre": "María",
            "apellido": "Docente",
            "correo": "maria@udl.edu.mx",
            "password": "Segura-Prueba123",
            "rol": "DOCENTE",
            "id_plantel_asignado": 1,
        },
        "test-token",
    )


def test_new_user_rejects_password_mismatch_before_calling_iam():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.register_user",
    ) as register_mock:
        response = client.post(
            "/admin/usuarios/nuevo",
            data={
                "nombre": "María",
                "apellido": "Docente",
                "correo": "maria@udl.edu.mx",
                "password": "Segura-Prueba123",
                "password_confirmation": "diferente",
                "rol": "DOCENTE",
                "id_plantel_asignado": "1",
            },
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "no coincide" in html
    assert 'value="Segura-Prueba123"' not in html
    register_mock.assert_not_called()


def test_duplicate_user_error_preserves_only_non_sensitive_values():
    client = authenticated_client()

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.register_user",
        side_effect=IAMValidationError("El correo ya está registrado"),
    ):
        response = client.post(
            "/admin/usuarios/nuevo",
            data={
                "nombre": "María",
                "apellido": "Docente",
                "correo": "maria@udl.edu.mx",
                "password": "Segura-Prueba123",
                "password_confirmation": "Segura-Prueba123",
                "rol": "DOCENTE",
                "id_plantel_asignado": "1",
            },
        )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "El correo ya está registrado" in html
    assert 'value="maria@udl.edu.mx"' in html
    assert 'value="Segura-Prueba123"' not in html


def test_admin_plantel_only_receives_assigned_plantel_for_user_form():
    client = authenticated_client(role="ADMIN_PLANTEL")

    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles",
        return_value=PLANTELES[:2],
    ):
        response = client.get("/admin/usuarios/nuevo")

    html = response.get_data(as_text=True)
    assert "Plantel León" in html
    assert "Plantel Centro" not in html


def test_admin_plantel_user_list_is_limited_again_in_visual_layer():
    client = authenticated_client(role="ADMIN_PLANTEL")
    users = [
        USUARIOS[0],
        {**USUARIOS[1], "activo": True},
        {**USUARIOS[1], "id_usuario": 3, "correo": "otro@udl.edu.mx", "id_plantel_asignado": 2},
    ]
    with patch(
        "schedule.app.routes.admin_routes.IAMClient.list_users", return_value=users,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles", return_value=PLANTELES,
    ):
        response = client.get("/admin/usuarios")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "luis@udl.edu.mx" in html
    assert "ana@udl.edu.mx" not in html
    assert "otro@udl.edu.mx" not in html
    assert "Plantel Centro" not in html


def test_admin_plantel_user_form_does_not_offer_coordinator_role():
    client = authenticated_client(role="ADMIN_PLANTEL")
    with patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles", return_value=PLANTELES[:2],
    ):
        response = client.get("/admin/usuarios/nuevo")

    html = response.get_data(as_text=True)
    assert 'value="COORDINADOR"' not in html
    assert 'value="DOCENTE"' in html


def test_user_edit_form_loads_iam_user_and_keeps_password_optional():
    client = authenticated_client()
    target = {**USUARIOS[1], "id_usuario": 9, "activo": True}
    with patch(
        "schedule.app.routes.admin_routes.IAMClient.get_user", return_value=target,
    ) as get_mock, patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles", return_value=PLANTELES[:2],
    ):
        response = client.get("/admin/usuarios/9/editar")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    get_mock.assert_called_once_with(9, "test-token")
    assert 'action="/admin/usuarios/9/editar"' in html
    assert 'value="luis@udl.edu.mx"' in html
    assert 'data-edit-mode="true"' in html
    assert 'id="userPassword" name="password"' in html
    assert "Déjala vacía para conservar" in html


def test_user_edit_submits_expected_contract_without_empty_password():
    client = authenticated_client()
    target = {**USUARIOS[1], "id_usuario": 9, "activo": True}
    updated = {**target, "nombre": "Luis actualizado"}
    with patch(
        "schedule.app.routes.admin_routes.IAMClient.get_user", return_value=target,
    ), patch(
        "schedule.app.routes.admin_routes.CatalogClient.list_planteles", return_value=PLANTELES[:2],
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.update_user", return_value=updated,
    ) as update_mock:
        response = client.post(
            "/admin/usuarios/9/editar",
            data={
                "nombre": " Luis actualizado ", "apellido": " Docente ",
                "correo": " LUIS@UDL.EDU.MX ", "rol": "DOCENTE",
                "id_plantel_asignado": "1", "password": "",
                "password_confirmation": "",
            },
        )

    assert response.status_code == 302
    update_mock.assert_called_once_with(
        9,
        {
            "nombre": "Luis actualizado", "apellido": "Docente",
            "correo": "luis@udl.edu.mx", "rol": "DOCENTE",
            "id_plantel_asignado": 1,
        },
        "test-token",
    )


def test_user_deactivation_is_delegated_to_iam():
    client = authenticated_client()
    target = {**USUARIOS[1], "id_usuario": 9, "activo": True}
    with patch(
        "schedule.app.routes.admin_routes.IAMClient.get_user", return_value=target,
    ), patch(
        "schedule.app.routes.admin_routes.IAMClient.deactivate_user", return_value={**target, "activo": False},
    ) as deactivate_mock:
        response = client.post("/admin/usuarios/9/desactivar")

    assert response.status_code == 302
    deactivate_mock.assert_called_once_with(9, "test-token")
    with client.session_transaction() as frontend_session:
        assert ("success", "El usuario se desactivó correctamente.") in frontend_session["_flashes"]


def test_current_user_cannot_deactivate_own_account_from_visual_route():
    client = authenticated_client()
    with patch(
        "schedule.app.routes.admin_routes.IAMClient.get_user",
    ) as get_mock, patch(
        "schedule.app.routes.admin_routes.IAMClient.deactivate_user",
    ) as deactivate_mock:
        response = client.post("/admin/usuarios/1/desactivar")

    assert response.status_code == 302
    get_mock.assert_not_called()
    deactivate_mock.assert_not_called()
