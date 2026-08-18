#!/bin/sh
set -e

echo "=== IAM Microservice: Running DB Migrations ==="
export PYTHONPATH=/app
export FLASK_APP=run.py

flask db upgrade || {
    echo "Warning: flask db upgrade failed, attempting auto migration..."
    flask db migrate -m "Auto migration" 2>/dev/null || true
    flask db upgrade
}

echo "=== IAM Microservice: Starting Server ==="
exec python run.py
