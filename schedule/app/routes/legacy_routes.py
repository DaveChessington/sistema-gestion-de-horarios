"""Redirecciones temporales para las URLs anteriores a Flask/Jinja2."""

from flask import Blueprint, redirect, url_for


legacy_admin_bp = Blueprint("legacy_admin", __name__)


@legacy_admin_bp.get("/templates/admin.html")
def legacy_dashboard():
    """Conserva temporalmente la URL anterior del panel."""
    return redirect(url_for("admin.dashboard"))


@legacy_admin_bp.get("/templates/planteles.html")
def legacy_planteles():
    """Conserva temporalmente la URL anterior del catálogo de planteles."""
    return redirect(url_for("admin.planteles"))


@legacy_admin_bp.get("/templates/plantel-formulario.html")
def legacy_plantel_new():
    """Conserva temporalmente la URL anterior del formulario de plantel."""
    return redirect(url_for("admin.plantel_new"))


LEGACY_ADMIN_ROUTES = {
    "salones.html": "admin.salones",
    "salon-formulario.html": "admin.salon_new",
    "equipos.html": "admin.equipos",
    "equipo-formulario.html": "admin.equipo_new",
    "programas.html": "admin.programas",
    "programa-formulario.html": "admin.programa_new",
    "usuarios.html": "admin.usuarios",
    "usuario-formulario.html": "admin.usuario_new",
    "horarios-admin.html": "admin.horarios",
}


@legacy_admin_bp.get("/templates/<page>")
def legacy_admin_page(page):
    """Redirige las páginas administrativas que ya fueron migradas."""
    endpoint = LEGACY_ADMIN_ROUTES.get(page)
    if endpoint is None:
        return "Página no encontrada", 404
    return redirect(url_for(endpoint))
