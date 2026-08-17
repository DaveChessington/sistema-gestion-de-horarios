"""Opciones y validaciones puras de los formularios administrativos."""

from datetime import date


USER_ROLE_OPTIONS = (
    ("COORDINADOR", "Coordinador"),
    ("ADMIN_PLANTEL", "Admin. plantel"),
    ("DOCENTE", "Docente"),
    ("ALUMNO", "Alumno"),
)

BOOKING_EVENT_TYPES = (
    {"id": 1, "name": "Clase Curricular"},
    {"id": 2, "name": "Evento Institucional"},
    {"id": 3, "name": "Conferencia / Taller"},
    {"id": 4, "name": "Sesión de Estudio (Grupal)"},
)

BOOKING_SLOTS = (
    ("07:00|07:50", "07:00 – 07:50", "Turno Matutino"),
    ("08:00|08:50", "08:00 – 08:50", "Turno Matutino"),
    ("09:00|09:50", "09:00 – 09:50", "Turno Matutino"),
    ("10:00|10:50", "10:00 – 10:50", "Turno Matutino"),
    ("11:00|11:50", "11:00 – 11:50", "Turno Matutino"),
    ("12:00|12:50", "12:00 – 12:50", "Turno Matutino"),
    ("13:00|13:50", "13:00 – 13:50", "Turno Matutino"),
    ("16:00|16:50", "16:00 – 16:50", "Turno Vespertino"),
    ("17:00|17:50", "17:00 – 17:50", "Turno Vespertino"),
    ("18:00|18:50", "18:00 – 18:50", "Turno Vespertino"),
    ("19:00|19:50", "19:00 – 19:50", "Turno Vespertino"),
    ("20:00|20:50", "20:00 – 20:50", "Turno Vespertino"),
    ("21:00|21:50", "21:00 – 21:50", "Turno Vespertino"),
)


def strong_password_error(password):
    """Replica en el formulario la política publicada por IAM."""
    if len(password) < 12:
        return "La contraseña debe tener al menos 12 caracteres."
    if len(password.encode("utf-8")) > 72:
        return "La contraseña no puede superar 72 bytes."
    if not any(character.isupper() for character in password):
        return "La contraseña debe incluir una letra mayúscula."
    if not any(character.islower() for character in password):
        return "La contraseña debe incluir una letra minúscula."
    if not any(character.isdigit() for character in password):
        return "La contraseña debe incluir un número."
    if not any(not character.isalnum() for character in password):
        return "La contraseña debe incluir un carácter especial."
    return None


def validated_booking_payload(form_values, planteles, salones, programas):
    """Valida el formulario y genera el contrato HTTP esperado por Booking."""
    try:
        plantel_id = int(form_values["id_plantel"])
    except (TypeError, ValueError):
        plantel_id = None
    try:
        salon_id = int(form_values["id_salon"])
    except (TypeError, ValueError):
        salon_id = None
    try:
        program_id = (
            int(form_values["id_programa"])
            if form_values["id_programa"]
            else None
        )
    except (TypeError, ValueError):
        program_id = 0
    try:
        event_type_id = int(form_values["id_tipo_evento"])
    except (TypeError, ValueError):
        event_type_id = None
    try:
        student_count = (
            int(form_values["numero_alumnos"])
            if form_values["numero_alumnos"]
            else None
        )
    except (TypeError, ValueError):
        student_count = 0

    valid_plantel_ids = {record.get("id") for record in planteles}
    valid_program_ids = {record.get("id_programa") for record in programas}
    allowed_salons = {
        record.get("id_salon"): record
        for record in salones
        if record.get("id_salon") is not None
    }
    selected_salon = allowed_salons.get(salon_id)
    valid_slots = {slot[0]: slot[0].split("|", 1) for slot in BOOKING_SLOTS}
    selected_slot = valid_slots.get(form_values["bloque"])
    valid_event_type_ids = {item["id"] for item in BOOKING_EVENT_TYPES}
    try:
        date.fromisoformat(form_values["fecha_reserva"])
        valid_date = True
    except (TypeError, ValueError):
        valid_date = False
    try:
        salon_capacity = int(selected_salon.get("capacidad", 0)) if selected_salon else 0
    except (TypeError, ValueError):
        salon_capacity = 0

    if plantel_id not in valid_plantel_ids:
        return None, "Selecciona un plantel activo permitido para tu cuenta."
    if selected_salon is None or str(selected_salon.get("id_plantel")) != str(
        plantel_id
    ):
        return None, "Selecciona un salón activo perteneciente al plantel indicado."
    if program_id is not None and program_id not in valid_program_ids:
        return None, "Selecciona un programa activo o deja el campo sin asignar."
    if not valid_date:
        return None, "Selecciona una fecha válida para la reserva."
    if selected_slot is None:
        return None, "Selecciona uno de los bloques de 50 minutos disponibles."
    if event_type_id not in valid_event_type_ids:
        return None, "Selecciona un tipo de evento válido."
    if student_count is not None and student_count <= 0:
        return None, "El número de alumnos debe ser mayor a cero."
    if student_count is not None and student_count > salon_capacity:
        return (
            None,
            f"La cantidad de alumnos excede la capacidad del salón ({salon_capacity}).",
        )
    return {
        "id_salon": salon_id,
        "id_programa": program_id,
        "materia_nombre": form_values["materia_nombre"] or None,
        "fecha_reserva": form_values["fecha_reserva"],
        "hora_inicio": selected_slot[0],
        "hora_fin": selected_slot[1],
        "id_tipo_evento": event_type_id,
        "numero_alumnos": student_count,
        "observaciones": form_values["observaciones"],
    }, None
