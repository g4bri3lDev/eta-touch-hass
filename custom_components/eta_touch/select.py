"""Selects for ETA touch."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pyetatouch import (
    Component,
    Kind,
    MatchedVariable,
    VarAddress,
    code_for_state,
    get_entry,
    state_key,
    state_keys,
    switch_codes,
)

from .coordinator import EtaConfigEntry, EtaDataCoordinator
from .entity import (
    EtaEntity,
    async_write,
    component_device_info,
    variables_for_platform,
)
from .helpers import mode_unique_id

PARALLEL_UPDATES = 1

# catalog key of a panel mode button -> option key of the mode select (in panel order)
MODE_OPTIONS = {
    "auto_button": "auto",
    "heat_button": "heating",
    "setback_button": "setback",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    entities: list[SelectEntity] = [
        EtaSelect(entry, component, variable)
        for component, variable in variables_for_platform(entry, Platform.SELECT)
    ]
    installation = entry.runtime_data.installation
    for component in installation.components:
        buttons = [
            variable
            for variable in installation.variables_for(component)
            if (catalog_entry := get_entry(variable.key)) is not None
            and catalog_entry.kind is Kind.MODE
            and variable.key in MODE_OPTIONS
            and variable.info is not None
            and variable.info.writable
        ]
        if buttons:
            entities.append(EtaModeSelect(entry, component, buttons))
    async_add_entities(entities)


class EtaSelect(EtaEntity, SelectEntity):
    """A writable enumeration."""

    def __init__(
        self, entry: EtaConfigEntry, component: Component, variable: MatchedVariable
    ) -> None:
        """Initialise the select."""
        super().__init__(entry, component, variable)
        assert self.info is not None
        self._attr_options = state_keys(self.info)

    @property
    def current_option(self) -> str | None:
        """Return the active option."""
        if (value := self.raw_value) is None:
            return None
        key = state_key(int(value.raw))
        return key if key in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        assert self.info is not None
        await self._async_write(code_for_state(self.info, option))


class EtaModeSelect(CoordinatorEntity[EtaDataCoordinator], SelectEntity):
    """The panel's mutually exclusive mode buttons (Auto, Heizen, Absenken) as one select."""

    _attr_has_entity_name = True
    _attr_translation_key = "mode"

    def __init__(
        self,
        entry: EtaConfigEntry,
        component: Component,
        buttons: list[MatchedVariable],
    ) -> None:
        """Initialise the select."""
        super().__init__(entry.runtime_data.values)
        self._client = entry.runtime_data.client
        self._buttons: dict[str, tuple[VarAddress, int]] = {}
        for button in buttons:
            assert button.info is not None
            self._buttons[MODE_OPTIONS[button.key]] = (
                button.address,
                switch_codes(button.info)[1],
            )
        self._attr_options = [o for o in MODE_OPTIONS.values() if o in self._buttons]
        self._attr_unique_id = mode_unique_id(
            entry.entry_id, component.node, component.fub
        )
        self._attr_device_info = component_device_info(entry, component)

    @property
    def available(self) -> bool:
        """Return whether the heater delivered the button states."""
        data = self.coordinator.data or {}
        return super().available and all(a in data for a, _ in self._buttons.values())

    @property
    def current_option(self) -> str | None:
        """Return the pressed mode button (None when the circuit is off)."""
        data = self.coordinator.data or {}
        for option, (address, on) in self._buttons.items():
            if (value := data.get(address)) is not None and int(value.raw) == on:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        """Press the button of the selected mode."""
        address, on = self._buttons[option]
        await async_write(self._client, self.coordinator, address, on)
