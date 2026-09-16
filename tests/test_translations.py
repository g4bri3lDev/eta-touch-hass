"""Every catalog key has metadata and translations."""

import json
from pathlib import Path
from typing import Any

from pyetatouch import CATALOG, Kind

from custom_components.eta_touch.descriptions import META

ROOT = Path(__file__).parent.parent / "custom_components" / "eta_touch"
PLATFORM_FOR_KIND = {
    Kind.SETTING: "number",
    Kind.SWITCH: "switch",
    Kind.SELECT: "select",
    Kind.ACTION: "button",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _shape(data: object) -> object:
    if isinstance(data, dict):
        return {key: _shape(value) for key, value in data.items()}
    return None


def test_strings_match_english() -> None:
    assert _load("strings.json") == _load("translations/en.json")


def test_german_has_same_keys() -> None:
    assert _shape(_load("translations/de.json")) == _shape(
        _load("translations/en.json")
    )


def test_catalog_keys_are_covered() -> None:
    entity = _load("translations/en.json")["entity"]
    for entry in CATALOG:
        assert entry.key in META, entry.key
        assert entry.key in entity["sensor"], entry.key
        if platform := PLATFORM_FOR_KIND.get(entry.kind):
            assert entry.key in entity[platform], entry.key
    assert "problem" in entity["binary_sensor"]
    assert "active_errors" in entity["sensor"]
    assert "rediscover" in entity["button"]
    assert set(entity["select"]["mode"]["state"]) == {"auto", "heat", "setback"}
