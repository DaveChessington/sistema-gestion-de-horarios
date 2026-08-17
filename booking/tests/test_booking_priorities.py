import requests
import jwt
import datetime

# Configuration
BOOKING_API_URL = "http://127.0.0.1:5003/api/v1/booking/request"
JWT_SECRET_KEY = "secret-key-booking-udl" # From config.py fallback

def generate_token(id_usuario, rol):
    payload = {
        'id_usuario': id_usuario,
        'rol': rol,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def main():
    print("--- Iniciando Prueba de Prioridades y Desplazamiento ---")
    
    # 1. Alumno realiza una reserva (Baja prioridad P = 10 (Alumno) + 10 (Estudio) = 20)
    token_alumno = generate_token(id_usuario=100, rol='ALUMNO')
    headers_alumno = {'Authorization': f'Bearer {token_alumno}', 'Content-Type': 'application/json'}
    
    payload_alumno = {
        'id_salon': 1, # Asumiendo que el salon 1 existe en catalog
        'fecha_reserva': '2026-11-20',
        'hora_inicio': '14:00',
        'hora_fin': '16:00',
        'id_tipo_evento': 4, # Sesión de Estudio
        'observaciones': 'Estudio para examen final'
    }
    
    print("\n[1] Intentando registrar reserva para Alumno...")
    res_alumno = requests.post(BOOKING_API_URL, json=payload_alumno, headers=headers_alumno)
    print(f"Status: {res_alumno.status_code}")
    print(res_alumno.json())
    
    # 2. Docente realiza reserva en el mismo horario (Alta prioridad P = 40 (Docente) + 50 (Clase) = 90)
    token_docente = generate_token(id_usuario=200, rol='DOCENTE')
    headers_docente = {'Authorization': f'Bearer {token_docente}', 'Content-Type': 'application/json'}
    
    payload_docente = {
        'id_salon': 1,
        'id_programa': 5,
        'materia_nombre': 'Arquitectura de Software',
        'fecha_reserva': '2026-11-20',
        'hora_inicio': '14:00',
        'hora_fin': '16:00',
        'id_tipo_evento': 1, # Clase Curricular
        'observaciones': 'Clase de reposición'
    }
    
    print("\n[2] Intentando registrar reserva para Docente (Alta prioridad) en el mismo horario...")
    res_docente = requests.post(BOOKING_API_URL, json=payload_docente, headers=headers_docente)
    print(f"Status: {res_docente.status_code}")
    print(res_docente.json())
    
    # 3. Otro Alumno intenta registrar reserva (Baja prioridad, igual a la primera)
    # Debería ser rechazado por FIFO frente a la del docente, o si fuera contra el primer alumno, también rechazado.
    token_alumno2 = generate_token(id_usuario=101, rol='ALUMNO')
    headers_alumno2 = {'Authorization': f'Bearer {token_alumno2}', 'Content-Type': 'application/json'}
    
    print("\n[3] Intentando registrar reserva para otro Alumno (Menor prioridad que el Docente)...")
    res_alumno2 = requests.post(BOOKING_API_URL, json=payload_alumno, headers=headers_alumno2)
    print(f"Status: {res_alumno2.status_code}")
    print(res_alumno2.json())
    
    # 4. Validar id_salon inexistente
    print("\n[4] Intentando registrar reserva en un salón inexistente...")
    payload_invalido = payload_docente.copy()
    payload_invalido['id_salon'] = 9999
    res_invalido = requests.post(BOOKING_API_URL, json=payload_invalido, headers=headers_docente)
    print(f"Status: {res_invalido.status_code}")
    print(res_invalido.json())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error ejecutando pruebas: {e}")
