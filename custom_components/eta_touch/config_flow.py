"""Config flow for ETA touch (stub, replaced in the config flow task)."""

from homeassistant.config_entries import ConfigFlow
from pyetatouch import EtaClient, discover

from .const import DOMAIN

__all__ = ["EtaClient", "EtaTouchConfigFlow", "discover"]


class EtaTouchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Placeholder flow."""

    VERSION = 1
