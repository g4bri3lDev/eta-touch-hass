"""Tests for the ETA touch integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyetatouch import (
    Component,
    ComponentType,
    Installation,
    MatchedVariable,
    VarAddress,
    VarInfo,
    VarValue,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_touch.const import DOMAIN
from custom_components.eta_touch.helpers import variable_unique_id

HOST = "192.0.2.10"
PORT = 8080
MAC = "00:24:96:aa:bb:cc"
TITLE = "ETAtouch"

BOILER_TEMP = VarAddress.parse("40/10021/0/11109/0")
BOILER_STATE = VarAddress.parse("40/10021/0/0/19402")
TOTAL = VarAddress.parse("40/10021/0/0/12016")
HOURS = VarAddress.parse("40/10021/0/0/12153")
OUTDOOR = VarAddress.parse("120/10241/0/0/12197")
HK_OUTDOOR = VarAddress.parse("120/10101/0/0/12197")
HK_POWER = VarAddress.parse("120/10101/0/0/12080")
HK_OFFSET = VarAddress.parse("120/10101/0/0/12240")
HK_FLOW_MINUS = VarAddress.parse("120/10101/0/0/12104")
WW_TARGET = VarAddress.parse("120/10111/0/0/12132")
WW_PRIORITY = VarAddress.parse("120/10111/0/0/12770")
WW_TEMP = VarAddress.parse("120/10111/0/11129/0")
FWM_OUTDOOR = VarAddress.parse("120/10999/0/0/12197")

STATES = {4000: "Ausgeschaltet", 4001: "Bereit"}
ON_OFF = {1802: "Aus", 1803: "Ein"}
PRIORITIES = {1971: "Niedrig", 1972: "Mittel", 1973: "Hoch"}

ENABLED_BY_DEFAULT = {
    BOILER_TEMP,
    BOILER_STATE,
    TOTAL,
    HOURS,
    OUTDOOR,
    HK_POWER,
    HK_OFFSET,
    WW_TARGET,
    WW_TEMP,
}


def info(
    address: VarAddress,
    name: str,
    *,
    writable: bool = False,
    unit: str = "",
    scale: int = 1,
    minimum: float | None = None,
    maximum: float | None = None,
    options: dict[int, str] | None = None,
) -> VarInfo:
    """Build variable metadata."""
    return VarInfo(
        address=address,
        name=name,
        full_name=name,
        type="TEXT" if options else "DEFAULT",
        unit=unit,
        scale=scale,
        writable=writable,
        minimum=minimum,
        maximum=maximum,
        default=None,
        options=options or {},
    )


def value(
    address: VarAddress,
    raw: float,
    text: str,
    unit: str = "",
    scale: int = 1,
    offset: int = 0,
) -> VarValue:
    """Build a variable value."""
    return VarValue(address, raw, text, unit, scale, 0, offset)


COMPONENTS = (
    Component(ComponentType.BOILER, 40, 10021, "Kessel"),
    Component(ComponentType.SYSTEM, 120, 10241, "Sys"),
    Component(ComponentType.HEATING_CIRCUIT, 120, 10101, "HK"),
    Component(ComponentType.HOT_WATER, 120, 10111, "WW"),
    Component(None, 120, 10999, "FWM"),
)

INSTALLATION = Installation(
    COMPONENTS,
    (
        MatchedVariable("boiler_temperature", BOILER_TEMP, None),
        MatchedVariable(
            "boiler_state", BOILER_STATE, info(BOILER_STATE, "Kessel", options=STATES)
        ),
        MatchedVariable("total_consumption", TOTAL, None),
        MatchedVariable("full_load_hours", HOURS, None),
        MatchedVariable("outdoor_temperature", OUTDOOR, None),
        MatchedVariable("outdoor_temperature", HK_OUTDOOR, None),
        MatchedVariable(
            "power",
            HK_POWER,
            info(HK_POWER, "Ein/Aus Taste", writable=True, options=ON_OFF),
        ),
        MatchedVariable(
            "curve_offset",
            HK_OFFSET,
            info(
                HK_OFFSET,
                "Schieber",
                writable=True,
                unit="%",
                scale=10,
                minimum=-1000.0,
                maximum=1000.0,
            ),
        ),
        MatchedVariable(
            "flow_at_minus_10",
            HK_FLOW_MINUS,
            info(HK_FLOW_MINUS, "Vorlauf bei -10", unit="°C", scale=10),
        ),
        MatchedVariable(
            "hot_water_target_temperature",
            WW_TARGET,
            info(
                WW_TARGET,
                "Soll",
                writable=True,
                unit="°C",
                scale=10,
                minimum=0.0,
                maximum=900.0,
            ),
        ),
        MatchedVariable(
            "priority",
            WW_PRIORITY,
            info(WW_PRIORITY, "Priorität", writable=True, options=PRIORITIES),
        ),
        MatchedVariable("hot_water_temperature", WW_TEMP, None),
        MatchedVariable("outdoor_temperature", FWM_OUTDOOR, None),
    ),
)

VALUES = {
    BOILER_TEMP: value(BOILER_TEMP, 600.0, "60", "°C", 10),
    BOILER_STATE: value(BOILER_STATE, 4001.0, "Bereit", offset=4000),
    TOTAL: value(TOTAL, 170000.0, "17000", "kg", 10),
    HOURS: value(HOURS, 36000.0, "10h 0m", "s"),
    OUTDOOR: value(OUTDOOR, 125.0, "12,5", "°C", 10),
    HK_OUTDOOR: value(HK_OUTDOOR, 125.0, "12,5", "°C", 10),
    HK_POWER: value(HK_POWER, 1803.0, "Ein", offset=1802),
    HK_OFFSET: value(HK_OFFSET, 300.0, "30", "%", 10),
    HK_FLOW_MINUS: value(HK_FLOW_MINUS, 650.0, "65", "°C", 10),
    WW_TARGET: value(WW_TARGET, 500.0, "50", "°C", 10),
    WW_PRIORITY: value(WW_PRIORITY, 1973.0, "xxx", offset=1971),
    WW_TEMP: value(WW_TEMP, 442.0, "44", "°C", 10),
    FWM_OUTDOOR: value(FWM_OUTDOOR, 125.0, "12,5", "°C", 10),
}


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the integration for a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id_for(
    hass: HomeAssistant, platform: str, entry: MockConfigEntry, suffix: VarAddress | str
) -> str:
    """Look up an entity ID by variable address or fixed unique-ID suffix."""
    unique_id = (
        variable_unique_id(entry.entry_id, suffix)
        if isinstance(suffix, VarAddress)
        else f"{entry.entry_id}_{suffix}"
    )
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None, f"no {platform} entity for {suffix}"
    return entity_id


async def enable_entity(
    hass: HomeAssistant, platform: str, entry: MockConfigEntry, address: VarAddress
) -> str:
    """Enable a disabled-by-default entity and reload the entry."""
    entity_id = entity_id_for(hass, platform, entry, address)
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    return entity_id
