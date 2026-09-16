"""The ETA touch integration."""

from __future__ import annotations

from contextlib import AsyncExitStack, suppress

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyetatouch import (
    EtaClient,
    EtaError,
    Installation,
    VarAddress,
    enabled_by_default,
    get_entry,
)

from .const import CONF_INSTALLATION, DOMAIN
from .coordinator import (
    EtaConfigEntry,
    EtaDataCoordinator,
    EtaErrorsCoordinator,
    EtaRuntimeData,
)
from .entity import controller_device_info
from .helpers import variable_unique_id, varset_name

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _enabled_addresses(
    hass: HomeAssistant, entry: EtaConfigEntry, installation: Installation
) -> list[VarAddress]:
    registry = er.async_get(hass)
    known = {
        registry_entry.unique_id: registry_entry
        for registry_entry in er.async_entries_for_config_entry(
            registry, entry.entry_id
        )
    }
    addresses: list[VarAddress] = []
    for component in installation.components:
        for variable in installation.variables_for(component):
            registry_entry = known.get(
                variable_unique_id(entry.entry_id, variable.address)
            )
            if registry_entry is not None:
                enabled = registry_entry.disabled_by is None
            else:
                catalog_entry = get_entry(variable.key)
                enabled = catalog_entry is not None and enabled_by_default(
                    catalog_entry, component.type
                )
            if enabled:
                addresses.append(variable.address)
    return addresses


async def _close(stack: AsyncExitStack) -> None:
    with suppress(EtaError):
        await stack.aclose()


async def async_setup_entry(hass: HomeAssistant, entry: EtaConfigEntry) -> bool:
    """Set up ETA touch from a config entry."""
    client = EtaClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT]
    )
    installation = Installation.from_dict(entry.data[CONF_INSTALLATION])
    controller = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **controller_device_info(entry)
    )
    name = await varset_name(hass, entry.entry_id)
    stack = AsyncExitStack()
    try:
        varset = await stack.enter_async_context(
            client.varset(name, _enabled_addresses(hass, entry, installation))
        )
        values = EtaDataCoordinator(hass, entry, varset)
        faults = EtaErrorsCoordinator(hass, entry, client)
        await values.async_config_entry_first_refresh()
        await faults.async_config_entry_first_refresh()
    except EtaError as err:
        await _close(stack)
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(err)},
        ) from err
    except BaseException:
        await _close(stack)
        raise
    entry.runtime_data = EtaRuntimeData(
        client, installation, varset, values, faults, stack, controller.id
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EtaConfigEntry) -> bool:
    """Unload a config entry and delete its variable set."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await _close(entry.runtime_data.stack)
    return unloaded
