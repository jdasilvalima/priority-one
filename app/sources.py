"""Read the 5 JSON files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_raw() -> dict:
    return {name: _read(ROOT / "data" / f"{name}.json") for name in ("salesforce", "gong", "clay", "payments")}


def load_playbook() -> dict:
    return _read(ROOT / "config" / "playbook.json")
