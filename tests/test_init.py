"""Tests for setup and unload."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pyetatouch import EtaConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import DOMAIN
from custom_components.eta_touch.helpers import variable_unique_id

from . import (
    BOILER_TEMP,
    ENABLED_BY_DEFAULT,
    HK_POWER,
    OUTDOOR,
    TITLE,
    WW_PRIORITY,
    enable_entity,
    entity_id_for,
    setup_integration,
)
from .conftest import FakeVarSet


async def test_setup_and_unload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
) -> None:
    await setup_integration(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert set(varset.addresses) == ENABLED_BY_DEFAULT
    assert varset.name.startswith("ha")
    assert len(varset.name) == 12
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert varset.closed


@pytest.mark.skip(reason="select platform in Task 4")
async def test_enabled_entity_is_polled_after_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
) -> None:
    await setup_integration(hass, config_entry)
    assert WW_PRIORITY not in varset.addresses
    await enable_entity(hass, "select", config_entry, WW_PRIORITY)
    assert WW_PRIORITY in varset.addresses


async def test_retry_when_varset_cannot_be_created(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
) -> None:
    varset.enter_error = EtaConnectionError("down")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_retry_when_first_refresh_fails(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
) -> None:
    varset.error = EtaConnectionError("down")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert varset.closed


@pytest.mark.skip(reason="switch platform in Task 4")
async def test_devices(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: object
) -> None:
    await setup_integration(hass, config_entry)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    controller = devices.async_get_device({(DOMAIN, config_entry.entry_id)})
    assert controller is not None
    assert controller.name == TITLE
    assert controller.model == "ETAtouch"

    def device(fub_id: str) -> dr.DeviceEntry:
        found = devices.async_get_device(
            {(DOMAIN, f"{config_entry.entry_id}_{fub_id}")}
        )
        assert found is not None
        assert found.via_device_id == controller.id
        return found

    boiler, system, hk, fwm = (
        device("40_10021"),
        device("120_10241"),
        device("120_10101"),
        device("120_10999"),
    )
    assert (boiler.name, boiler.model) == ("Kessel", "Boiler")
    assert (system.name, system.model) == ("Sys", "System")
    assert (hk.name, hk.model) == ("HK", "Heating circuit")
    assert (fwm.name, fwm.model) == ("FWM", "Function block 10999")

    for platform, address, owner in (
        ("sensor", BOILER_TEMP, boiler),
        ("sensor", OUTDOOR, system),
        ("switch", HK_POWER, hk),
    ):
        entity_id = entities.async_get_entity_id(
            platform, DOMAIN, variable_unique_id(config_entry.entry_id, address)
        )
        assert entity_id is not None
        registry_entry = entities.async_get(entity_id)
        assert registry_entry is not None
        assert registry_entry.device_id == owner.id

    problem = entities.async_get(
        entity_id_for(hass, "binary_sensor", config_entry, "problem")
    )
    assert problem is not None
    assert problem.device_id == controller.id
