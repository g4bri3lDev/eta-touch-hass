"""Tests for setup and unload."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pyetatouch import EtaConnectionError, Installation
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import CONF_INSTALLATION, DOMAIN
from custom_components.eta_touch.helpers import variable_unique_id

from . import (
    BOILER_TEMP,
    COMPONENTS,
    HK_AUTO,
    HK_COME,
    HK_OUTDOOR,
    HK_POWER,
    HOST,
    INSTALLATION,
    MAC,
    OUTDOOR,
    POLLED,
    TITLE,
    WW_PRIORITY,
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
    assert set(varset.addresses) == POLLED
    assert varset.name.startswith("ha")
    assert len(varset.name) == 12
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert varset.closed


async def test_all_matched_variables_are_polled(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    varset: FakeVarSet,
) -> None:
    await setup_integration(hass, config_entry)
    # disabled-by-default entities are polled too, so enabling one needs no extra request
    assert WW_PRIORITY in varset.addresses
    assert HK_OUTDOOR in varset.addresses
    # actions (buttons) have no value to poll
    assert HK_COME not in varset.addresses


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


async def test_devices(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: object
) -> None:
    await setup_integration(hass, config_entry)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    controller = devices.async_get_device_by_identifier(
        (DOMAIN, config_entry.entry_id), config_entry.entry_id
    )
    assert controller is not None
    assert controller.name == TITLE
    assert controller.model == "ETAtouch"
    assert controller.configuration_url == "https://www.meineta.at"
    assert (dr.CONNECTION_NETWORK_MAC, MAC) in controller.connections

    def child(fub_id: str) -> dr.ChildDeviceEntry:
        found = devices.async_get_child_device_by_identifier(
            (DOMAIN, f"{config_entry.entry_id}_{fub_id}"), config_entry.entry_id
        )
        assert found is not None
        assert found.parent_device_id == controller.id
        return found

    boiler, system, hk = child("40_10021"), child("120_10241"), child("120_10101")
    assert (boiler.name, system.name, hk.name) == ("Kessel", "Sys", "HK")
    assert child("120_10999").name == "FWM"

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


async def test_controller_without_mac(hass: HomeAssistant, mock_client: object) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        unique_id=None,
        data={CONF_HOST: HOST, CONF_INSTALLATION: INSTALLATION.to_dict()},
    )
    await setup_integration(hass, entry)
    controller = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert controller is not None
    assert controller.connections == set()


async def test_stale_entities_are_removed(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: object
) -> None:
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        "switch",
        DOMAIN,
        variable_unique_id(
            config_entry.entry_id, HK_AUTO
        ),  # old per-button mode switch
        config_entry=config_entry,
    )
    kept = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        variable_unique_id(config_entry.entry_id, BOILER_TEMP),
        config_entry=config_entry,
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(stale.entity_id) is None
    assert registry.async_get(kept.entity_id) is not None
    for suffix in (
        "problem",
        "active_errors",
        "latest_error",
        "rediscover",
        "120_10101_mode",
        "40_10021_energy",
    ):
        assert any(
            e.unique_id == f"{config_entry.entry_id}_{suffix}"
            for e in er.async_entries_for_config_entry(registry, config_entry.entry_id)
        ), suffix


async def test_stale_devices_are_removed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: object,
    mock_discover: AsyncMock,
) -> None:
    await setup_integration(hass, config_entry)
    devices = dr.async_get(hass)
    controller = devices.async_get_device_by_identifier(
        (DOMAIN, config_entry.entry_id), config_entry.entry_id
    )
    assert controller is not None
    assert len(dr.async_entries_for_parent_device(devices, controller.id)) == len(
        COMPONENTS
    )

    # the heater no longer reports the hot water block
    smaller = Installation(
        tuple(c for c in COMPONENTS if c.fub != 10111),
        tuple(v for v in INSTALLATION.variables if v.address.fub != 10111),
    )
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, CONF_INSTALLATION: smaller.to_dict()}
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        devices.async_get_child_device_by_identifier(
            (DOMAIN, f"{config_entry.entry_id}_120_10111"), config_entry.entry_id
        )
        is None
    )
    assert (
        len(dr.async_entries_for_parent_device(devices, controller.id))
        == len(COMPONENTS) - 1
    )
