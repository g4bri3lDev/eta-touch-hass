"""Runtime data and coordinators for ETA touch."""

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pyetatouch import (
    EtaClient,
    EtaError,
    EtaFault,
    EtaWebserviceUnavailableError,
    Installation,
    VarAddress,
    VarSet,
    VarValue,
)

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERRORS_INTERVAL,
    EVENT_ERROR_CLEARED,
    EVENT_ERROR_RAISED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class EtaRuntimeData:
    """Objects shared by the platforms of one config entry."""

    client: EtaClient
    installation: Installation
    varset: VarSet
    values: EtaDataCoordinator
    faults: EtaErrorsCoordinator
    stack: AsyncExitStack
    controller_device_id: str


type EtaConfigEntry = ConfigEntry[EtaRuntimeData]


def webservice_issue_id(entry: ConfigEntry) -> str:
    """Return the repair issue ID for an unavailable web service."""
    return f"webservice_unavailable_{entry.entry_id}"


def fault_payload(fault: EtaFault) -> dict[str, str | None]:
    """Return a JSON-serialisable description of a fault."""
    return {
        "component": fault.fub_name,
        "message": fault.message,
        "priority": fault.priority,
        "description": fault.description,
        "time": fault.time.isoformat() if fault.time else None,
    }


def _fault_key(fault: EtaFault) -> tuple[int, int, str, str | None]:
    return (
        fault.node,
        fault.fub,
        fault.message,
        fault.time.isoformat() if fault.time else None,
    )


class EtaDataCoordinator(DataUpdateCoordinator[dict[VarAddress, VarValue]]):
    """Polls the variable set."""

    config_entry: EtaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, varset: VarSet) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} values",
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.varset = varset

    async def _async_update_data(self) -> dict[VarAddress, VarValue]:
        issue_id = webservice_issue_id(self.config_entry)
        try:
            values = await self.varset.read_all()
        except EtaWebserviceUnavailableError as err:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="webservice_unavailable",
                translation_placeholders={"host": self.config_entry.data[CONF_HOST]},
            )
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="webservice_unavailable"
            ) from err
        except EtaError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        return values


class EtaErrorsCoordinator(DataUpdateCoordinator[list[EtaFault]]):
    """Polls active faults and fires events on changes."""

    config_entry: EtaConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: EtaClient
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} faults",
            update_interval=ERRORS_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> list[EtaFault]:
        try:
            faults = await self.client.errors()
        except EtaError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if self.data is not None:
            before = {_fault_key(fault): fault for fault in self.data}
            after = {_fault_key(fault): fault for fault in faults}
            entry_id = self.config_entry.entry_id
            for key in after.keys() - before.keys():
                self.hass.bus.async_fire(
                    EVENT_ERROR_RAISED,
                    {"entry_id": entry_id, **fault_payload(after[key])},
                )
            for key in before.keys() - after.keys():
                self.hass.bus.async_fire(
                    EVENT_ERROR_CLEARED,
                    {"entry_id": entry_id, **fault_payload(before[key])},
                )
        return faults
