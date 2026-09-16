"""Tests for selects."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.eta_touch.const import DOMAIN
from custom_components.eta_touch.helpers import variable_unique_id

from . import (
    HK_AUTO,
    HK_HEAT,
    WW_PRIORITY,
    enable_entity,
    entity_id_for,
    setup_integration,
    value,
)
from .conftest import FakeVarSet


async def test_select(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = await enable_entity(hass, "select", config_entry, WW_PRIORITY)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "high"
    assert state.attributes["options"] == ["low", "medium", "high"]

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "medium"},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(WW_PRIORITY, 1972)


async def test_mode_select(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
    varset: FakeVarSet,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = entity_id_for(hass, "select", config_entry, "120_10101_mode")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "auto"
    assert state.attributes["options"] == ["auto", "heating", "setback"]

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "heating"},
        blocking=True,
    )
    mock_client.write.assert_awaited_once_with(HK_HEAT, 1803)

    varset.raw_values[HK_AUTO] = value(HK_AUTO, 1802.0, "Aus", offset=1802)
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_mode_buttons_are_not_separate_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await setup_integration(hass, config_entry)
    registry = er.async_get(hass)
    for platform in ("switch", "sensor", "select"):
        assert (
            registry.async_get_entity_id(
                platform, DOMAIN, variable_unique_id(config_entry.entry_id, HK_AUTO)
            )
            is None
        )
