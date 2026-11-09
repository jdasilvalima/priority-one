"""The scoring page and the tour are the same in the demo and in the platform."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
DEMO = ROOT / "demo"
PLATFORM = ROOT / "platform" / "web"


@pytest.mark.parametrize("file", ["Tour.jsx", "Scoring.jsx"])
def test_file_is_identical_in_both_folders(file):
    demo = (DEMO / "src" / file).read_text(encoding="utf-8")
    assert demo == (PLATFORM / "src" / file).read_text(encoding="utf-8")


def test_both_folders_pin_the_same_tour_library():
    versions = [json.loads((folder / "package.json").read_text(encoding="utf-8"))["dependencies"]["driver.js"]
                for folder in (DEMO, PLATFORM)]
    assert versions[0] == versions[1]
    assert versions[0][0].isdigit(), "pin an exact version, not a range"


@pytest.mark.parametrize("folder", [DEMO, PLATFORM], ids=["demo", "platform"])
def test_menu_can_restart_the_tour(folder):
    app = (folder / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "href={TOUR_HASH}" in app
    assert "Take the tour" in app
