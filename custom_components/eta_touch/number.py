"""Numbers for ETA touch."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pyetatouch import Component, MatchedVariable, decode_value

from .coordinator import EtaConfigEntry
from .entity import EtaEntity, variables_for_platform

PARALLEL_UPDATES = 1
UNBOUNDED = 1_000_000.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numbers."""
    async_add_entities(
        EtaNumber(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.NUMBER)
    )


class EtaNumber(EtaEntity, NumberEntity):
    """A writable numeric setting."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the number."""
        super().__init__(entry, component, variable)
        assert self.info is not None
        self._divisor = self.meta.number_divisor
        scale = (self.info.scale or 1) * self._divisor
        self._attr_native_step = 1 / (self.info.scale or 1)
        self._attr_native_min_value = (
            self.info.minimum / scale if self.info.minimum is not None else -UNBOUNDED
        )
        self._attr_native_max_value = (
            self.info.maximum / scale if self.info.maximum is not None else UNBOUNDED
        )
        self._attr_native_unit_of_measurement = self.meta.number_unit or self.meta.unit
        self._attr_device_class = self.meta.number_class

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if (value := self.raw_value) is None:
            return None
        decoded = decode_value(value, self.info)
        return decoded / self._divisor if isinstance(decoded, float) else None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value."""
        await self._async_write(value * self._divisor)
