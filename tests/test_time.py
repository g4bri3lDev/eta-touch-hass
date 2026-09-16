"""Tests for time entities and the duration number."""

from datetime import time
from unittest.mock import MagicMock

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.time import (
    DOMAIN as TIME_DOMAIN,
    SERVICE_SET_VALUE as SET_TIME,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TIME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import (
    QUIET_DURATION,
    SUCTION_TIME,
    enable_entity,
    entity_id_for,
    setup_integration,
)


async def test_time_entity(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = entity_id_for(hass, "time", config_entry, SUCTION_TIME)
    assert hass.states.get(entity_id).state == "20:00:00"
    await hass.services.async_call(
        TIME_DOMAIN,
        SET_TIME,
        {ATTR_ENTITY_ID: entity_id, ATTR_TIME: time(5, 30)},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(SUCTION_TIME, 330)


async def test_duration_number_in_minutes(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = await enable_entity(hass, "number", config_entry, QUIET_DURATION)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "600.0"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["max"] == 720.0
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 480},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(QUIET_DURATION, 28800.0)
