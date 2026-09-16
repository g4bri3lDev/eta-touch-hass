"""Tests for selects."""

from unittest.mock import MagicMock

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import WW_PRIORITY, enable_entity, setup_integration


async def test_select(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = await enable_entity(hass, "select", config_entry, WW_PRIORITY)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "Hoch"
    assert state.attributes["options"] == ["Niedrig", "Mittel", "Hoch"]

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "Mittel"},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(WW_PRIORITY, "Mittel")
