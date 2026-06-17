from __future__ import annotations

import os

os.environ.setdefault("FIELDVOICE_DB_PATH", "/tmp/fieldvoice.db")

from backend.app.main import app  # noqa: E402
