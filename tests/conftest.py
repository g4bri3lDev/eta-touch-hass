"""Fixtures for ETA touch tests."""

from collections.abc import Generator, Iterable
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from pyetatouch import MenuFub, VarAddress, VarValue
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import CONF_INSTALLATION, DOMAIN

from . import HOST, INSTALLATION, MAC, PORT, TITLE, VALUES


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration."""


class FakeVarSet:
    """Stands in for pyetatouch.VarSet."""

    def __init__(self, values: dict[VarAddress, VarValue]) -> None:
        self.raw_values = values
        self.name = ""
        self.addresses: list[VarAddress] = []
        self.rejected: tuple[VarAddress, ...] = ()
        self.enter_error: Exception | None = None
        self.error: Exception | None = None
        self.closed = False

    @property
    def accepted(self) -> tuple[VarAddress, ...]:
        return tuple(self.addresses)

    def bind(self, name: str, addresses: Iterable[VarAddress]) -> FakeVarSet:
        self.name = name
        self.addresses = list(addresses)
        self.closed = False
        return self

    async def __aenter__(self) -> FakeVarSet:
        if self.enter_error is not None:
            raise self.enter_error
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.closed = True

    async def read_all(self) -> dict[VarAddress, VarValue]:
        if self.error is not None:
            raise self.error
        return {a: v for a, v in self.raw_values.items() if a in self.addresses}


@pytest.fixture
def varset() -> FakeVarSet:
    """Return the fake variable set used by the mocked client."""
    return FakeVarSet(dict(VALUES))


@pytest.fixture
def mock_client(varset: FakeVarSet) -> Generator[MagicMock]:
    """Patch EtaClient everywhere it is constructed."""
    client = MagicMock()
    client.check_api = AsyncMock(return_value="1.2")
    client.errors = AsyncMock(return_value=[])
    client.write = AsyncMock()
    client.menu = AsyncMock(
        return_value=[
            MenuFub(
                40,
                10021,
                "Kessel",
                {(0, 11109, 0): "Kessel", (0, 0, 13987): "Ein/Aus Taste anzeigen"},
            )
        ]
    )
    client.varset = MagicMock(side_effect=varset.bind)
    with (
        patch("custom_components.eta_touch.EtaClient", return_value=client),
        patch("custom_components.eta_touch.config_flow.EtaClient", return_value=client),
    ):
        yield client


@pytest.fixture
def mock_discover() -> Generator[AsyncMock]:
    """Patch pyetatouch.discover."""
    mock = AsyncMock(return_value=INSTALLATION)
    with (
        patch("custom_components.eta_touch.config_flow.discover", mock),
        patch("custom_components.eta_touch.button.discover", mock),
    ):
        yield mock


@pytest.fixture
def mock_getmac() -> Generator[MagicMock]:
    """Patch the MAC lookup."""
    with patch(
        "custom_components.eta_touch.config_flow.get_mac_address", return_value=MAC
    ) as mock:
        yield mock


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip entry setup in flow tests."""
    with patch(
        "custom_components.eta_touch.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a configured entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        unique_id=MAC,
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_INSTALLATION: INSTALLATION.to_dict(),
        },
    )
