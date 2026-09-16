"""Time entities for ETA touch."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EtaConfigEntry
from .entity import EtaEntity, variables_for_platform

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up time entities."""
    async_add_entities(
        EtaTime(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.TIME)
    )


class EtaTime(EtaEntity, TimeEntity):
    """A time of day stored as minutes since midnight."""

    @property
    def native_value(self) -> time | None:
        """Return the configured time."""
        if (value := self.raw_value) is None:
            return None
        minutes = int(value.raw)
        return time(minutes // 60 % 24, minutes % 60)

    async def async_set_value(self, value: time) -> None:
        """Write a new time."""
        await self._async_write(value.hour * 60 + value.minute)
