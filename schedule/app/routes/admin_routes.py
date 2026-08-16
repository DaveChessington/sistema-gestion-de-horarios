"""Rutas visuales del área administrativa."""

from flask import Blueprint, redirect, render_template, url_for


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("")
@admin_bp.get("/")
def dashboard():
    """Muestra el resumen administrativo con datos visuales."""
    return render_template(
        "admin/dashboard.html",
        active_page="dashboard",
        breadcrumb="Administración / Resumen",
        page_title="Panel administrativo",
    )


@admin_bp.get("/planteles")
def planteles():
    """Muestra el catálogo visual de planteles con datos estáticos."""
    return render_template(
        "admin/planteles.html",
        active_page="planteles",
        breadcrumb="Administración / Catálogos / Planteles",
        page_title="Gestión de planteles",
        header_status="Datos de muestra",
    )


@admin_bp.get("/planteles/nuevo")
def plantel_new():
    """Muestra el formulario visual para un nuevo plantel."""
    return render_template(
        "admin/plantel-form.html",
        active_page="planteles",
        breadcrumb="Catálogos / Planteles / Nuevo",
        page_title="Registrar plantel",
        header_status="Formulario visual",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.planteles"),
        sidebar_title="Nuevo registro",
        sidebar_description="Formulario visual del catálogo institucional.",
        show_mobile_nav=False,
        show_sidebar_user=False,
    )


@admin_bp.get("/salones")
def salones():
    return render_template("admin/salones.html", active_page="salones", breadcrumb="Administración / Catálogos / Salones", page_title="Gestión de salones", header_status="Datos de muestra")


@admin_bp.get("/salones/nuevo")
def salon_new():
    return _render_visual_form("admin/salon-form.html", "salones", "Catálogos / Salones / Nuevo", "Registrar salón", "Formulario visual de espacios.", url_for("admin.salones"))


@admin_bp.get("/equipos")
def equipos():
    return render_template("admin/equipos.html", active_page="equipos", breadcrumb="Administración / Catálogos / Equipos", page_title="Inventario de equipos", header_status="Datos de muestra")


@admin_bp.get("/equipos/nuevo")
def equipo_new():
    return _render_visual_form("admin/equipo-form.html", "equipos", "Catálogos / Equipos / Nuevo", "Registrar equipo", "Formulario visual de inventario.", url_for("admin.equipos"))


@admin_bp.get("/programas")
def programas():
    return render_template("admin/programas.html", active_page="programas", breadcrumb="Administración / Catálogos / Programas", page_title="Catálogo de programas", header_status="Datos de muestra")


@admin_bp.get("/programas/nuevo")
def programa_new():
    return _render_visual_form("admin/programa-form.html", "programas", "Catálogos / Programas / Nuevo", "Registrar programa", "Formulario visual de software.", url_for("admin.programas"))


@admin_bp.get("/usuarios")
def usuarios():
    return render_template("admin/usuarios.html", active_page="usuarios", breadcrumb="Administración / Usuarios", page_title="Gestión de usuarios", header_status="Datos de muestra")


@admin_bp.get("/usuarios/nuevo")
def usuario_new():
    return _render_visual_form("admin/usuario-form.html", "usuarios", "Administración / Usuarios / Nuevo", "Registrar usuario", "Formulario visual de identidad y acceso.", url_for("admin.usuarios"))


@admin_bp.get("/horarios")
def horarios():
    return render_template("admin/horarios.html", active_page="horarios", breadcrumb="Administración / Horarios", page_title="Gestión de horarios", header_status="Datos de muestra", body_schedule_view="admin")


def _render_visual_form(template, active_page, breadcrumb, page_title, sidebar_description, back_url):
    """Comparte la presentación de formularios sin añadir envío o persistencia."""
    return render_template(
        template,
        active_page=active_page,
        breadcrumb=breadcrumb,
        page_title=page_title,
        header_status="Formulario visual",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=back_url,
        sidebar_title="Nuevo registro",
        sidebar_description=sidebar_description,
        show_mobile_nav=False,
        show_sidebar_user=False,
    )


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
