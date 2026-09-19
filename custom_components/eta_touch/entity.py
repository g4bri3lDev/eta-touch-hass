"""Base entity and device helpers for ETA touch."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    ChildDeviceInfo,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyetatouch import (
    Component,
    ComponentType,
    EtaClient,
    EtaError,
    Installation,
    Kind,
    MatchedVariable,
    VarAddress,
    VarValue,
    enabled_by_default,
    get_entry,
)

from .const import DOMAIN, MANUFACTURER, MEINETA_URL
from .coordinator import EtaConfigEntry, EtaDataCoordinator
from .descriptions import META
from .helpers import mode_unique_id, variable_unique_id

ENERGY_SOURCE_KEY = "total_consumption"
# fixed entities of the controller device (unique ID = f"{entry_id}_{suffix}")
CONTROLLER_ENTITY_SUFFIXES = ("problem", "active_errors", "latest_error", "rediscover")
# catalog key of a panel mode button -> option key of the mode select (in panel order)
MODE_OPTIONS = {
    "auto_button": "auto",
    "heat_button": "heating",
    "setback_button": "setback",
}

MODELS = {
    ComponentType.BOILER: "Boiler",
    ComponentType.HEATING_CIRCUIT: "Heating circuit",
    ComponentType.HOT_WATER: "Hot water",
    ComponentType.PELLET_STORE: "Pellet store",
    ComponentType.SOLAR: "Solar",
    ComponentType.SYSTEM: "System",
    ComponentType.BUFFER: "Buffer",
    ComponentType.FRESH_WATER: "Fresh water module",
    ComponentType.CIRCULATION: "Circulation",
}


def controller_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device of the ETAtouch controller (parent of all function blocks)."""
    info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        model="ETAtouch",
        name=entry.title,
        configuration_url=MEINETA_URL,
    )
    if entry.unique_id:  # the formatted MAC address, when setup or DHCP could read it
        info["connections"] = {(CONNECTION_NETWORK_MAC, entry.unique_id)}
    return info


def component_device_info(
    entry: EtaConfigEntry, component: Component
) -> ChildDeviceInfo:
    """Return the child device of a function block."""
    fallback = (
        MODELS[component.type] if component.type else f"Function block {component.fub}"
    )
    return ChildDeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{component.node}_{component.fub}")},
        parent_device_id=entry.runtime_data.controller_device_id,
        name=component.name or fallback,
    )


def platform_for(variable: MatchedVariable) -> Platform | None:
    """Return the platform a matched variable is exposed on (None if unknown key)."""
    catalog_entry = get_entry(variable.key)
    if catalog_entry is None:
        return None
    writable = variable.info is not None and variable.info.writable
    if catalog_entry.kind is Kind.MODE:
        return None  # grouped into one select per function block
    if catalog_entry.kind is Kind.ACTION:
        return Platform.BUTTON if writable else None
    if catalog_entry.kind is Kind.TIME:
        return Platform.TIME if writable else None
    if writable and catalog_entry.kind is Kind.SWITCH:
        return Platform.SWITCH
    if writable and catalog_entry.kind is Kind.SELECT:
        return Platform.SELECT
    if writable and catalog_entry.kind is Kind.SETTING:
        return Platform.NUMBER
    return Platform.SENSOR


def energy_unique_id(entry_id: str, component: Component) -> str:
    """Return the unique ID of a boiler's energy sensor."""
    return f"{entry_id}_{component.node}_{component.fub}_energy"


def polled_addresses(installation: Installation) -> list[VarAddress]:
    """Return the addresses whose values entities need.

    Everything the catalog matched is polled: reading a variable set is a single
    request regardless of its size. Only actions (buttons) have no value.
    """
    return [
        variable.address
        for component in installation.components
        for variable in installation.variables_for(component)
        if (catalog_entry := get_entry(variable.key)) is not None
        and catalog_entry.kind is not Kind.ACTION
    ]


async def async_write(
    client: EtaClient,
    coordinator: EtaDataCoordinator,
    address: VarAddress,
    value: float | str,
) -> None:
    """Write a value and refresh, translating library errors."""
    try:
        await client.write(address, value)
    except EtaError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="write_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    await coordinator.async_request_refresh()


def mode_buttons(
    installation: Installation, component: Component
) -> list[MatchedVariable]:
    """Return the writable panel mode buttons of a function block."""
    return [
        variable
        for variable in installation.variables_for(component)
        if variable.key in MODE_OPTIONS
        and variable.info is not None
        and variable.info.writable
    ]


def expected_unique_ids(entry_id: str, installation: Installation) -> set[str]:
    """Return the unique IDs of all entities the installation produces."""
    unique_ids = {f"{entry_id}_{suffix}" for suffix in CONTROLLER_ENTITY_SUFFIXES}
    for component in installation.components:
        if mode_buttons(installation, component):
            unique_ids.add(mode_unique_id(entry_id, component.node, component.fub))
        for variable in installation.variables_for(component):
            if platform_for(variable) is not None:
                unique_ids.add(variable_unique_id(entry_id, variable.address))
            if variable.key == ENERGY_SOURCE_KEY:
                unique_ids.add(energy_unique_id(entry_id, component))
    return unique_ids


def variables_for_platform(
    entry: EtaConfigEntry, platform: Platform
) -> list[tuple[Component, MatchedVariable]]:
    """Return the (component, variable) pairs exposed on a platform."""
    installation = entry.runtime_data.installation
    return [
        (component, variable)
        for component in installation.components
        for variable in installation.variables_for(component)
        if platform_for(variable) is platform
    ]


class EtaEntity(CoordinatorEntity[EtaDataCoordinator]):
    """An entity backed by one heater variable."""

    _attr_has_entity_name = True

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the entity."""
        super().__init__(entry.runtime_data.values)
        catalog_entry = get_entry(variable.key)
        assert catalog_entry is not None
        self._client = entry.runtime_data.client
        self.variable = variable
        self.info = variable.info
        self.kind = catalog_entry.kind
        self.meta = META[variable.key]
        self._attr_translation_key = variable.key
        self._attr_unique_id = variable_unique_id(entry.entry_id, variable.address)
        self._attr_device_info = component_device_info(entry, component)
        self._attr_entity_registry_enabled_default = enabled_by_default(
            catalog_entry, component.type
        )
        if self.meta.config:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def raw_value(self) -> VarValue | None:
        """Return the latest raw value."""
        return (self.coordinator.data or {}).get(self.variable.address)

    @property
    def available(self) -> bool:
        """Return whether the heater delivered a value."""
        return super().available and self.raw_value is not None

    async def _async_write(self, value: float | str) -> None:
        await async_write(self._client, self.coordinator, self.variable.address, value)
