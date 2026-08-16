"""Pruebas básicas de las primeras rutas públicas."""

from schedule.app import create_app


class TestConfig:
    TESTING = True


def test_public_schedule_is_rendered():
    client = create_app(TestConfig).test_client()

    response = client.get("/horarios")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Consulta de horarios" in html
    assert 'data-schedule-view="public"' in html
    assert 'href="/css/schedule.css"' in html
    assert 'src="/js/schedule-view.js"' in html


def test_public_schedule_has_named_route():
    client = create_app(TestConfig).test_client()

    response = client.get("/horarios")

    assert response.status_code == 200


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
    assert "admin@udl.edu.mx" in html
    assert "demo1234" in html
    assert 'id="loginForm"' in html
    assert 'data-admin-url="/admin/"' in html
    assert 'src="/js/login.js"' in html


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
