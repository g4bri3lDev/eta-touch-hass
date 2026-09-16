"""Base entity and device helpers for ETA touch."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyetatouch import (
    Component,
    ComponentType,
    EtaError,
    Kind,
    MatchedVariable,
    VarValue,
    enabled_by_default,
    get_entry,
)

from .const import DOMAIN, MANUFACTURER
from .coordinator import EtaConfigEntry, EtaDataCoordinator
from .descriptions import META
from .helpers import variable_unique_id

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
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        model="ETAtouch",
        name=entry.title,
    )


def component_device_info(entry: ConfigEntry, component: Component) -> DeviceInfo:
    """Return the device of a function block."""
    model = (
        MODELS[component.type] if component.type else f"Function block {component.fub}"
    )
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{component.node}_{component.fub}")},
        manufacturer=MANUFACTURER,
        model=model,
        name=component.name or model,
        via_device=(DOMAIN, entry.entry_id),
    )


def platform_for(variable: MatchedVariable) -> Platform | None:
    """Return the platform a matched variable is exposed on (None if unknown key)."""
    catalog_entry = get_entry(variable.key)
    if catalog_entry is None:
        return None
    writable = variable.info is not None and variable.info.writable
    if writable and catalog_entry.kind is Kind.SWITCH:
        return Platform.SWITCH
    if writable and catalog_entry.kind is Kind.SELECT:
        return Platform.SELECT
    if writable and catalog_entry.kind is Kind.SETTING:
        return Platform.NUMBER
    return Platform.SENSOR


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
        try:
            await self._client.write(self.variable.address, value)
        except EtaError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()
