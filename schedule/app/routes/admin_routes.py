"""Rutas visuales del área administrativa."""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from schedule.app.clients.booking_client import (
    BookingAuthorizationError,
    BookingClient,
    BookingUnavailableError,
    BookingValidationError,
)
from schedule.app.clients.catalog_client import (
    CatalogAuthorizationError,
    CatalogClient,
    CatalogUnavailableError,
    CatalogValidationError,
)
from schedule.app.clients.iam_client import (
    IAMAuthorizationError,
    IAMClient,
    IAMUnavailableError,
    IAMValidationError,
)
from schedule.app.forms import (
    BOOKING_EVENT_TYPES,
    BOOKING_SLOTS,
    USER_ROLE_OPTIONS,
    strong_password_error,
    validated_booking_payload,
)
from schedule.app.permissions import ADMIN_ROLES


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def require_administrative_session():
    """Restringe las vistas administrativas según la sesión creada por IAM."""
    usuario = session.get("iam_user")
    if not usuario:
        return redirect(url_for("public.login"))
    if usuario.get("rol") not in ADMIN_ROLES:
        return redirect(url_for("public.schedules"))
    return None


def _can_manage_plantel(plantel_id):
    """Aplica en la capa visual el mismo alcance que Catalog vuelve a validar."""
    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "COORDINADOR":
        return True
    return (
        usuario.get("rol") == "ADMIN_PLANTEL"
        and str(usuario.get("id_plantel_asignado")) == str(plantel_id)
    )

def _can_manage_equipo(equipo, salones):
    """Resuelve el plantel del equipo antes de habilitar acciones administrativas."""
    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "COORDINADOR":
        return True

    salon = next(
        (
            item
            for item in salones
            if str(item.get("id_salon")) == str(equipo.get("id_salon"))
        ),
        None,
    )
    return bool(salon and _can_manage_plantel(salon.get("id_plantel")))


def _can_manage_user(target_user):
    """Replica visualmente el alcance que IAM aplica como autoridad final."""
    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "COORDINADOR":
        return True
    return (
        current_user.get("rol") == "ADMIN_PLANTEL"
        and current_user.get("id_plantel_asignado") is not None
        and target_user.get("rol") != "COORDINADOR"
        and str(target_user.get("id_plantel_asignado"))
        == str(current_user.get("id_plantel_asignado"))
    )


def _available_user_roles():
    if session.get("iam_user", {}).get("rol") == "ADMIN_PLANTEL":
        return [option for option in USER_ROLE_OPTIONS if option[0] != "COORDINADOR"]
    return list(USER_ROLE_OPTIONS)


@admin_bp.get("")
@admin_bp.get("/")
def dashboard():
    """Muestra un resumen real y limitado al alcance de la sesión."""
    service_errors = []
    catalog_records = {
        "planteles": [],
        "salones": [],
        "equipos": [],
        "programas": [],
    }
    catalog_available = {}
    catalog_loaders = {
        "planteles": CatalogClient.list_planteles,
        "salones": CatalogClient.list_salones,
        "equipos": CatalogClient.list_equipos,
        "programas": CatalogClient.list_programas,
    }
    for collection_name, loader in catalog_loaders.items():
        try:
            catalog_records[collection_name] = loader(active_only=False)
            catalog_available[collection_name] = True
        except CatalogUnavailableError as error:
            catalog_available[collection_name] = False
            service_errors.append(f"Catalog ({collection_name}): {error}")

    current_user = session.get("iam_user", {})
    role = current_user.get("rol")
    assigned_id = current_user.get("id_plantel_asignado")
    allowed_room_ids = None
    if role == "ADMIN_PLANTEL":
        if assigned_id is None:
            service_errors.append(
                "La cuenta administrativa no tiene un plantel asignado."
            )
            catalog_records["planteles"] = []
            catalog_records["salones"] = []
            catalog_records["equipos"] = []
            allowed_room_ids = set()
        else:
            catalog_records["planteles"] = [
                record
                for record in catalog_records["planteles"]
                if str(record.get("id")) == str(assigned_id)
            ]
            if catalog_available.get("salones"):
                catalog_records["salones"] = [
                    record
                    for record in catalog_records["salones"]
                    if str(record.get("id_plantel")) == str(assigned_id)
                ]
                allowed_room_ids = {
                    str(record.get("id_salon"))
                    for record in catalog_records["salones"]
                    if record.get("id_salon") is not None
                }
                catalog_records["equipos"] = [
                    record
                    for record in catalog_records["equipos"]
                    if str(record.get("id_salon")) in allowed_room_ids
                ]
            else:
                catalog_records["equipos"] = []
                allowed_room_ids = set()

    iam_available = True
    try:
        user_records = IAMClient.list_users(session["iam_token"])
    except IAMAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        user_records = []
        iam_available = False
        service_errors.append(f"IAM: {error}")
    except IAMUnavailableError as error:
        user_records = []
        iam_available = False
        service_errors.append(f"IAM: {error}")

    if role == "ADMIN_PLANTEL":
        user_records = [
            record
            for record in user_records
            if assigned_id is not None
            and str(record.get("id_plantel_asignado")) == str(assigned_id)
        ]

    booking_available = True
    try:
        booking_records = BookingClient.list_history({}, session["iam_token"])
    except BookingAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        booking_records = []
        booking_available = False
        service_errors.append(f"Booking: {error}")
    except (BookingValidationError, BookingUnavailableError) as error:
        booking_records = []
        booking_available = False
        service_errors.append(f"Booking: {error}")

    if allowed_room_ids is not None:
        booking_records = [
            record
            for record in booking_records
            if str(record.get("id_salon")) in allowed_room_ids
        ]

    collections = {
        **catalog_records,
        "usuarios": user_records,
    }
    collection_metrics = {}
    for collection_name, records in collections.items():
        active_count = sum(1 for record in records if record.get("activo") is True)
        collection_metrics[collection_name] = {
            "total": len(records),
            "active": active_count,
            "inactive": len(records) - active_count,
        }

    record_total = sum(item["total"] for item in collection_metrics.values())
    active_total = sum(item["active"] for item in collection_metrics.values())
    dashboard_data = {
        "collections": collection_metrics,
        "totals": {
            "records": record_total,
            "active": active_total,
            "inactive": record_total - active_total,
            "unassigned_equipment": sum(
                1
                for record in catalog_records["equipos"]
                if record.get("id_salon") is None
            ),
        },
        "booking": {
            "total": len(booking_records),
            "approved": sum(
                1
                for record in booking_records
                if record.get("estado") in {"APROBADA", "APARTADA"}
            ),
            "pending": sum(
                1 for record in booking_records if record.get("estado") == "PENDIENTE"
            ),
        },
        "services": {
            "catalog": all(catalog_available.values()),
            "iam": iam_available,
            "booking": booking_available,
        },
        "scope": "plantel" if role == "ADMIN_PLANTEL" else "global",
    }

    return render_template(
        "admin/dashboard.html",
        active_page="dashboard",
        breadcrumb="Administración / Resumen",
        page_title="Panel administrativo",
        header_status="Servicios conectados" if not service_errors else "Datos parciales",
        dashboard_data=dashboard_data,
        service_errors=service_errors,
    )


@admin_bp.get("/planteles")
def planteles():
    """Muestra los planteles obtenidos mediante el contrato público de Catalog."""
    catalog_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=False)
    except CatalogUnavailableError as error:
        plantel_records = []
        catalog_error = str(error)

    current_user = session.get("iam_user", {})
    return render_template(
        "admin/planteles.html",
        active_page="planteles",
        breadcrumb="Administración / Catálogos / Planteles",
        page_title="Gestión de planteles",
        header_status="Catalog conectado" if catalog_error is None else "Catalog no disponible",
        planteles=plantel_records,
        catalog_error=catalog_error,
        can_create_plantel=current_user.get("rol") == "COORDINADOR",
        plantel_action_context={
            "edit_url_template": url_for("admin.plantel_edit", id_plantel=0),
            "deactivate_url_template": url_for("admin.plantel_deactivate", id_plantel=0),
            "role": current_user.get("rol"),
            "assigned_plantel_id": current_user.get("id_plantel_asignado"),
        },
    )


@admin_bp.route("/planteles/nuevo", methods=["GET", "POST"])
def plantel_new():
    """Muestra el formulario y delega el alta de planteles a Catalog."""
    form_values = {
        "nombre": request.form.get("nombre", "").strip(),
        "direccion": request.form.get("direccion", "").strip(),
    }
    form_error = None

    if request.method == "POST":
        if not form_values["nombre"]:
            form_error = "El nombre del plantel es obligatorio."
        else:
            try:
                plantel = CatalogClient.create_plantel(
                    form_values["nombre"],
                    form_values["direccion"],
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(f"El plantel {plantel['nombre']} se registró correctamente.", "success")
                return redirect(url_for("admin.planteles"))

    return render_template(
        "admin/plantel-form.html",
        active_page="planteles",
        breadcrumb="Catálogos / Planteles / Nuevo",
        page_title="Registrar plantel",
        header_status="Catalog conectado",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.planteles"),
        sidebar_title="Nuevo registro",
        sidebar_description="Formulario visual del catálogo institucional.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        form_values=form_values,
        form_error=form_error,
        is_edit=False,
        form_action=url_for("admin.plantel_new"),
    )


@admin_bp.route("/planteles/<int:id_plantel>/editar", methods=["GET", "POST"])
def plantel_edit(id_plantel):
    """Edita un plantel activo mediante el contrato PUT de Catalog."""
    if not _can_manage_plantel(id_plantel):
        flash("No tienes permisos para editar ese plantel.", "error")
        return redirect(url_for("admin.planteles"))

    try:
        plantel = CatalogClient.get_plantel(id_plantel)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.planteles"))

    form_values = {
        "nombre": request.form.get("nombre", plantel.get("nombre", "")).strip(),
        "direccion": request.form.get(
            "direccion", plantel.get("direccion") or ""
        ).strip(),
    }
    form_error = None

    if request.method == "POST":
        if not form_values["nombre"]:
            form_error = "El nombre del plantel es obligatorio."
        else:
            try:
                updated_plantel = CatalogClient.update_plantel(
                    id_plantel,
                    form_values["nombre"],
                    form_values["direccion"],
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(
                    f"El plantel {updated_plantel['nombre']} se actualizó correctamente.",
                    "success",
                )
                return redirect(url_for("admin.planteles"))

    return render_template(
        "admin/plantel-form.html",
        active_page="planteles",
        breadcrumb="Catálogos / Planteles / Editar",
        page_title="Editar plantel",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.planteles"),
        sidebar_title="Edición de plantel",
        sidebar_description="Actualización conectada con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        form_values=form_values,
        form_error=form_error,
        is_edit=True,
        form_action=url_for("admin.plantel_edit", id_plantel=id_plantel),
        plantel=plantel,
    )


@admin_bp.post("/planteles/<int:id_plantel>/desactivar")
def plantel_deactivate(id_plantel):
    """Solicita a Catalog la desactivación lógica de un plantel."""
    if not _can_manage_plantel(id_plantel):
        flash("No tienes permisos para desactivar ese plantel.", "error")
        return redirect(url_for("admin.planteles"))

    try:
        CatalogClient.deactivate_plantel(id_plantel, session["iam_token"])
    except CatalogAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash(
            "El plantel y sus recursos dependientes se desactivaron correctamente.",
            "success",
        )

    return redirect(url_for("admin.planteles"))


@admin_bp.get("/salones")
def salones():
    """Muestra salones y sus planteles obtenidos desde Catalog."""
    catalog_error = None
    try:
        salon_records = CatalogClient.list_salones(active_only=False)
        plantel_records = CatalogClient.list_planteles(active_only=False)
    except CatalogUnavailableError as error:
        salon_records = []
        plantel_records = []
        catalog_error = str(error)

    current_user = session.get("iam_user", {})
    return render_template(
        "admin/salones.html",
        active_page="salones",
        breadcrumb="Administración / Catálogos / Salones",
        page_title="Gestión de salones",
        header_status="Catalog conectado" if catalog_error is None else "Catalog no disponible",
        salones=salon_records,
        planteles=plantel_records,
        catalog_error=catalog_error,
        salon_action_context={
            "edit_url_template": url_for("admin.salon_edit", id_salon=0),
            "deactivate_url_template": url_for("admin.salon_deactivate", id_salon=0),
            "role": current_user.get("rol"),
            "assigned_plantel_id": current_user.get("id_plantel_asignado"),
        },
    )


@admin_bp.route("/salones/nuevo", methods=["GET", "POST"])
def salon_new():
    """Muestra el formulario y delega el alta de salones a Catalog."""
    form_values = {
        "numero": request.form.get("numero", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip(),
        "capacidad": request.form.get("capacidad", "").strip(),
        "id_plantel": request.form.get("id_plantel", "").strip(),
    }
    form_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=True)
    except CatalogUnavailableError as error:
        plantel_records = []
        form_error = str(error)

    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "ADMIN_PLANTEL":
        assigned_id = usuario.get("id_plantel_asignado")
        plantel_records = [
            plantel for plantel in plantel_records
            if str(plantel.get("id")) == str(assigned_id)
        ]

    if request.method == "POST" and form_error is None:
        try:
            capacidad = int(form_values["capacidad"])
        except (TypeError, ValueError):
            capacidad = 0
        try:
            id_plantel = int(form_values["id_plantel"])
        except (TypeError, ValueError):
            id_plantel = 0

        valid_plantel_ids = {plantel.get("id") for plantel in plantel_records}
        if not form_values["numero"]:
            form_error = "El nombre o número del salón es obligatorio."
        elif capacidad <= 0:
            form_error = "La capacidad del salón debe ser mayor a cero."
        elif id_plantel not in valid_plantel_ids:
            form_error = "Selecciona un plantel activo permitido para tu cuenta."
        else:
            try:
                salon = CatalogClient.create_salon(
                    form_values["numero"],
                    form_values["descripcion"],
                    capacidad,
                    id_plantel,
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(f"El salón {salon['numero']} se registró correctamente.", "success")
                return redirect(url_for("admin.salones"))

    return render_template(
        "admin/salon-form.html",
        active_page="salones",
        breadcrumb="Catálogos / Salones / Nuevo",
        page_title="Registrar salón",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.salones"),
        sidebar_title="Nuevo registro",
        sidebar_description="Formulario conectado con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        form_values=form_values,
        form_error=form_error,
        is_edit=False,
        form_action=url_for("admin.salon_new"),
    )


@admin_bp.route("/salones/<int:id_salon>/editar", methods=["GET", "POST"])
def salon_edit(id_salon):
    """Edita un salón activo y conserva la validación relacional en Catalog."""
    try:
        salon = CatalogClient.get_salon(id_salon)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.salones"))

    if not _can_manage_plantel(salon.get("id_plantel")):
        flash("No tienes permisos para editar ese salón.", "error")
        return redirect(url_for("admin.salones"))

    form_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=True)
    except CatalogUnavailableError as error:
        plantel_records = []
        form_error = str(error)

    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "ADMIN_PLANTEL":
        assigned_id = usuario.get("id_plantel_asignado")
        plantel_records = [
            plantel
            for plantel in plantel_records
            if str(plantel.get("id")) == str(assigned_id)
        ]

    form_values = {
        "numero": request.form.get("numero", salon.get("numero", "")).strip(),
        "descripcion": request.form.get(
            "descripcion", salon.get("descripcion") or ""
        ).strip(),
        "capacidad": request.form.get(
            "capacidad", str(salon.get("capacidad", ""))
        ).strip(),
        "id_plantel": request.form.get(
            "id_plantel", str(salon.get("id_plantel", ""))
        ).strip(),
    }

    if request.method == "POST" and form_error is None:
        try:
            capacidad = int(form_values["capacidad"])
        except (TypeError, ValueError):
            capacidad = 0
        try:
            id_plantel = int(form_values["id_plantel"])
        except (TypeError, ValueError):
            id_plantel = 0

        valid_plantel_ids = {plantel.get("id") for plantel in plantel_records}
        if not form_values["numero"]:
            form_error = "El nombre o número del salón es obligatorio."
        elif capacidad <= 0:
            form_error = "La capacidad del salón debe ser mayor a cero."
        elif id_plantel not in valid_plantel_ids:
            form_error = "Selecciona un plantel activo permitido para tu cuenta."
        else:
            try:
                updated_salon = CatalogClient.update_salon(
                    id_salon,
                    form_values["numero"],
                    form_values["descripcion"],
                    capacidad,
                    id_plantel,
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(
                    f"El salón {updated_salon['numero']} se actualizó correctamente.",
                    "success",
                )
                return redirect(url_for("admin.salones"))

    return render_template(
        "admin/salon-form.html",
        active_page="salones",
        breadcrumb="Catálogos / Salones / Editar",
        page_title="Editar salón",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.salones"),
        sidebar_title="Edición de salón",
        sidebar_description="Actualización conectada con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        form_values=form_values,
        form_error=form_error,
        is_edit=True,
        form_action=url_for("admin.salon_edit", id_salon=id_salon),
        salon=salon,
    )


@admin_bp.post("/salones/<int:id_salon>/desactivar")
def salon_deactivate(id_salon):
    """Solicita a Catalog la desactivación lógica de un salón."""
    try:
        salon = CatalogClient.get_salon(id_salon)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.salones"))

    if not _can_manage_plantel(salon.get("id_plantel")):
        flash("No tienes permisos para desactivar ese salón.", "error")
        return redirect(url_for("admin.salones"))

    try:
        CatalogClient.deactivate_salon(id_salon, session["iam_token"])
    except CatalogAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash(
            "El salón y sus equipos asociados se desactivaron correctamente.",
            "success",
        )

    return redirect(url_for("admin.salones"))


@admin_bp.get("/equipos")
def equipos():
    """Muestra equipos y sus ubicaciones obtenidos desde Catalog."""
    catalog_error = None
    try:
        equipo_records = CatalogClient.list_equipos(active_only=False)
        salon_records = CatalogClient.list_salones(active_only=False)
        plantel_records = CatalogClient.list_planteles(active_only=False)
    except CatalogUnavailableError as error:
        equipo_records = []
        salon_records = []
        plantel_records = []
        catalog_error = str(error)

    current_user = session.get("iam_user", {})
    return render_template(
        "admin/equipos.html",
        active_page="equipos",
        breadcrumb="Administración / Catálogos / Equipos",
        page_title="Inventario de equipos",
        header_status="Catalog conectado" if catalog_error is None else "Catalog no disponible",
        equipos=equipo_records,
        salones=salon_records,
        planteles=plantel_records,
        catalog_error=catalog_error,
        equipment_action_context={
            "edit_url_template": url_for("admin.equipo_edit", id_equipo=0),
            "deactivate_url_template": url_for("admin.equipo_deactivate", id_equipo=0),
            "role": current_user.get("rol"),
            "assigned_plantel_id": current_user.get("id_plantel_asignado"),
        },
    )


@admin_bp.route("/equipos/nuevo", methods=["GET", "POST"])
def equipo_new():
    """Muestra el formulario y delega el alta de equipos a Catalog."""
    form_values = {
        "numero": request.form.get("numero", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip(),
        "id_salon": request.form.get("id_salon", "").strip(),
    }
    form_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=True)
        salon_records = CatalogClient.list_salones(active_only=True)
    except CatalogUnavailableError as error:
        plantel_records = []
        salon_records = []
        form_error = str(error)

    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "ADMIN_PLANTEL":
        assigned_id = usuario.get("id_plantel_asignado")
        plantel_records = [
            plantel for plantel in plantel_records
            if plantel.get("id") == assigned_id
        ]
        salon_records = [
            salon for salon in salon_records
            if salon.get("id_plantel") == assigned_id
        ]

    if request.method == "POST" and form_error is None:
        id_salon = None
        invalid_salon = False
        if form_values["id_salon"]:
            try:
                id_salon = int(form_values["id_salon"])
            except (TypeError, ValueError):
                invalid_salon = True

        valid_salon_ids = {salon.get("id_salon") for salon in salon_records}
        if not form_values["numero"]:
            form_error = "El número o identificador del equipo es obligatorio."
        elif invalid_salon or (id_salon is not None and id_salon not in valid_salon_ids):
            form_error = "Selecciona un salón activo permitido para tu cuenta."
        elif usuario.get("rol") == "ADMIN_PLANTEL" and id_salon is None:
            form_error = "Selecciona un salón de tu plantel para conservar el alcance del equipo."
        else:
            try:
                equipo = CatalogClient.create_equipo(
                    form_values["numero"],
                    form_values["descripcion"],
                    id_salon,
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(f"El equipo {equipo['numero']} se registró correctamente.", "success")
                return redirect(url_for("admin.equipos"))

    return render_template(
        "admin/equipo-form.html",
        active_page="equipos",
        breadcrumb="Catálogos / Equipos / Nuevo",
        page_title="Registrar equipo",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.equipos"),
        sidebar_title="Nuevo registro",
        sidebar_description="Formulario conectado con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        salones=salon_records,
        form_values=form_values,
        form_error=form_error,
        is_edit=False,
        form_action=url_for("admin.equipo_new"),
        requires_salon=usuario.get("rol") == "ADMIN_PLANTEL",
    )


@admin_bp.route("/equipos/<int:id_equipo>/editar", methods=["GET", "POST"])
def equipo_edit(id_equipo):
    """Edita un equipo activo sin alterar sus asociaciones de programas."""
    try:
        equipo = CatalogClient.get_equipo(id_equipo)
        plantel_records = CatalogClient.list_planteles(active_only=True)
        salon_records = CatalogClient.list_salones(active_only=True)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.equipos"))

    if not _can_manage_equipo(equipo, salon_records):
        flash("No tienes permisos para editar ese equipo.", "error")
        return redirect(url_for("admin.equipos"))

    usuario = session.get("iam_user", {})
    if usuario.get("rol") == "ADMIN_PLANTEL":
        assigned_id = usuario.get("id_plantel_asignado")
        plantel_records = [
            plantel
            for plantel in plantel_records
            if str(plantel.get("id")) == str(assigned_id)
        ]
        salon_records = [
            salon
            for salon in salon_records
            if str(salon.get("id_plantel")) == str(assigned_id)
        ]

    form_values = {
        "numero": request.form.get("numero", equipo.get("numero", "")).strip(),
        "descripcion": request.form.get(
            "descripcion", equipo.get("descripcion") or ""
        ).strip(),
        "id_salon": request.form.get(
            "id_salon",
            "" if equipo.get("id_salon") is None else str(equipo.get("id_salon")),
        ).strip(),
    }
    form_error = None

    if request.method == "POST":
        id_salon = None
        invalid_salon = False
        if form_values["id_salon"]:
            try:
                id_salon = int(form_values["id_salon"])
            except (TypeError, ValueError):
                invalid_salon = True

        valid_salon_ids = {salon.get("id_salon") for salon in salon_records}
        if not form_values["numero"]:
            form_error = "El número o identificador del equipo es obligatorio."
        elif invalid_salon or (id_salon is not None and id_salon not in valid_salon_ids):
            form_error = "Selecciona un salón activo permitido para tu cuenta."
        elif usuario.get("rol") == "ADMIN_PLANTEL" and id_salon is None:
            form_error = "Selecciona un salón de tu plantel para conservar el alcance del equipo."
        else:
            try:
                updated_equipo = CatalogClient.update_equipo(
                    id_equipo,
                    form_values["numero"],
                    form_values["descripcion"],
                    id_salon,
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(
                    f"El equipo {updated_equipo['numero']} se actualizó correctamente.",
                    "success",
                )
                return redirect(url_for("admin.equipos"))

    return render_template(
        "admin/equipo-form.html",
        active_page="equipos",
        breadcrumb="Catálogos / Equipos / Editar",
        page_title="Editar equipo",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.equipos"),
        sidebar_title="Edición de equipo",
        sidebar_description="Actualización conectada con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        salones=salon_records,
        form_values=form_values,
        form_error=form_error,
        is_edit=True,
        form_action=url_for("admin.equipo_edit", id_equipo=id_equipo),
        equipo=equipo,
        requires_salon=usuario.get("rol") == "ADMIN_PLANTEL",
    )


@admin_bp.post("/equipos/<int:id_equipo>/desactivar")
def equipo_deactivate(id_equipo):
    """Solicita a Catalog la desactivación lógica de un equipo."""
    try:
        equipo = CatalogClient.get_equipo(id_equipo)
        salon_records = CatalogClient.list_salones(active_only=True)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.equipos"))

    if not _can_manage_equipo(equipo, salon_records):
        flash("No tienes permisos para desactivar ese equipo.", "error")
        return redirect(url_for("admin.equipos"))

    try:
        CatalogClient.deactivate_equipo(id_equipo, session["iam_token"])
    except CatalogAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash("El equipo se desactivó correctamente.", "success")

    return redirect(url_for("admin.equipos"))


@admin_bp.get("/programas")
def programas():
    """Muestra programas y asociaciones obtenidos desde Catalog."""
    catalog_error = None
    try:
        programa_records = CatalogClient.list_programas(active_only=False)
        equipo_records = CatalogClient.list_equipos(active_only=False)
    except CatalogUnavailableError as error:
        programa_records = []
        equipo_records = []
        catalog_error = str(error)

    return render_template(
        "admin/programas.html",
        active_page="programas",
        breadcrumb="Administración / Catálogos / Programas",
        page_title="Catálogo de programas",
        header_status="Catalog conectado" if catalog_error is None else "Catalog no disponible",
        programas=programa_records,
        equipos=equipo_records,
        catalog_error=catalog_error,
        program_action_context={
            "associate_url_template": url_for(
                "admin.programa_equipos", id_programa=0
            ),
            "edit_url_template": url_for("admin.programa_edit", id_programa=0),
            "deactivate_url_template": url_for(
                "admin.programa_deactivate", id_programa=0
            ),
        },
    )


@admin_bp.route("/programas/nuevo", methods=["GET", "POST"])
def programa_new():
    """Muestra el formulario y delega el alta de programas a Catalog."""
    form_values = {
        "nombre": request.form.get("nombre", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip(),
    }
    form_error = None

    if request.method == "POST":
        if not form_values["nombre"]:
            form_error = "El nombre del programa es obligatorio."
        else:
            try:
                programa = CatalogClient.create_programa(
                    form_values["nombre"],
                    form_values["descripcion"],
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(f"El programa {programa['nombre']} se registró correctamente.", "success")
                return redirect(url_for("admin.programas"))

    return render_template(
        "admin/programa-form.html",
        active_page="programas",
        breadcrumb="Catálogos / Programas / Nuevo",
        page_title="Registrar programa",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.programas"),
        sidebar_title="Nuevo registro",
        sidebar_description="Formulario conectado con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        form_values=form_values,
        form_error=form_error,
        is_edit=False,
        form_action=url_for("admin.programa_new"),
    )


@admin_bp.route("/programas/<int:id_programa>/editar", methods=["GET", "POST"])
def programa_edit(id_programa):
    """Edita un programa activo mediante el contrato protegido de Catalog."""
    try:
        programa = CatalogClient.get_programa(id_programa)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.programas"))

    form_values = {
        "nombre": request.form.get("nombre", programa.get("nombre", "")).strip(),
        "descripcion": request.form.get(
            "descripcion", programa.get("descripcion") or ""
        ).strip(),
    }
    form_error = None

    if request.method == "POST":
        if not form_values["nombre"]:
            form_error = "El nombre del programa es obligatorio."
        else:
            try:
                updated_programa = CatalogClient.update_programa(
                    id_programa,
                    form_values["nombre"],
                    form_values["descripcion"],
                    session["iam_token"],
                )
            except CatalogAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (CatalogValidationError, CatalogUnavailableError) as error:
                form_error = str(error)
            else:
                flash(
                    f"El programa {updated_programa['nombre']} se actualizó correctamente.",
                    "success",
                )
                return redirect(url_for("admin.programas"))

    return render_template(
        "admin/programa-form.html",
        active_page="programas",
        breadcrumb="Catálogos / Programas / Editar",
        page_title="Editar programa",
        header_status="Catalog conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.programas"),
        sidebar_title="Edición de programa",
        sidebar_description="Actualización conectada con Catalog.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        form_values=form_values,
        form_error=form_error,
        is_edit=True,
        form_action=url_for("admin.programa_edit", id_programa=id_programa),
        programa=programa,
    )


@admin_bp.post("/programas/<int:id_programa>/desactivar")
def programa_deactivate(id_programa):
    """Solicita a Catalog la desactivación lógica de un programa."""
    try:
        CatalogClient.deactivate_programa(id_programa, session["iam_token"])
    except CatalogAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash("El programa se desactivó correctamente.", "success")

    return redirect(url_for("admin.programas"))


@admin_bp.get("/programas/<int:id_programa>/equipos")
def programa_equipos(id_programa):
    """Muestra los equipos que pueden vincularse con un programa activo."""
    try:
        programa = CatalogClient.get_programa(id_programa)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.programas"))

    catalog_error = None
    try:
        equipo_records = CatalogClient.list_equipos(active_only=True)
        salon_records = CatalogClient.list_salones(active_only=True)
        plantel_records = CatalogClient.list_planteles(active_only=True)
    except CatalogUnavailableError as error:
        equipo_records = []
        salon_records = []
        plantel_records = []
        catalog_error = str(error)

    salons_by_id = {
        str(salon.get("id_salon")): salon for salon in salon_records
    }
    planteles_by_id = {
        str(plantel.get("id")): plantel for plantel in plantel_records
    }
    equipment_view_records = []
    for equipo in equipo_records:
        if not _can_manage_equipo(equipo, salon_records):
            continue
        salon = salons_by_id.get(str(equipo.get("id_salon")))
        plantel = planteles_by_id.get(str(salon.get("id_plantel"))) if salon else None
        associated = any(
            str(item.get("id_programa")) == str(id_programa)
            for item in equipo.get("programas", [])
            if isinstance(item, dict)
        )
        equipment_view_records.append(
            {
                **equipo,
                "salon_nombre": salon.get("numero") if salon else "Sin salón asignado",
                "plantel_nombre": plantel.get("nombre") if plantel else "Sin plantel",
                "associated": associated,
            }
        )

    return render_template(
        "admin/programa-equipos.html",
        active_page="programas",
        breadcrumb="Catálogos / Programas / Asociaciones",
        page_title=f"Equipos de {programa['nombre']}",
        header_status="Catalog conectado" if catalog_error is None else "Catalog no disponible",
        back_url=url_for("admin.programas"),
        sidebar_title="Asociaciones de software",
        sidebar_description="Vinculación de equipos conectada con Catalog.",
        programa=programa,
        equipos=equipment_view_records,
        catalog_error=catalog_error,
    )


def _change_program_equipment(id_programa, id_equipo, assign):
    """Valida el alcance visual y delega una asociación individual a Catalog."""
    try:
        programa = CatalogClient.get_programa(id_programa)
        equipo = CatalogClient.get_equipo(id_equipo)
        salon_records = CatalogClient.list_salones(active_only=True)
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.programas"))

    if not _can_manage_equipo(equipo, salon_records):
        flash("No tienes permisos para administrar programas en ese equipo.", "error")
        return redirect(url_for("admin.programa_equipos", id_programa=id_programa))

    try:
        if assign:
            CatalogClient.assign_programa(
                id_equipo, id_programa, session["iam_token"]
            )
        else:
            CatalogClient.remove_programa(
                id_equipo, id_programa, session["iam_token"]
            )
    except CatalogAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (CatalogValidationError, CatalogUnavailableError) as error:
        flash(str(error), "error")
    else:
        action = "vinculó con" if assign else "desvinculó de"
        flash(
            f"El equipo {equipo['numero']} se {action} {programa['nombre']} correctamente.",
            "success",
        )

    return redirect(url_for("admin.programa_equipos", id_programa=id_programa))


@admin_bp.post("/programas/<int:id_programa>/equipos/<int:id_equipo>/asociar")
def programa_equipo_assign(id_programa, id_equipo):
    return _change_program_equipment(id_programa, id_equipo, assign=True)


@admin_bp.post("/programas/<int:id_programa>/equipos/<int:id_equipo>/desvincular")
def programa_equipo_remove(id_programa, id_equipo):
    return _change_program_equipment(id_programa, id_equipo, assign=False)


@admin_bp.get("/usuarios")
def usuarios():
    """Muestra usuarios de IAM y nombres de plantel obtenidos desde Catalog."""
    service_errors = []
    try:
        user_records = IAMClient.list_users(session["iam_token"])
    except IAMAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        user_records = []
        service_errors.append(str(error))
    except IAMUnavailableError as error:
        user_records = []
        service_errors.append(str(error))

    try:
        plantel_records = CatalogClient.list_planteles(active_only=False)
    except CatalogUnavailableError as error:
        plantel_records = []
        service_errors.append(str(error))

    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        user_records = [
            user for user in user_records
            if assigned_id is not None
            and str(user.get("id_plantel_asignado")) == str(assigned_id)
            and user.get("rol") != "COORDINADOR"
        ]
        plantel_records = [
            plantel for plantel in plantel_records
            if str(plantel.get("id")) == str(assigned_id)
        ]

    return render_template(
        "admin/usuarios.html",
        active_page="usuarios",
        breadcrumb="Administración / Usuarios",
        page_title="Gestión de usuarios",
        header_status="Servicios conectados" if not service_errors else "Servicio no disponible",
        usuarios=user_records,
        planteles=plantel_records,
        service_errors=service_errors,
        user_action_context={
            "edit_url_template": url_for("admin.usuario_edit", user_id=0),
            "deactivate_url_template": url_for("admin.usuario_deactivate", user_id=0),
            "current_user_id": current_user.get("id_usuario"),
            "role": current_user.get("rol"),
            "assigned_plantel_id": current_user.get("id_plantel_asignado"),
        },
    )


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
def usuario_new():
    """Muestra el formulario administrativo y delega el registro a IAM."""
    form_values = {
        "nombre": request.form.get("nombre", "").strip(),
        "apellido": request.form.get("apellido", "").strip(),
        "correo": request.form.get("correo", "").strip().lower(),
        "rol": request.form.get("rol", "").strip().upper(),
        "id_plantel_asignado": request.form.get("id_plantel_asignado", "").strip(),
    }
    password = request.form.get("password", "")
    password_confirmation = request.form.get("password_confirmation", "")
    form_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=True)
    except CatalogUnavailableError as error:
        plantel_records = []
        form_error = str(error)

    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        plantel_records = [
            plantel for plantel in plantel_records
            if plantel.get("id") == assigned_id
        ]

    if request.method == "POST" and form_error is None:
        id_plantel = None
        invalid_plantel = False
        if form_values["id_plantel_asignado"]:
            try:
                id_plantel = int(form_values["id_plantel_asignado"])
            except (TypeError, ValueError):
                invalid_plantel = True

        valid_roles = {option[0] for option in _available_user_roles()}
        valid_plantel_ids = {plantel.get("id") for plantel in plantel_records}
        if not form_values["nombre"] or not form_values["apellido"]:
            form_error = "El nombre y el apellido son obligatorios."
        elif "@" not in form_values["correo"]:
            form_error = "Ingresa un correo institucional válido."
        elif strong_password_error(password):
            form_error = strong_password_error(password)
        elif password != password_confirmation:
            form_error = "La confirmación de la contraseña no coincide."
        elif form_values["rol"] not in valid_roles:
            form_error = "Selecciona un rol válido."
        elif invalid_plantel or (id_plantel is not None and id_plantel not in valid_plantel_ids):
            form_error = "Selecciona un plantel activo permitido para tu cuenta."
        elif form_values["rol"] == "ADMIN_PLANTEL" and id_plantel is None:
            form_error = "El administrador de plantel requiere una asignación."
        elif current_user.get("rol") == "ADMIN_PLANTEL" and id_plantel is None:
            form_error = "Debes asignar el usuario a tu plantel."
        else:
            try:
                usuario = IAMClient.register_user(
                    {
                        "nombre": form_values["nombre"],
                        "apellido": form_values["apellido"],
                        "correo": form_values["correo"],
                        "password": password,
                        "rol": form_values["rol"],
                        "id_plantel_asignado": id_plantel,
                    },
                    session["iam_token"],
                )
            except IAMAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (IAMValidationError, IAMUnavailableError) as error:
                form_error = str(error)
            else:
                flash(f"El usuario {usuario['correo']} se registró correctamente.", "success")
                return redirect(url_for("admin.usuarios"))

    return render_template(
        "admin/usuario-form.html",
        active_page="usuarios",
        breadcrumb="Administración / Usuarios / Nuevo",
        page_title="Registrar usuario",
        header_status="IAM conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.usuarios"),
        sidebar_title="Nuevo registro",
        sidebar_description="Registro administrativo conectado con IAM.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        form_values=form_values,
        form_error=form_error,
        available_roles=_available_user_roles(),
        is_edit=False,
        form_action=url_for("admin.usuario_new"),
        lock_scope_fields=False,
        requires_plantel=current_user.get("rol") == "ADMIN_PLANTEL",
    )


@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
def usuario_edit(user_id):
    """Edita una cuenta existente mediante IAM sin exponer su contraseña actual."""
    try:
        target_user = IAMClient.get_user(user_id, session["iam_token"])
    except IAMAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
        return redirect(url_for("admin.usuarios"))
    except (IAMValidationError, IAMUnavailableError) as error:
        flash(str(error), "error")
        return redirect(url_for("admin.usuarios"))

    if not _can_manage_user(target_user):
        flash("No tienes permisos para editar ese usuario.", "error")
        return redirect(url_for("admin.usuarios"))

    form_values = {
        "nombre": request.form.get("nombre", target_user.get("nombre", "")).strip(),
        "apellido": request.form.get("apellido", target_user.get("apellido", "")).strip(),
        "correo": request.form.get("correo", target_user.get("correo", "")).strip().lower(),
        "rol": request.form.get("rol", target_user.get("rol", "")).strip().upper(),
        "id_plantel_asignado": request.form.get(
            "id_plantel_asignado",
            "" if target_user.get("id_plantel_asignado") is None else str(target_user["id_plantel_asignado"]),
        ).strip(),
    }
    password = request.form.get("password", "")
    password_confirmation = request.form.get("password_confirmation", "")
    form_error = None
    try:
        plantel_records = CatalogClient.list_planteles(active_only=True)
    except CatalogUnavailableError as error:
        plantel_records = []
        form_error = str(error)

    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        plantel_records = [
            plantel for plantel in plantel_records
            if str(plantel.get("id")) == str(assigned_id)
        ]

    if request.method == "POST" and form_error is None:
        id_plantel = None
        invalid_plantel = False
        if form_values["id_plantel_asignado"]:
            try:
                id_plantel = int(form_values["id_plantel_asignado"])
            except (TypeError, ValueError):
                invalid_plantel = True
        valid_roles = {option[0] for option in _available_user_roles()}
        valid_plantel_ids = {plantel.get("id") for plantel in plantel_records}
        is_self = str(current_user.get("id_usuario")) == str(user_id)
        if not form_values["nombre"] or not form_values["apellido"]:
            form_error = "El nombre y el apellido son obligatorios."
        elif "@" not in form_values["correo"]:
            form_error = "Ingresa un correo institucional válido."
        elif password and strong_password_error(password):
            form_error = strong_password_error(password)
        elif password != password_confirmation:
            form_error = "La confirmación de la contraseña no coincide."
        elif form_values["rol"] not in valid_roles:
            form_error = "Selecciona un rol válido."
        elif invalid_plantel or (id_plantel is not None and id_plantel not in valid_plantel_ids):
            form_error = "Selecciona un plantel activo permitido para tu cuenta."
        elif form_values["rol"] == "ADMIN_PLANTEL" and id_plantel is None:
            form_error = "El administrador de plantel requiere una asignación."
        elif current_user.get("rol") == "ADMIN_PLANTEL" and id_plantel is None:
            form_error = "Debes asignar el usuario a tu plantel."
        elif is_self and (
            form_values["rol"] != target_user.get("rol")
            or str(id_plantel) != str(target_user.get("id_plantel_asignado"))
        ):
            form_error = "No puedes cambiar tu propio rol o alcance durante la sesión."
        else:
            payload = {
                "nombre": form_values["nombre"],
                "apellido": form_values["apellido"],
                "correo": form_values["correo"],
                "rol": form_values["rol"],
                "id_plantel_asignado": id_plantel,
            }
            if password:
                payload["password"] = password
            try:
                updated_user = IAMClient.update_user(user_id, payload, session["iam_token"])
            except IAMAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (IAMValidationError, IAMUnavailableError) as error:
                form_error = str(error)
            else:
                if is_self:
                    session["iam_user"] = {**current_user, **updated_user}
                flash(f"El usuario {updated_user['correo']} se actualizó correctamente.", "success")
                return redirect(url_for("admin.usuarios"))

    return render_template(
        "admin/usuario-form.html",
        active_page="usuarios",
        breadcrumb="Administración / Usuarios / Editar",
        page_title="Editar usuario",
        header_status="IAM conectado" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.usuarios"),
        sidebar_title="Edición de cuenta",
        sidebar_description="Actualización administrativa conectada con IAM.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        form_values=form_values,
        form_error=form_error,
        available_roles=_available_user_roles(),
        is_edit=True,
        form_action=url_for("admin.usuario_edit", user_id=user_id),
        lock_scope_fields=str(current_user.get("id_usuario")) == str(user_id),
        requires_plantel=current_user.get("rol") == "ADMIN_PLANTEL",
        target_user=target_user,
    )


@admin_bp.post("/usuarios/<int:user_id>/desactivar")
def usuario_deactivate(user_id):
    """Solicita a IAM la baja lógica de una cuenta administrable."""
    current_user = session.get("iam_user", {})
    if str(current_user.get("id_usuario")) == str(user_id):
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("admin.usuarios"))
    try:
        target_user = IAMClient.get_user(user_id, session["iam_token"])
        if not _can_manage_user(target_user):
            flash("No tienes permisos para desactivar ese usuario.", "error")
            return redirect(url_for("admin.usuarios"))
        IAMClient.deactivate_user(user_id, session["iam_token"])
    except IAMAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (IAMValidationError, IAMUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash("El usuario se desactivó correctamente.", "success")
    return redirect(url_for("admin.usuarios"))


@admin_bp.get("/horarios")
def horarios():
    """Muestra la cuadrícula administrativa obtenida desde Booking."""
    filters = {
        name: request.args.get(name)
        for name in BookingClient.FILTER_NAMES
        if request.args.get(name) not in {None, ""}
    }
    current_user = session.get("iam_user", {})
    allowed_room_ids = None
    schedule_error = None
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        if assigned_id is None:
            schedule_error = "La cuenta administrativa no tiene un plantel asignado."
        else:
            filters["id_plantel"] = assigned_id
            try:
                salon_records = CatalogClient.list_salones(active_only=False)
            except CatalogUnavailableError as error:
                schedule_error = (
                    "No se pudo validar el alcance del plantel con Catalog. "
                    f"{error}"
                )
            else:
                allowed_room_ids = {
                    str(record.get("id_salon"))
                    for record in salon_records
                    if str(record.get("id_plantel")) == str(assigned_id)
                    and record.get("id_salon") is not None
                }

    schedule_records = []
    if schedule_error is None:
        try:
            schedule_records = BookingClient.list_schedule(filters)
        except BookingUnavailableError as error:
            schedule_error = str(error)
        else:
            if allowed_room_ids is not None:
                schedule_records = [
                    record
                    for record in schedule_records
                    if str(record.get("id_salon")) in allowed_room_ids
                ]

    rooms = {
        record.get("id_salon")
        for record in schedule_records
        if record.get("id_salon") is not None
    }
    morning_count = 0
    afternoon_count = 0
    for record in schedule_records:
        try:
            start_hour = int(str(record.get("hora_inicio", "")).split(":", 1)[0])
        except (TypeError, ValueError):
            continue
        if 7 <= start_hour <= 13:
            morning_count += 1
        elif 16 <= start_hour <= 21:
            afternoon_count += 1

    return render_template(
        "admin/horarios.html",
        active_page="horarios",
        breadcrumb="Administración / Horarios",
        page_title="Gestión de horarios",
        header_status="Booking conectado" if schedule_error is None else "Consulta no disponible",
        body_schedule_view="admin",
        schedule_records=schedule_records,
        schedule_error=schedule_error,
        filter_values=filters,
        schedule_metrics={
            "total": len(schedule_records),
            "rooms": len(rooms),
            "morning": morning_count,
            "afternoon": afternoon_count,
        },
    )


@admin_bp.get("/horarios/historial")
def horario_history():
    """Muestra el historial autenticado y limita el alcance administrativo."""
    filter_values = {
        "estado": request.args.get("estado", "").strip().upper(),
        "id_salon": request.args.get("id_salon", "").strip(),
        "fecha_reserva": request.args.get("fecha_reserva", "").strip(),
        "id_usuario": request.args.get("id_usuario", "").strip(),
    }
    service_errors = []
    can_query = True
    history_filters = {}
    valid_states = {"APROBADA", "APARTADA", "PENDIENTE", "RECHAZADA", "DESPLAZADA", "CANCELADA"}

    if filter_values["estado"]:
        if filter_values["estado"] in valid_states:
            history_filters["estado"] = filter_values["estado"]
        else:
            service_errors.append("El estado seleccionado no es válido.")
            can_query = False
    if filter_values["id_salon"]:
        try:
            history_filters["id_salon"] = int(filter_values["id_salon"])
        except (TypeError, ValueError):
            service_errors.append("El identificador del salón no es válido.")
            can_query = False
    if filter_values["id_usuario"]:
        try:
            history_filters["id_usuario"] = int(filter_values["id_usuario"])
        except (TypeError, ValueError):
            service_errors.append("El identificador del usuario no es válido.")
            can_query = False
    if filter_values["fecha_reserva"]:
        try:
            date.fromisoformat(filter_values["fecha_reserva"])
        except (TypeError, ValueError):
            service_errors.append("La fecha seleccionada no es válida.")
            can_query = False
        else:
            history_filters["fecha_reserva"] = filter_values["fecha_reserva"]

    plantel_records = []
    salon_records = []
    catalog_available = True
    try:
        plantel_records = CatalogClient.list_planteles(active_only=False)
        salon_records = CatalogClient.list_salones(active_only=False)
    except CatalogUnavailableError as error:
        catalog_available = False
        service_errors.append(str(error))

    current_user = session.get("iam_user", {})
    allowed_room_ids = None
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        if assigned_id is None:
            service_errors.append("La cuenta administrativa no tiene un plantel asignado.")
            can_query = False
            plantel_records = []
            salon_records = []
        elif not catalog_available:
            service_errors.append("No se pudo validar el alcance del plantel.")
            can_query = False
        else:
            plantel_records = [
                record
                for record in plantel_records
                if str(record.get("id")) == str(assigned_id)
            ]
            salon_records = [
                record
                for record in salon_records
                if str(record.get("id_plantel")) == str(assigned_id)
            ]
            allowed_room_ids = {
                str(record.get("id_salon"))
                for record in salon_records
                if record.get("id_salon") is not None
            }

    history_records = []
    if can_query:
        try:
            history_records = BookingClient.list_history(
                history_filters,
                session["iam_token"],
            )
        except BookingAuthorizationError as error:
            if error.status_code == 401:
                session.clear()
                return redirect(url_for("public.login"))
            service_errors.append(str(error))
        except (BookingValidationError, BookingUnavailableError) as error:
            service_errors.append(str(error))
        else:
            if allowed_room_ids is not None:
                history_records = [
                    record
                    for record in history_records
                    if str(record.get("id_salon")) in allowed_room_ids
                ]

    state_counts = {
        state: sum(1 for record in history_records if record.get("estado") == state)
        for state in valid_states
    }
    return render_template(
        "admin/horario-history.html",
        active_page="horarios",
        breadcrumb="Administración / Horarios / Historial",
        page_title="Historial de reservas",
        header_status="Booking conectado" if not service_errors else "Consulta parcial",
        back_url=url_for("admin.horarios"),
        history_records=history_records,
        planteles=plantel_records,
        salones=salon_records,
        filter_values=filter_values,
        service_errors=service_errors,
        state_counts=state_counts,
    )


@admin_bp.post("/horarios/<int:id_peticion>/cancelar")
def horario_cancel(id_peticion):
    """Delega en Booking la cancelación autenticada de una reserva."""
    return_filters = {
        name: request.args.get(name, "").strip()
        for name in ("estado", "id_salon", "fecha_reserva", "id_usuario")
        if request.args.get(name, "").strip()
    }

    try:
        result = BookingClient.cancel_booking(id_peticion, session["iam_token"])
    except BookingAuthorizationError as error:
        if error.status_code == 401:
            session.clear()
            return redirect(url_for("public.login"))
        flash(str(error), "error")
    except (BookingValidationError, BookingUnavailableError) as error:
        flash(str(error), "error")
    else:
        flash(
            result.get("message", f"La reserva #{id_peticion} se canceló correctamente."),
            "success",
        )

    return redirect(url_for("admin.horario_history", **return_filters))


@admin_bp.route("/horarios/nuevo", methods=["GET", "POST"])
def horario_new():
    """Captura una reserva y delega prioridad y colisiones a Booking."""
    form_values = _edit_booking_form_values()
    plantel_records, salon_records, program_records, form_error = (
        _booking_form_catalogs()
    )

    current_user = session.get("iam_user", {})
    assigned_id = current_user.get("id_plantel_asignado")
    if (
        request.method == "GET"
        and current_user.get("rol") == "ADMIN_PLANTEL"
        and assigned_id is not None
        and len(plantel_records) == 1
    ):
        form_values["id_plantel"] = str(assigned_id)

    if request.method == "POST" and form_error is None:
        payload, form_error = validated_booking_payload(
            form_values,
            plantel_records,
            salon_records,
            program_records,
        )
        if payload is not None:
            try:
                result = BookingClient.create_booking(payload, session["iam_token"])
            except BookingAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (BookingValidationError, BookingUnavailableError) as error:
                form_error = str(error)
            else:
                flash(result.get("message", "La reserva se registró correctamente."), "success")
                return redirect(url_for("admin.horarios"))

    return render_template(
        "admin/horario-form.html",
        active_page="horarios",
        breadcrumb="Administración / Horarios / Nueva reserva",
        page_title="Registrar reserva",
        header_status="Servicios conectados" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.horarios"),
        sidebar_title="Nueva reserva",
        sidebar_description="Solicitud administrativa conectada con Booking.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=plantel_records,
        salones=salon_records,
        programas=program_records,
        booking_slots=BOOKING_SLOTS,
        event_types=BOOKING_EVENT_TYPES,
        form_values=form_values,
        form_error=form_error,
    )


def _edit_booking_form_values():
    return {
        "id_plantel": request.form.get("id_plantel", "").strip(),
        "id_salon": request.form.get("id_salon", "").strip(),
        "id_programa": request.form.get("id_programa", "").strip(),
        "materia_nombre": request.form.get("materia_nombre", "").strip(),
        "fecha_reserva": request.form.get("fecha_reserva", "").strip(),
        "bloque": request.form.get("bloque", "").strip(),
        "id_tipo_evento": request.form.get("id_tipo_evento", "").strip(),
        "numero_alumnos": request.form.get("numero_alumnos", "").strip(),
        "observaciones": request.form.get("observaciones", "").strip(),
    }


def _booking_form_catalogs():
    """Carga opciones de formulario respetando el alcance administrativo."""
    try:
        planteles = CatalogClient.list_planteles(active_only=True)
        salones = CatalogClient.list_salones(active_only=True)
        programas = CatalogClient.list_programas(active_only=True)
    except CatalogUnavailableError as error:
        return [], [], [], str(error)
    current_user = session.get("iam_user", {})
    if current_user.get("rol") == "ADMIN_PLANTEL":
        assigned_id = current_user.get("id_plantel_asignado")
        if assigned_id is None:
            return [], [], programas, "La cuenta administrativa no tiene un plantel asignado."
        planteles = [
            record for record in planteles
            if str(record.get("id")) == str(assigned_id)
        ]
        salones = [
            record for record in salones
            if str(record.get("id_plantel")) == str(assigned_id)
        ]
    return planteles, salones, programas, None


@admin_bp.route("/horarios/<int:id_peticion>/editar", methods=["GET", "POST"])
def horario_edit(id_peticion):
    """Consulta y reprograma una reserva mediante Booking."""
    planteles, salones, programas, form_error = _booking_form_catalogs()
    if request.method == "POST":
        form_values = _edit_booking_form_values()
    else:
        try:
            booking = BookingClient.get_booking(id_peticion, session["iam_token"])
        except BookingAuthorizationError as error:
            if error.status_code == 401:
                session.clear()
                return redirect(url_for("public.login"))
            flash(str(error), "error")
            return redirect(url_for("admin.horario_history"))
        except (BookingValidationError, BookingUnavailableError) as error:
            flash(str(error), "error")
            return redirect(url_for("admin.horario_history"))

        selected_salon = next(
            (
                salon for salon in salones
                if str(salon.get("id_salon")) == str(booking.get("id_salon"))
            ),
            None,
        )
        form_values = {
            "id_plantel": str(selected_salon.get("id_plantel")) if selected_salon else "",
            "id_salon": str(booking.get("id_salon") or ""),
            "id_programa": str(booking.get("id_programa") or ""),
            "materia_nombre": booking.get("materia_nombre") or "",
            "fecha_reserva": booking.get("fecha_reserva") or booking.get("fecha") or "",
            "bloque": (
                f"{str(booking.get('hora_inicio') or '')[:5]}|"
                f"{str(booking.get('hora_fin') or '')[:5]}"
            ),
            "id_tipo_evento": str(booking.get("id_tipo_evento") or ""),
            "numero_alumnos": str(booking.get("numero_alumnos") or ""),
            "observaciones": booking.get("observaciones") or "",
        }
        if selected_salon is None and form_error is None:
            form_error = "El salón actual ya no está disponible en Catalog."

    if request.method == "POST" and form_error is None:
        payload, form_error = validated_booking_payload(
            form_values,
            planteles,
            salones,
            programas,
        )
        if payload is not None:
            try:
                result = BookingClient.update_booking(
                    id_peticion,
                    payload,
                    session["iam_token"],
                )
            except BookingAuthorizationError as error:
                if error.status_code == 401:
                    session.clear()
                    return redirect(url_for("public.login"))
                form_error = str(error)
            except (BookingValidationError, BookingUnavailableError) as error:
                form_error = str(error)
            else:
                flash(result.get("message", "La reserva se actualizó correctamente."), "success")
                return redirect(url_for("admin.horario_history"))

    return render_template(
        "admin/horario-form.html",
        active_page="horarios",
        breadcrumb=f"Administración / Horarios / Editar #{id_peticion}",
        page_title="Editar reserva",
        header_status="Servicios conectados" if form_error is None else "Revisa el formulario",
        header_status_class="form-preview-badge",
        show_header_status_dot=False,
        back_url=url_for("admin.horario_history"),
        sidebar_title=f"Reserva #{id_peticion}",
        sidebar_description="Reprogramación protegida por IAM y procesada por Booking.",
        show_mobile_nav=False,
        show_sidebar_user=False,
        planteles=planteles,
        salones=salones,
        programas=programas,
        booking_slots=BOOKING_SLOTS,
        event_types=BOOKING_EVENT_TYPES,
        form_values=form_values,
        form_error=form_error,
        form_mode="edit",
        form_action=url_for("admin.horario_edit", id_peticion=id_peticion),
    )
