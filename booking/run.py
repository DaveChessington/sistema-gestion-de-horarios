import os
import sys

# Agregar la raíz del proyecto al sys.path para permitir imports absolutos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from booking.app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('BOOKING_PORT', 5003))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 't']
    app.run(host=host, port=port, debug=debug)
