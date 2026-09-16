"""Tests for diagnostics."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pyetatouch import EtaConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from . import setup_integration


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    await setup_integration(hass, config_entry)
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )
    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["entry"]["unique_id"] == "**REDACTED**"
    assert diagnostics["unknown_variables"] == [
        {"address": "40/10021/0/0/13987", "name": "Ein/Aus Taste anzeigen"}
    ]
    assert diagnostics["values"]["40/10021/0/11109/0"]["raw"] == 600.0
    assert diagnostics["varset"]["rejected"] == []
    assert diagnostics["faults"] == []


async def test_diagnostics_without_menu(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    await setup_integration(hass, config_entry)
    mock_client.menu.side_effect = EtaConnectionError("down")
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )
    assert diagnostics["unknown_variables"].startswith("unavailable")
