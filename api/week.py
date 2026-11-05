"""GET /api/week: the only route. The browser never talks to the database."""

import os
import sys
from pathlib import Path

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import read_rows, snapshot_from_rows  # noqa: E402
from app.sources import load_playbook  # noqa: E402
from app.week import DEMO_NOW, render_week  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/week")
def week():
    try:
        snapshot = snapshot_from_rows(read_rows(os.environ["DATABASE_URL_READONLY"]))
    except (KeyError, IndexError, psycopg.Error) as error:
        # Only the error type: the message of a connection error can contain the address.
        print(f"week unavailable: {type(error).__name__}")
        return JSONResponse({"error": "The week is not available."}, status_code=503)
    return render_week(snapshot, DEMO_NOW, load_playbook())
