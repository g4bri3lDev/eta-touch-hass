"""Tests for the rediscover button."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pyetatouch import EtaConnectionError, Installation
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import CONF_INSTALLATION

from . import COMPONENTS, INSTALLATION, entity_id_for, setup_integration


async def test_rediscover(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
    mock_discover: AsyncMock,
) -> None:
    await setup_integration(hass, config_entry)
    smaller = Installation(COMPONENTS, INSTALLATION.variables[:2])
    mock_discover.return_value = smaller
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id_for(hass, "button", config_entry, "rediscover")},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert mock_discover.await_args.args[0] is mock_client
    assert mock_discover.await_args.kwargs["set_name"].endswith("d")
    assert config_entry.data[CONF_INSTALLATION] == smaller.to_dict()
    assert config_entry.state is ConfigEntryState.LOADED


async def test_rediscover_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
    mock_discover: AsyncMock,
) -> None:
    await setup_integration(hass, config_entry)
    mock_discover.side_effect = EtaConnectionError("down")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id_for(hass, "button", config_entry, "rediscover")},
            blocking=True,
        )
