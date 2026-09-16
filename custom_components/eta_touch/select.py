"""Selects for ETA touch."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pyetatouch import Component, MatchedVariable, decode_value

from .coordinator import EtaConfigEntry
from .entity import EtaEntity, variables_for_platform

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    async_add_entities(
        EtaSelect(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.SELECT)
    )


class EtaSelect(EtaEntity, SelectEntity):
    """A writable enumeration."""

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the select."""
        super().__init__(entry, component, variable)
        assert self.info is not None
        self._attr_options = list(dict.fromkeys(self.info.options.values()))

    @property
    def current_option(self) -> str | None:
        """Return the active option."""
        if (value := self.raw_value) is None:
            return None
        decoded = decode_value(value, self.info)
        return decoded if isinstance(decoded, str) else None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        await self._async_write(option)
