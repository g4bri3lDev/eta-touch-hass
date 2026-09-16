"""Buttons for ETA touch."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pyetatouch import EtaError, discover

from .const import CONF_INSTALLATION, DOMAIN
from .coordinator import EtaConfigEntry
from .entity import controller_device_info
from .helpers import varset_name

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    async_add_entities([EtaRediscoverButton(entry)])


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
