"""Stand-ins for Salesforce, Gong, Clay and the payments database, shaped like their exports."""

from fastapi import FastAPI, HTTPException

from app.sources import SOURCE_NAMES, read_source

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/{source}")
def export(source: str) -> dict:
    if source not in SOURCE_NAMES:
        raise HTTPException(status_code=404, detail="Unknown source.")
    return read_source(source)
