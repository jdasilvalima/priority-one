"""The fake Salesforce, Gong, Clay and payments exports, served over HTTP."""

import pytest
from fastapi.testclient import TestClient

from app.fake_sources import app
from app.sources import SOURCE_NAMES, load_raw

client = TestClient(app)


@pytest.mark.parametrize("source", SOURCE_NAMES)
def test_each_source_serves_its_export(source):
    response = client.get(f"/{source}")
    assert response.status_code == 200
    assert response.json() == load_raw()[source]


def test_unknown_source_is_404():
    assert client.get("/hubspot").status_code == 404


def test_a_path_cannot_leave_the_data_folder():
    assert client.get("/..%2Fconfig%2Fplaybook").status_code == 404


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
