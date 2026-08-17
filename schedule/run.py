"""Punto de entrada local para el frontend Flask/Jinja2."""

import os
import sys
import webbrowser
from pathlib import Path
from threading import Timer


# Permite ejecutar tanto `python schedule/run.py` como `python -m schedule.run`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schedule.app import create_app


app = create_app()


if __name__ == "__main__":
    host = app.config["HOST"]
    port = app.config["PORT"]
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    should_open_browser = app.config["OPEN_BROWSER"] and (
        not app.config["DEBUG"] or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    )
    if should_open_browser:
        browser_timer = Timer(
            1.0,
            webbrowser.open,
            args=[f"http://{browser_host}:{port}/login"],
        )
        browser_timer.daemon = True
        browser_timer.start()

    app.run(
        host=host,
        port=port,
        debug=app.config["DEBUG"],
    )
