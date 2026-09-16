"""Diagnostics for ETA touch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pyetatouch import EtaError, entry_for_alias

from .coordinator import EtaConfigEntry, fault_payload

TO_REDACT = {CONF_HOST, "unique_id"}


async def _unknown_variables(entry: EtaConfigEntry) -> list[dict[str, str]] | str:
    try:
        menu = await entry.runtime_data.client.menu()
    except EtaError as err:
        return f"unavailable: {err}"
    return [
        {"address": f"{fub.node}/{fub.fub}/{'/'.join(map(str, key))}", "name": name}
        for fub in menu
        for key, name in fub.variables.items()
        if entry_for_alias(key) is None
    ]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EtaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "varset": {
            "name": runtime.varset.name,
            "accepted": [str(address) for address in runtime.varset.accepted],
            "rejected": [str(address) for address in runtime.varset.rejected],
        },
        "values": {
            str(address): {"raw": value.raw, "text": value.text, "unit": value.unit}
            for address, value in (runtime.values.data or {}).items()
        },
        "faults": [fault_payload(fault) for fault in runtime.faults.data or []],
        "unknown_variables": await _unknown_variables(entry),
    }
