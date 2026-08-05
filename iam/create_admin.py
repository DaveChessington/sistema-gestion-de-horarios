import sys
from app import create_app
from app.services.auth_service import AuthService

app = create_app()

def main():
    correo = sys.argv[1] if len(sys.argv) > 1 else "admin@udl.edu.mx"
    password = sys.argv[2] if len(sys.argv) > 2 else "password123"
    nombre = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    apellido = sys.argv[4] if len(sys.argv) > 4 else "Sistema"

    with app.app_context():
        datos = {
            "nombre": nombre,
            "apellido": apellido,
            "correo": correo,
            "password": password,
            "rol": "COORDINADOR"
        }
        res = AuthService.register_user(datos)
        if res['success']:
            print(f"OK: Usuario administrador '{correo}' creado exitosamente.")
        else:
            print(f"ERROR: {res['error']}")

if __name__ == '__main__':
    main()
