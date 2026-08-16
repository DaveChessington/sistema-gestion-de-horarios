"""Rutas públicas del frontend."""

from flask import Blueprint, redirect, render_template, url_for


public_bp = Blueprint("public", __name__)


@public_bp.get("/login")
def login():
    """Muestra el acceso institucional sin autenticar todavía contra IAM."""
    return render_template("public/login.html")


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
    """Muestra la consulta pública utilizando la vista visual existente."""
    return render_template("public/horarios.html")


@public_bp.get("/")
def home():
    """Usa el login como punto de entrada del módulo frontend."""
    return redirect(url_for("public.login"))
