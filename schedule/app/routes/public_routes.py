"""Rutas públicas y sesión de acceso de la capa de presentación."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from schedule.app.clients.booking_client import BookingClient, BookingUnavailableError
from schedule.app.clients.catalog_client import CatalogClient, CatalogUnavailableError
from schedule.app.clients.iam_client import (
    IAMAuthenticationError,
    IAMClient,
    IAMUnavailableError,
)
from schedule.app.permissions import ADMIN_ROLES, PUBLIC_ROLES


public_bp = Blueprint("public", __name__)


def _schedule_filters():
    """Normaliza filtros y respeta el alcance de ADMIN_PLANTEL."""
    filters = {
        name: request.args.get(name)
        for name in BookingClient.FILTER_NAMES
        if request.args.get(name) not in {None, ""}
    }
    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        if assigned_id is not None:
            filters["id_plantel"] = assigned_id
    return filters


def _role_destination(role):
    """Obtiene la vista inicial correspondiente al rol emitido por IAM."""
    if role in ADMIN_ROLES:
        return url_for("admin.dashboard")
    if role in PUBLIC_ROLES:
        return url_for("public.schedules")
    return None


@public_bp.route("/login", methods=["GET", "POST"])
def login():
    """Autentica contra IAM y crea una sesión exclusiva del frontend."""
    current_user = session.get("iam_user")
    if request.method == "GET" and current_user:
        destination = _role_destination(current_user.get("rol"))
        if destination:
            return redirect(destination)
        session.clear()

    if request.method == "GET":
        return render_template("public/login.html", login_email="")

    correo = request.form.get("correo", "").strip().lower()
    password = request.form.get("password", "")
    if not correo or "@" not in correo or not password:
        return render_template(
            "public/login.html",
            login_email=correo,
            login_error="Ingresa un correo y una contraseña válidos.",
        )

    try:
        authentication = IAMClient.login(correo, password)
    except IAMAuthenticationError as error:
        return render_template(
            "public/login.html",
            login_email=correo,
            login_error=str(error),
        )
    except IAMUnavailableError as error:
        return render_template(
            "public/login.html",
            login_email=correo,
            login_error=str(error),
            iam_unavailable=True,
        )

    usuario = authentication["usuario"]
    role = str(usuario.get("rol", "")).upper()
    destination = _role_destination(role)
    if destination is None:
        return render_template(
            "public/login.html",
            login_email=correo,
            login_error="El rol de esta cuenta no tiene una vista habilitada.",
        )

    session.clear()
    session["iam_token"] = authentication["token"]
    session["iam_user"] = {
        "id_usuario": usuario.get("id_usuario"),
        "nombre": usuario.get("nombre"),
        "apellido": usuario.get("apellido"),
        "correo": usuario.get("correo", correo),
        "rol": role,
        "id_plantel_asignado": usuario.get("id_plantel_asignado"),
    }
    if role in PUBLIC_ROLES:
        role_label = "Docente" if role == "DOCENTE" else "Alumno"
        flash(
            f"Has iniciado sesión como {role_label}. Por permisos de tu rol, "
            "solo puedes consultar las vistas públicas.",
            "role_notice",
        )
    return redirect(destination)


@public_bp.post("/logout")
def logout():
    """Elimina el token y la identidad conservados por el frontend."""
    session.clear()
    return redirect(url_for("public.login"))


@public_bp.get("/templates/login.html")
def legacy_login():
    """Conserva temporalmente los enlaces anteriores durante la migración."""
    return redirect(url_for("public.login"))


@public_bp.get("/index.html")
def legacy_index():
    """Evita mantener una segunda entrada de login accesible."""
    return redirect(url_for("public.login"))


@public_bp.get("/templates/horarios-publicos.html")
def legacy_public_schedules():
    """Conserva la URL anterior de la consulta pública."""
    return redirect(url_for("public.schedules"))


@public_bp.get("/horarios")
def schedules():
    """Consulta la cuadrícula pública de Booking y conserva la vista existente."""
    filters = _schedule_filters()
    try:
        schedule_records = BookingClient.list_schedule(filters)
        schedule_error = None
    except BookingUnavailableError as error:
        schedule_records = []
        schedule_error = str(error)

    return render_template(
        "public/horarios.html",
        schedule_records=schedule_records,
        schedule_error=schedule_error,
        filter_values=filters,
    )


@public_bp.get("/api/horarios")
def schedule_data():
    """Proxy JSON del mismo origen para actualizar la cuadrícula con Fetch."""
    try:
        records = BookingClient.list_schedule(_schedule_filters())
    except BookingUnavailableError as error:
        return jsonify({"error": str(error)}), 503
    return jsonify({"total": len(records), "grid": records})


@public_bp.get("/api/horarios/filtros")
def schedule_filter_options():
    """Obtiene de Catalog las opciones vigentes de consulta de horarios."""
    try:
        planteles = CatalogClient.list_planteles(active_only=True)
        salones = CatalogClient.list_salones(active_only=True)
        programas = CatalogClient.list_programas(active_only=True)
    except CatalogUnavailableError as error:
        return jsonify({"error": str(error)}), 503

    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        planteles = [
            record for record in planteles
            if str(record.get("id", record.get("id_plantel"))) == str(assigned_id)
        ]
        salones = [
            record for record in salones
            if str(record.get("id_plantel")) == str(assigned_id)
        ]

    return jsonify({
        "planteles": planteles,
        "salones": salones,
        "programas": programas,
    })


@public_bp.get("/")
def home():
    """Usa el login como punto de entrada del módulo frontend."""
    return redirect(url_for("public.login"))
