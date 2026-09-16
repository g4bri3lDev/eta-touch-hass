"""Sensors for ETA touch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyetatouch import (
    Component,
    Kind,
    MatchedVariable,
    decode_value,
    state_key,
    state_keys,
)

from .coordinator import EtaConfigEntry, EtaErrorsCoordinator, fault_payload
from .entity import EtaEntity, controller_device_info, variables_for_platform

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    entities: list[SensorEntity] = [
        EtaSensor(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.SENSOR)
    ]
    entities.append(EtaActiveErrorsSensor(entry))
    async_add_entities(entities)


class EtaSensor(EtaEntity, SensorEntity):
    """A read-only heater value."""

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the sensor."""
        super().__init__(entry, component, variable)
        if self.meta.config:
            # Sensors may not use the config category; read-only settings are diagnostics.
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if self.info is not None and self.info.options:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = state_keys(self.info)
            return
        self._attr_native_unit_of_measurement = self.meta.unit
        self._attr_device_class = self.meta.sensor_class
        self._attr_suggested_unit_of_measurement = self.meta.suggested_unit
        self._attr_suggested_display_precision = self.meta.precision
        self._attr_state_class = (
            SensorStateClass.TOTAL_INCREASING
            if self.kind is Kind.TOTAL
            else SensorStateClass.MEASUREMENT
        )

    @property
    def native_value(self) -> float | str | None:
        """Return the decoded value."""
        if (value := self.raw_value) is None:
            return None
        if self.device_class is SensorDeviceClass.ENUM:
            key = state_key(int(value.raw))
            return key if key in (self.options or []) else None
        decoded = decode_value(value, self.info)
        return decoded if isinstance(decoded, float) else None


class EtaActiveErrorsSensor(CoordinatorEntity[EtaErrorsCoordinator], SensorEntity):
    """Number of active heater faults."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_errors"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: EtaConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(entry.runtime_data.faults)
        self._attr_unique_id = f"{entry.entry_id}_active_errors"
        self._attr_device_info = controller_device_info(entry)

    @property
    def native_value(self) -> int:
        """Return the number of active faults."""
        return len(self.coordinator.data or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the faults."""
        return {
            "errors": [fault_payload(fault) for fault in self.coordinator.data or []]
        }
