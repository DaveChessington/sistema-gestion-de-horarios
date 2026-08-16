"""Pruebas básicas del contenedor administrativo visual."""

import pytest

from schedule.app import create_app


class TestConfig:
    TESTING = True


def test_admin_dashboard_is_rendered():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel administrativo" in html
    assert "Resumen general del sistema" in html
    assert 'href="/css/schedule.css"' in html
    assert 'id="dashboardPlantelCount"' in html
    assert 'id="dashboardUsuarioCount"' in html
    assert 'id="dashboardRecordCount"' in html
    assert 'href="/admin/planteles"' in html
    assert 'src="/js/dashboard.js"' in html


def test_admin_dashboard_accepts_trailing_slash():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/")

    assert response.status_code == 200


def test_legacy_admin_url_redirects_to_new_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/templates/admin.html")

    assert response.status_code == 302
    assert response.headers["Location"].rstrip("/").endswith("/admin")


def test_planteles_catalog_is_rendered():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/planteles")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Gestión de planteles" in html
    assert "Plantel León" in html
    assert "Plantel Centro" in html
    assert "Plantel Norte" in html
    assert 'aria-current="page"' in html
    assert 'id="plantelSearch"' in html
    assert 'src="/js/planteles.js"' in html


def test_legacy_planteles_url_redirects_to_new_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/templates/planteles.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/planteles")


def test_new_plantel_form_is_prepared_for_mock_submission():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/planteles/nuevo")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Registrar plantel" in html
    assert "Nombre del plantel" in html
    assert "Dirección" in html
    assert "Formulario visual" in html
    assert 'id="plantelForm"' in html
    assert 'src="/js/plantel-form.js"' in html
    assert 'href="/admin/planteles"' in html


@pytest.mark.parametrize(
    "script_name",
    [
        "admin-session.js",
        "mock-data.js",
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
        "dashboard.js",
    ],
)
def test_mock_frontend_scripts_are_served(script_name):
    client = create_app(TestConfig).test_client()

    response = client.get(f"/js/{script_name}")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


def test_legacy_plantel_form_url_redirects_to_new_route():
    client = create_app(TestConfig).test_client()

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
    ],
)
def test_remaining_admin_views_are_rendered(path, expected_text):
    client = create_app(TestConfig).test_client()

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
    client = create_app(TestConfig).test_client()

    response = client.get(f"/templates/{legacy_page}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(new_path)


def test_admin_schedule_keeps_visual_period_switcher():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/horarios")

    html = response.get_data(as_text=True)
    assert 'data-schedule-view="admin"' in html
    assert "Turno Matutino" in html
    assert "Turno Vespertino" in html
    assert 'src="/js/schedule-view.js"' in html


def test_salones_catalog_is_prepared_for_mock_interactions():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/salones")

    html = response.get_data(as_text=True)
    assert 'id="salonSearch"' in html
    assert 'id="salonPlantelFilter"' in html
    assert 'id="salonStatusFilter"' in html
    assert 'src="/js/salones.js"' in html


def test_salon_form_is_prepared_for_mock_submission():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/salones/nuevo")

    html = response.get_data(as_text=True)
    assert 'id="salonForm"' in html
    assert 'id="salonPlantel"' in html
    assert 'type="submit"' in html
    assert 'src="/js/salon-form.js"' in html


def test_programas_catalog_is_prepared_for_mock_interactions():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/programas")

    html = response.get_data(as_text=True)
    assert 'id="programSearch"' in html
    assert 'id="programStatusFilter"' in html
    assert 'id="programCardGrid"' in html
    assert 'src="/js/programas.js"' in html


def test_program_form_is_prepared_for_mock_submission():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/programas/nuevo")

    html = response.get_data(as_text=True)
    assert 'id="programForm"' in html
    assert 'id="programName"' in html
    assert 'id="programDescription"' in html
    assert 'id="programPreviewName"' in html
    assert 'type="submit"' in html
    assert 'src="/js/programa-form.js"' in html


def test_equipos_catalog_is_prepared_for_mock_interactions():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/equipos")

    html = response.get_data(as_text=True)
    assert 'id="equipmentSearch"' in html
    assert 'id="equipmentPlantelFilter"' in html
    assert 'id="equipmentSalonFilter"' in html
    assert 'id="equipmentStatusFilter"' in html
    assert 'id="equipmentTableBody"' in html
    assert 'id="equipmentMobileGrid"' in html
    assert 'src="/js/equipos.js"' in html


def test_equipment_form_is_prepared_for_mock_submission():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/equipos/nuevo")

    html = response.get_data(as_text=True)
    assert 'id="equipmentForm"' in html
    assert 'id="equipmentName"' in html
    assert 'id="equipmentPlantel"' in html
    assert 'id="equipmentSalon"' in html
    assert 'id="equipmentPreviewName"' in html
    assert 'type="submit"' in html
    assert 'src="/js/equipo-form.js"' in html


def test_usuarios_catalog_is_prepared_for_mock_interactions():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/usuarios")

    html = response.get_data(as_text=True)
    assert 'id="userSearch"' in html
    assert 'id="userRoleFilter"' in html
    assert 'id="userPlantelFilter"' in html
    assert 'id="userStatusFilter"' in html
    assert 'id="userTableBody"' in html
    assert 'id="userMobileGrid"' in html
    assert 'src="/js/usuarios.js"' in html


def test_user_form_is_prepared_for_safe_mock_submission():
    client = create_app(TestConfig).test_client()

    response = client.get("/admin/usuarios/nuevo")

    html = response.get_data(as_text=True)
    assert 'id="userForm"' in html
    assert 'id="userEmail"' in html
    assert 'id="userPassword"' in html
    assert 'id="userRole"' in html
    assert 'id="userPlantel"' in html
    assert "No se almacena la contraseña" in html
    assert 'type="submit"' in html
    assert 'src="/js/usuario-form.js"' in html
