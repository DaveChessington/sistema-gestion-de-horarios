#!/bin/sh
set -e

echo "=== Catalog Microservice: Running DB Migrations ==="
export PYTHONPATH=/app
export FLASK_APP=catalog.app:create_app

flask db upgrade -d /app/catalog/migrations || {
    echo "Warning: flask db upgrade failed, attempting auto migration..."
    flask db migrate -d /app/catalog/migrations -m "Auto migration" 2>/dev/null || true
    flask db upgrade -d /app/catalog/migrations
}

echo "=== Catalog Microservice: Starting Server ==="
exec python /app/catalog/run.py
