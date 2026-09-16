"""Binary sensors for ETA touch."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import EtaConfigEntry, EtaErrorsCoordinator
from .entity import controller_device_info

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    async_add_entities([EtaProblemBinarySensor(entry)])


class EtaProblemBinarySensor(
    CoordinatorEntity[EtaErrorsCoordinator], BinarySensorEntity
):
    """On while the heater reports faults."""

    _attr_has_entity_name = True
    _attr_translation_key = "problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, entry: EtaConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(entry.runtime_data.faults)
        self._attr_unique_id = f"{entry.entry_id}_problem"
        self._attr_device_info = controller_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return whether faults are active."""
        return bool(self.coordinator.data)
