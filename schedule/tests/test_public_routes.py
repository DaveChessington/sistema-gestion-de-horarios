"""Pruebas básicas de las primeras rutas públicas."""

from unittest.mock import patch

import pytest

from schedule.app import create_app
from schedule.app.clients.booking_client import BookingUnavailableError
from schedule.app.clients.catalog_client import CatalogUnavailableError
from schedule.app.clients.iam_client import (
    IAMAuthenticationError,
    IAMUnavailableError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "frontend-test-secret"
    IAM_API_BASE_URL = "http://iam.test/api/v1/auth"
    IAM_REQUEST_TIMEOUT = 1
    BOOKING_API_BASE_URL = "http://booking.test/api/v1"
    BOOKING_REQUEST_TIMEOUT = 1


def test_public_schedule_is_rendered():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        response = client.get("/horarios")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Consulta de horarios" in html
    assert 'data-schedule-view="public"' in html
    assert 'href="/css/schedule.css"' in html
    assert 'src="/js/schedule-view.js"' in html
    assert 'id="bookingScheduleData"' in html
    assert 'data-schedule-filters' in html
    assert 'data-schedule-api-url="/api/horarios"' in html
    assert 'name="id_programa"' in html
    assert "Booking conectado" in html
    assert "Vista demostrativa" not in html
    assert 'id="publicLoginLink"' in html
    assert 'id="publicSessionLogout"' not in html


def test_public_schedule_has_named_route():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        response = client.get("/horarios")

    assert response.status_code == 200


def test_public_schedule_forwards_filters_and_embeds_booking_records():
    client = create_app(TestConfig).test_client()
    records = [{
        "id_peticion": 4,
        "id_salon": 2,
        "fecha_reserva": "2026-08-17",
        "hora_inicio": "08:00:00",
        "hora_fin": "08:50:00",
        "estado": "APROBADA",
        "materia_nombre": "Redes",
        "id_programa": None,
        "id_usuario": 7,
        "prioridad_calculada": 90,
        "nombre_tipo_evento": "Clase Curricular",
    }]

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=records,
    ) as booking_client:
        response = client.get("/horarios?id_salon=2&fecha_reserva=2026-08-17")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '"materia_nombre": "Redes"' in html
    assert "Docente de muestra" not in html
    booking_client.assert_called_once_with({
        "id_salon": "2",
        "fecha_reserva": "2026-08-17",
    })


def test_public_schedule_reports_booking_unavailable():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        side_effect=BookingUnavailableError("Booking temporalmente no disponible."),
    ):
        response = client.get("/horarios")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="bookingScheduleError"' in html
    assert "Booking temporalmente no disponible." in html
    assert 'data-schedule-body' in html
    assert 'data-schedule-error' in html


def test_schedule_json_proxy_forwards_filters():
    client = create_app(TestConfig).test_client()
    records = [{"id_peticion": 4, "id_reserva": 8, "estado": "APROBADA"}]

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=records,
    ) as booking_client:
        response = client.get(
            "/api/horarios?id_plantel=1&id_salon=2&id_programa=3&fecha_reserva=2026-08-17"
        )

    assert response.status_code == 200
    assert response.get_json() == {"total": 1, "grid": records}
    booking_client.assert_called_once_with({
        "id_plantel": "1",
        "id_salon": "2",
        "id_programa": "3",
        "fecha_reserva": "2026-08-17",
    })


def test_schedule_json_proxy_reports_booking_failure():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        side_effect=BookingUnavailableError("Booking no disponible."),
    ):
        response = client.get("/api/horarios")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Booking no disponible."


def test_schedule_filter_options_are_loaded_from_catalog():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.CatalogClient.list_planteles",
        return_value=[{"id": 1, "nombre": "Centro"}],
    ), patch(
        "schedule.app.routes.public_routes.CatalogClient.list_salones",
        return_value=[{"id_salon": 2, "numero": "A-1", "id_plantel": 1}],
    ), patch(
        "schedule.app.routes.public_routes.CatalogClient.list_programas",
        return_value=[{"id_programa": 3, "nombre": "ICO"}],
    ):
        response = client.get("/api/horarios/filtros")

    assert response.status_code == 200
    assert response.get_json() == {
        "planteles": [{"id": 1, "nombre": "Centro"}],
        "salones": [{"id_salon": 2, "numero": "A-1", "id_plantel": 1}],
        "programas": [{"id_programa": 3, "nombre": "ICO"}],
    }


def test_schedule_filter_options_report_catalog_failure():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.CatalogClient.list_planteles",
        side_effect=CatalogUnavailableError("Catalog no disponible."),
    ):
        response = client.get("/api/horarios/filtros")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Catalog no disponible."


def test_root_redirects_to_login():
    client = create_app(TestConfig).test_client()

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_existing_stylesheet_is_served():
    client = create_app(TestConfig).test_client()

    response = client.get("/css/schedule.css")

    assert response.status_code == 200
    assert response.mimetype == "text/css"


def test_existing_schedule_script_is_served():
    client = create_app(TestConfig).test_client()

    response = client.get("/js/schedule-view.js")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


def test_login_is_rendered_from_its_public_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/login")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Acceso institucional" in html
    assert "Autenticación institucional" in html
    assert "demo1234" not in html
    assert 'id="loginForm"' in html
    assert 'method="post"' in html
    assert 'action="/login"' in html
    assert 'src="/js/login.js"' in html


def iam_login_result(role="COORDINADOR"):
    return {
        "token": "real-iam-token",
        "usuario": {
            "id_usuario": 7,
            "nombre": "Ana",
            "apellido": "Prueba",
            "correo": "ana@udl.edu.mx",
            "rol": role,
            "id_plantel_asignado": 1,
        },
    }


def test_valid_admin_login_creates_frontend_session():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        return_value=iam_login_result(),
    ) as iam_login:
        response = client.post(
            "/login",
            data={"correo": "ANA@UDL.EDU.MX", "password": "valid-password"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")
    iam_login.assert_called_once_with("ana@udl.edu.mx", "valid-password")
    with client.session_transaction() as frontend_session:
        assert frontend_session["iam_token"] == "real-iam-token"
        assert frontend_session["iam_user"]["rol"] == "COORDINADOR"
        assert "password" not in frontend_session


@pytest.mark.parametrize("role", ["DOCENTE", "ALUMNO"])
def test_public_roles_are_redirected_to_public_schedule(role):
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        return_value=iam_login_result(role),
    ):
        response = client.post(
            "/login",
            data={"correo": "ana@udl.edu.mx", "password": "valid-password"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/horarios")


@pytest.mark.parametrize(
    ("role", "role_label"),
    [("DOCENTE", "Docente"), ("ALUMNO", "Alumno")],
)
def test_public_role_sees_permission_notice_and_logout_instead_of_login(
    role, role_label
):
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        return_value=iam_login_result(role),
    ), patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        response = client.post(
            "/login",
            data={"correo": "ana@udl.edu.mx", "password": "valid-password"},
            follow_redirects=True,
        )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="rolePermissionNotice"' in html
    assert f"Has iniciado sesión como {role_label}" in html
    assert "solo puedes consultar las vistas públicas" in html
    assert 'id="publicSessionLogout"' in html
    assert 'method="post" action="/logout"' in html
    assert 'id="publicLoginLink"' not in html
    assert 'id="publicAdminReturn"' not in html
    assert "Ana" in html


def test_public_role_notice_is_only_shown_once_but_logout_remains_available():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        return_value=iam_login_result("DOCENTE"),
    ), patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        first_response = client.post(
            "/login",
            data={"correo": "ana@udl.edu.mx", "password": "valid-password"},
            follow_redirects=True,
        )
        second_response = client.get("/horarios")

    assert 'id="rolePermissionNotice"' in first_response.get_data(as_text=True)
    second_html = second_response.get_data(as_text=True)
    assert 'id="rolePermissionNotice"' not in second_html
    assert 'id="publicSessionLogout"' in second_html
    assert 'id="publicLoginLink"' not in second_html


def test_admin_session_on_public_schedule_can_return_to_panel_or_logout():
    client = create_app(TestConfig).test_client()
    with client.session_transaction() as frontend_session:
        frontend_session["iam_token"] = "token"
        frontend_session["iam_user"] = iam_login_result("COORDINADOR")["usuario"]

    with patch(
        "schedule.app.routes.public_routes.BookingClient.list_schedule",
        return_value=[],
    ):
        response = client.get("/horarios")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="publicAdminReturn"' in html
    assert 'href="/admin/"' in html
    assert 'id="publicSessionLogout"' in html
    assert 'id="publicLoginLink"' not in html


def test_invalid_iam_credentials_are_rendered_without_session():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        side_effect=IAMAuthenticationError("Credenciales inválidas"),
    ):
        response = client.post(
            "/login",
            data={"correo": "ana@udl.edu.mx", "password": "incorrecta"},
        )

    assert response.status_code == 200
    assert "Credenciales inválidas" in response.get_data(as_text=True)
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session


def test_unavailable_iam_is_reported_as_a_controlled_error():
    client = create_app(TestConfig).test_client()

    with patch(
        "schedule.app.routes.public_routes.IAMClient.login",
        side_effect=IAMUnavailableError("El servicio de identidad no está disponible."),
    ):
        response = client.post(
            "/login",
            data={"correo": "ana@udl.edu.mx", "password": "valid-password"},
        )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="loginServiceError"' in html
    assert "El servicio de identidad no está disponible." in html


def test_logout_clears_frontend_session():
    client = create_app(TestConfig).test_client()
    with client.session_transaction() as frontend_session:
        frontend_session["iam_token"] = "token"
        frontend_session["iam_user"] = iam_login_result()["usuario"]

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as frontend_session:
        assert "iam_token" not in frontend_session
        assert "iam_user" not in frontend_session


def test_login_visual_script_is_served():
    client = create_app(TestConfig).test_client()

    response = client.get("/js/login.js")

    assert response.status_code == 200
    assert response.mimetype == "text/javascript"


def test_legacy_login_url_redirects_to_new_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/templates/login.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_legacy_index_redirects_to_login():
    client = create_app(TestConfig).test_client()

    response = client.get("/index.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_legacy_public_schedule_redirects_to_named_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/templates/horarios-publicos.html")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/horarios")
