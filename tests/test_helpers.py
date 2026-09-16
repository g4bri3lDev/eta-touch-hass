"""Tests for helpers."""

from homeassistant.core import HomeAssistant
from pyetatouch import VarAddress

from custom_components.eta_touch.helpers import variable_unique_id, varset_name


async def test_varset_name(hass: HomeAssistant) -> None:
    first = await varset_name(hass, "entry1")
    assert first == await varset_name(hass, "entry1")
    assert first != await varset_name(hass, "entry2")
    assert first.startswith("ha")
    assert len(first) == 12
    assert first.isalnum()


def test_variable_unique_id() -> None:
    address = VarAddress(40, 10021, 0, 11109, 0)
    assert variable_unique_id("abc", address) == "abc_40_10021_0_11109_0"
