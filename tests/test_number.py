"""Tests for numbers."""

from unittest.mock import MagicMock

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pyetatouch import EtaValueError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import HK_OFFSET, WW_TARGET, entity_id_for, setup_integration


async def test_number_attributes_and_write(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = entity_id_for(hass, "number", config_entry, WW_TARGET)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "50.0"
    assert state.attributes["min"] == 0.0
    assert state.attributes["max"] == 90.0
    assert state.attributes["step"] == 0.1
    assert state.attributes["unit_of_measurement"] == "°C"

    offset = hass.states.get(entity_id_for(hass, "number", config_entry, HK_OFFSET))
    assert offset is not None
    assert offset.attributes["min"] == -100.0

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 55},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(WW_TARGET, 55.0)


async def test_number_write_error(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    mock_client.write.side_effect = EtaValueError(400, "Value is out of range.")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: entity_id_for(hass, "number", config_entry, WW_TARGET),
                ATTR_VALUE: 55,
            },
            blocking=True,
        )
