"""The API behind the page. The browser reaches it through the web server, never the database."""

import os
import time
from typing import Literal

import psycopg
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import auth, db
from app.clock import scoring_now, week_key
from app.sources import load_playbook
from app.week import apply_actions, render_week

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
COOKIE = "session"


class Login(BaseModel):
    password: str = Field(max_length=200)


class Action(BaseModel):
    kind: Literal["logged", "snoozed", "flagged"]
    reason: str | None = Field(default=None, min_length=1, max_length=200)


@app.exception_handler(psycopg.Error)
@app.exception_handler(db.NoRunYet)
def unavailable(request: Request, error: Exception) -> JSONResponse:
    # Only the error type: the message of a connection error can name the host and the login.
    print(f"week unavailable: {type(error).__name__}", flush=True)
    return JSONResponse({"error": "The week is not available."}, status_code=503)


def require_session(session: str | None = Cookie(default=None)) -> None:
    if not session or not auth.is_valid(session, os.environ["SESSION_SECRET"], time.time()):
        raise HTTPException(status_code=401, detail="Sign in first.")


@app.get("/api/health")
def health() -> dict:
    with db.connect() as connection:
        if db.latest_run(connection) is None:
            raise db.NoRunYet
    return {"status": "ok"}


@app.post("/api/login", status_code=204)
def login(body: Login, response: Response) -> None:
    if not auth.password_matches(body.password, os.environ["APP_PASSWORD"]):
        raise HTTPException(status_code=401, detail="Wrong password.")
    response.set_cookie(
        COOKIE,
        auth.new_token(os.environ["SESSION_SECRET"], time.time()),
        max_age=auth.LIFETIME,
        httponly=True,
        samesite="strict",
        secure=os.environ.get("COOKIE_SECURE", "").lower() == "true",
    )


@app.post("/api/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE)


@app.get("/api/week", dependencies=[Depends(require_session)])
def week() -> dict:
    now = scoring_now()
    with db.connect() as connection:
        rows = db.read_rows(connection)
        actions = db.read_actions(connection, week_key(now))
    return apply_actions(render_week(db.snapshot_from_rows(rows), now, load_playbook()), actions)


@app.post("/api/accounts/{account_id}/actions", status_code=204, dependencies=[Depends(require_session)])
def save_action(account_id: str, action: Action) -> None:
    if action.kind == "flagged" and action.reason is None:
        raise HTTPException(status_code=422, detail="A reason is required.")
    with db.connect() as connection:
        saved = db.save_action(connection, account_id, week_key(scoring_now()), action.kind, action.reason)
    if not saved:
        raise HTTPException(status_code=404, detail="Unknown account.")


@app.delete("/api/accounts/{account_id}/snooze", status_code=204, dependencies=[Depends(require_session)])
def undo_snooze(account_id: str) -> None:
    with db.connect() as connection:
        db.undo_snooze(connection, account_id, week_key(scoring_now()))
