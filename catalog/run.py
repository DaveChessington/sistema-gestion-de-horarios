import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from catalog.app import create_app

app = create_app()

if __name__ == '__main__':
    port = 5002  # int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=os.environ.get('HOST', '0.0.0.0'), port=port, debug=os.environ.get('DEBUG', False))
