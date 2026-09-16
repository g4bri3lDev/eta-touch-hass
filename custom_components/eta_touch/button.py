"""Buttons for ETA touch."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pyetatouch import Component, EtaError, MatchedVariable, discover, switch_codes

from .const import CONF_INSTALLATION, DOMAIN
from .coordinator import EtaConfigEntry
from .entity import EtaEntity, controller_device_info, variables_for_platform
from .helpers import varset_name

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    entities: list[ButtonEntity] = [
        EtaActionButton(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.BUTTON)
    ]
    entities.append(EtaRediscoverButton(entry))
    async_add_entities(entities)


class EtaActionButton(EtaEntity, ButtonEntity):
    """A momentary panel action (e.g. Kommen, Gehen, fill pellet container)."""

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the button."""
        super().__init__(entry, component, variable)
        assert self.info is not None
        self._on = switch_codes(self.info)[1]

    @property
    def available(self) -> bool:
        """Actions are not polled; they are available while the heater is reachable."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Trigger the action."""
        await self._async_write(self._on)


class EtaRediscoverButton(ButtonEntity):
    """Re-read the heater's configuration."""

    _attr_has_entity_name = True
    _attr_translation_key = "rediscover"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: EtaConfigEntry) -> None:
        """Initialise the button."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_rediscover"
        self._attr_device_info = controller_device_info(entry)

    async def async_press(self) -> None:
        """Run discovery and reload with the result."""
        entry = self._entry
        name = await varset_name(self.hass, f"rediscover:{entry.entry_id}")
        try:
            installation = await discover(
                entry.runtime_data.client, set_name=f"{name}d"
            )
        except EtaError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rediscover_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_INSTALLATION: installation.to_dict()}
        )
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
