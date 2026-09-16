"""Tests for the config flow."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from pyetatouch import (
    EtaConnectionError,
    EtaError,
    EtaNotEtaDeviceError,
    EtaUnsupportedApiError,
    EtaWebserviceUnavailableError,
    Installation,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import (
    CONF_ADVANCED,
    CONF_INSTALLATION,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from . import COMPONENTS, HOST, INSTALLATION, MAC, PORT, TITLE

USER_INPUT = {CONF_HOST: HOST, CONF_ADVANCED: {CONF_PORT: PORT}}
DHCP = DhcpServiceInfo(ip=HOST, hostname="eta", macaddress="002496aabbcc")
pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def _finish_progress(hass: HomeAssistant, result: FlowResult) -> FlowResult:
    """Finish the discovery step (instant mocks skip the progress screen)."""
    if result["type"] is FlowResultType.SHOW_PROGRESS:
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    return result


async def _user(
    hass: HomeAssistant, user_input: dict[str, object] = USER_INPUT
) -> FlowResult:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


@pytest.mark.usefixtures("mock_client", "mock_discover", "mock_getmac")
async def test_user_flow(hass: HomeAssistant) -> None:
    result = await _finish_progress(hass, await _user(hass))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {
        CONF_HOST: HOST,
        CONF_PORT: PORT,
        CONF_INSTALLATION: INSTALLATION.to_dict(),
    }
    assert result["result"].unique_id == MAC


@pytest.mark.usefixtures("mock_client", "mock_getmac")
async def test_progress_is_shown_while_discovering(
    hass: HomeAssistant, mock_discover: AsyncMock
) -> None:
    release = asyncio.Event()

    async def slow_discover(*args: object, **kwargs: object) -> Installation:
        await release.wait()
        return INSTALLATION

    mock_discover.side_effect = slow_discover
    result = await _user(hass)
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "discover"
    release.set()
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (EtaWebserviceUnavailableError("x"), "webservice_disabled"),
        (EtaConnectionError("x"), "cannot_connect"),
        (EtaNotEtaDeviceError("x"), "not_eta_device"),
        (EtaUnsupportedApiError("1.1"), "unsupported_api"),
        (EtaError("x"), "unknown"),
    ],
)
@pytest.mark.usefixtures("mock_discover", "mock_getmac")
async def test_user_flow_errors(
    hass: HomeAssistant, mock_client: MagicMock, error: Exception, key: str
) -> None:
    mock_client.check_api.side_effect = error
    result = await _user(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}
    mock_client.check_api.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    result = await _finish_progress(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_client", "mock_discover")
async def test_user_flow_without_mac(
    hass: HomeAssistant, mock_getmac: MagicMock
) -> None:
    mock_getmac.return_value = None
    result = await _finish_progress(hass, await _user(hass))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id is None


@pytest.mark.usefixtures("mock_client", "mock_discover", "mock_getmac")
async def test_user_flow_same_host_aborts(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await _user(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_client", "mock_discover", "mock_getmac")
async def test_user_flow_same_mac_updates_host(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await _user(
        hass, {CONF_HOST: "192.0.2.20", CONF_ADVANCED: {CONF_PORT: PORT}}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.0.2.20"


@pytest.mark.usefixtures("mock_client", "mock_getmac")
async def test_discovery_failed(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    mock_discover.side_effect = EtaConnectionError("x")
    result = await _finish_progress(hass, await _user(hass))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "discovery_failed"


@pytest.mark.usefixtures("mock_client", "mock_getmac")
async def test_no_components(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    mock_discover.return_value = Installation(COMPONENTS, ())
    result = await _finish_progress(hass, await _user(hass))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_components"


@pytest.mark.usefixtures("mock_client", "mock_discover")
async def test_dhcp_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await _finish_progress(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == MAC
    assert result["data"][CONF_HOST] == HOST


@pytest.mark.usefixtures("mock_client")
async def test_dhcp_updates_host(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={
            CONF_HOST: "192.0.2.99",
            CONF_PORT: PORT,
            CONF_INSTALLATION: INSTALLATION.to_dict(),
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


@pytest.mark.usefixtures("mock_client")
async def test_dhcp_attaches_mac_to_manual_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=None,
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_INSTALLATION: INSTALLATION.to_dict(),
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id == MAC


async def test_dhcp_not_eta(hass: HomeAssistant, mock_client: MagicMock) -> None:
    mock_client.check_api.side_effect = EtaNotEtaDeviceError("x")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=DHCP
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_eta_device"


@pytest.mark.usefixtures("mock_client", "mock_getmac")
async def test_reconfigure(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.20", CONF_ADVANCED: {CONF_PORT: 8081}}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_HOST] == "192.0.2.20"
    assert config_entry.data[CONF_PORT] == 8081


@pytest.mark.usefixtures("mock_client")
async def test_reconfigure_wrong_device(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_getmac: MagicMock
) -> None:
    config_entry.add_to_hass(hass)
    mock_getmac.return_value = "00:24:96:00:00:01"
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"


@pytest.mark.usefixtures("mock_getmac")
async def test_reconfigure_error(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    config_entry.add_to_hass(hass)
    mock_client.check_api.side_effect = EtaConnectionError("x")
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 120}
