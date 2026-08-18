#!/bin/sh
set -e

echo "=== Booking Microservice: Running DB Migrations ==="
export PYTHONPATH=/app
export FLASK_APP=booking.app:create_app

flask db upgrade -d /app/booking/migrations || {
    echo "Warning: flask db upgrade failed, attempting auto migration..."
    flask db migrate -d /app/booking/migrations -m "Auto migration" 2>/dev/null || true
    flask db upgrade -d /app/booking/migrations
}

echo "=== Booking Microservice: Starting Server ==="
exec python /app/booking/run.py
