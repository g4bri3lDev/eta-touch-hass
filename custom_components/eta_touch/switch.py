"""Switches for ETA touch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pyetatouch import Component, MatchedVariable, switch_codes

from .coordinator import EtaConfigEntry
from .entity import EtaEntity, variables_for_platform

PARALLEL_UPDATES = 1
MAIN_SWITCH_KEY = "power"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    async_add_entities(
        EtaSwitch(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.SWITCH)
    )


class EtaSwitch(EtaEntity, SwitchEntity):
    """A two-option variable (off/on, no/yes)."""

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the switch."""
        super().__init__(entry, component, variable)
        assert self.info is not None
        self._off, self._on = switch_codes(self.info)
        if variable.key == MAIN_SWITCH_KEY:
            # The block's on/off button is its main feature: use the device name.
            self._attr_name = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the option 'on' is active."""
        if (value := self.raw_value) is None:
            return None
        return int(value.raw) == self._on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self._async_write(self._on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self._async_write(self._off)
