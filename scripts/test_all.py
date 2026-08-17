"""Ejecuta las suites en procesos aislados para evitar colisiones de paquetes."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("iam", "catalog", "booking", "schedule")


def main():
    failures = []
    for service in SERVICES:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT)
        print(f"\n=== {service.upper()} ===", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q"],
            cwd=ROOT / service,
            env=environment,
            check=False,
        )
        if result.returncode:
            failures.append(service)
    if failures:
        print(f"\nSuites con fallos: {', '.join(failures)}")
        return 1
    print("\nTodas las suites finalizaron correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
