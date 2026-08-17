import click
from app.services.auth_service import AuthService

def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--correo", default="admin@udl.edu.mx", help="Correo del administrador")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Contraseña fuerte del administrador")
    @click.option("--nombre", default="Admin", help="Nombre del usuario")
    @click.option("--apellido", default="Sistema", help="Apellido del usuario")
    def create_admin(correo, password, nombre, apellido):
        """Crea un usuario administrador inicial."""
        datos = {
            "nombre": nombre,
            "apellido": apellido,
            "correo": correo,
            "password": password,
            "rol": "COORDINADOR"
        }
        resultado = AuthService.register_user(datos)
        if resultado['success']:
            click.echo(f"OK: Usuario administrador '{correo}' creado exitosamente.")
        else:
            click.echo(f"ERROR: {resultado['error']}")
