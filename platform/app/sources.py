"""Read the 4 source exports and the playbook."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_NAMES = ("salesforce", "gong", "clay", "payments")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_source(name: str) -> dict:
    return _read(ROOT / "data" / f"{name}.json")


def load_raw() -> dict:
    return {name: read_source(name) for name in SOURCE_NAMES}


def load_playbook() -> dict:
    return _read(ROOT / "config" / "playbook.json")
