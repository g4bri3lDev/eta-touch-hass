"""Tests for sensors, fault entities and events."""

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from pyetatouch import EtaFault, EtaWebserviceUnavailableError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.eta_touch.const import (
    DOMAIN,
    EVENT_ERROR_CLEARED,
    EVENT_ERROR_RAISED,
)
from custom_components.eta_touch.coordinator import webservice_issue_id

from . import (
    BOILER_STATE,
    BOILER_TEMP,
    HK_FLOW_MINUS,
    HK_OUTDOOR,
    HOURS,
    TOTAL,
    entity_id_for,
    setup_integration,
)
from .conftest import FakeVarSet

FAULT = EtaFault(
    40,
    10021,
    "Kessel",
    "Abgasfühler",
    "Error",
    datetime(2026, 9, 16, 12, 0),
    "Fühler defekt",
)


async def test_sensor_states(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: object
) -> None:
    await setup_integration(hass, config_entry)

    temp = hass.states.get(entity_id_for(hass, "sensor", config_entry, BOILER_TEMP))
    assert temp is not None
    assert temp.state == "60.0"
    assert temp.attributes["unit_of_measurement"] == "°C"
    assert temp.attributes["device_class"] == SensorDeviceClass.TEMPERATURE

    state = hass.states.get(entity_id_for(hass, "sensor", config_entry, BOILER_STATE))
    assert state is not None
    assert state.state == "ready"
    assert state.attributes["options"] == ["off", "ready"]

    total = hass.states.get(entity_id_for(hass, "sensor", config_entry, TOTAL))
    assert total is not None
    assert total.state == "17000.0"
    assert total.attributes["state_class"] == SensorStateClass.TOTAL_INCREASING

    hours = hass.states.get(entity_id_for(hass, "sensor", config_entry, HOURS))
    assert hours is not None
    assert hours.attributes["unit_of_measurement"] == "h"
    assert float(hours.state) == 10.0


async def test_disabled_by_default(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: object
) -> None:
    await setup_integration(hass, config_entry)
    registry = er.async_get(hass)
    for address in (HK_OUTDOOR, HK_FLOW_MINUS):
        entry = registry.async_get(entity_id_for(hass, "sensor", config_entry, address))
        assert entry is not None
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    read_only_setting = registry.async_get(
        entity_id_for(hass, "sensor", config_entry, HK_FLOW_MINUS)
    )
    assert read_only_setting is not None
    assert read_only_setting.entity_category is EntityCategory.DIAGNOSTIC


async def test_unavailable_raises_issue_and_recovers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration(hass, config_entry)
    entity_id = entity_id_for(hass, "sensor", config_entry, BOILER_TEMP)
    issues = ir.async_get(hass)

    varset.error = EtaWebserviceUnavailableError("refused")
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert issues.async_get_issue(DOMAIN, webservice_issue_id(config_entry)) is not None

    varset.error = None
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "60.0"
    assert issues.async_get_issue(DOMAIN, webservice_issue_id(config_entry)) is None


async def test_fault_entities_and_events(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup_integration(hass, config_entry)
    problem = entity_id_for(hass, "binary_sensor", config_entry, "problem")
    active = entity_id_for(hass, "sensor", config_entry, "active_errors")
    assert hass.states.get(problem).state == STATE_OFF
    assert hass.states.get(active).state == "0"

    raised = async_capture_events(hass, EVENT_ERROR_RAISED)
    cleared = async_capture_events(hass, EVENT_ERROR_CLEARED)
    mock_client.errors.return_value = [FAULT]
    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(problem).state == STATE_ON
    state = hass.states.get(active)
    assert state.state == "1"
    assert state.attributes["errors"][0]["message"] == "Abgasfühler"
    assert len(raised) == 1
    assert raised[0].data["component"] == "Kessel"
    assert raised[0].data["time"] == "2026-09-16T12:00:00"

    mock_client.errors.return_value = []
    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(cleared) == 1
