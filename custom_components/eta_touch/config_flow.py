"""Config flow for ETA touch."""

from __future__ import annotations

import asyncio
from functools import partial
import logging
from typing import Any

from getmac import get_mac_address
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from pyetatouch import (
    EtaClient,
    EtaConnectionError,
    EtaError,
    EtaNotEtaDeviceError,
    EtaUnsupportedApiError,
    EtaWebserviceUnavailableError,
    Installation,
    discover,
)
import voluptuous as vol

from .const import (
    CONF_ADVANCED,
    CONF_INSTALLATION,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .helpers import varset_name

_LOGGER = logging.getLogger(__name__)
TITLE = "ETAtouch"


def _connection_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_ADVANCED): section(
                vol.Schema({vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port}),
                {"collapsed": True},
            ),
        }
    )


class EtaTouchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ETA touch."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._host = ""
        self._port = DEFAULT_PORT
        self._client: EtaClient | None = None
        self._installation: Installation | None = None
        self._discovery_task: asyncio.Task[Installation] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EtaTouchOptionsFlow:
        """Return the options flow."""
        return EtaTouchOptionsFlow()

    async def _async_validate(self, host: str, port: int) -> dict[str, str]:
        client = EtaClient(async_get_clientsession(self.hass), host, port)
        try:
            await client.check_api()
        except EtaWebserviceUnavailableError:
            return {"base": "webservice_disabled"}
        except EtaConnectionError:
            return {"base": "cannot_connect"}
        except EtaNotEtaDeviceError:
            return {"base": "not_eta_device"}
        except EtaUnsupportedApiError:
            return {"base": "unsupported_api"}
        except EtaError:
            _LOGGER.exception("Unexpected error validating %s", host)
            return {"base": "unknown"}
        self._host, self._port, self._client = host, port, client
        return {}

    async def _async_mac(self, host: str) -> str | None:
        mac: str | None = await self.hass.async_add_executor_job(
            partial(get_mac_address, ip=host)
        )
        return format_mac(mac) if mac else None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_ADVANCED][CONF_PORT]
            self._async_abort_entries_match({CONF_HOST: host})
            errors = await self._async_validate(host, port)
            if not errors:
                if mac := await self._async_mac(host):
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: host, CONF_PORT: port}
                    )
                return await self.async_step_discover()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), user_input
            ),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a heater found via DHCP."""
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})
        for entry in self._async_current_entries(include_ignore=False):
            if (
                entry.unique_id is None
                and entry.data.get(CONF_HOST) == discovery_info.ip
            ):
                self.hass.config_entries.async_update_entry(entry, unique_id=mac)
                return self.async_abort(reason="already_configured")
        if await self._async_validate(discovery_info.ip, DEFAULT_PORT):
            return self.async_abort(reason="not_eta_device")
        self.context["title_placeholders"] = {"host": discovery_info.ip}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered heater."""
        if user_input is not None:
            return await self.async_step_discover()
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm", description_placeholders={"host": self._host}
        )

    async def _async_discover(self) -> Installation:
        assert self._client is not None
        name = await varset_name(self.hass, f"discover:{self._host}")
        return await discover(self._client, set_name=f"{name}d")

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Read the heater's configuration with a progress indicator."""
        if self._discovery_task is None:
            self._discovery_task = self.hass.async_create_task(self._async_discover())
        if not self._discovery_task.done():
            return self.async_show_progress(
                step_id="discover",
                progress_action="discover",
                progress_task=self._discovery_task,
            )
        task, self._discovery_task = self._discovery_task, None
        try:
            self._installation = task.result()
        except EtaError:
            _LOGGER.exception("Discovery of %s failed", self._host)
            return self.async_show_progress_done(next_step_id="discovery_failed")
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_discovery_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Abort after a failed discovery."""
        return self.async_abort(reason="discovery_failed")

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the entry."""
        installation = self._installation
        assert installation is not None
        if not installation.variables:
            return self.async_abort(reason="no_components")
        return self.async_create_entry(
            title=TITLE,
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_INSTALLATION: installation.to_dict(),
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host or port."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_ADVANCED][CONF_PORT]
            errors = await self._async_validate(host, port)
            if not errors:
                mac = await self._async_mac(host)
                if mac and entry.unique_id and mac != entry.unique_id:
                    return self.async_abort(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: host, CONF_PORT: port}
                )
        suggested = user_input or {
            CONF_HOST: entry.data[CONF_HOST],
            CONF_ADVANCED: {CONF_PORT: entry.data[CONF_PORT]},
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema(), suggested
            ),
            errors=errors,
        )


class EtaTouchOptionsFlow(OptionsFlowWithReload):
    """Options: update interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=10,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
        )
