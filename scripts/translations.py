"""Generate strings.json and translations/{en,de}.json.

Run: uv run python scripts/translations.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyetatouch import CATALOG, STATE_KEYS, Kind

ROOT = Path(__file__).parent.parent / "custom_components" / "eta_touch"

# key: (English, German)
NAMES: dict[str, tuple[str, str]] = {
    "power": ("Power", "Ein/Aus"),
    "outdoor_temperature": ("Outdoor temperature", "Außentemperatur"),
    "flow_temperature": ("Flow temperature", "Vorlauftemperatur"),
    "return_temperature": ("Return temperature", "Rücklauftemperatur"),
    "hot_water_charge_now": ("Charge hot water now", "Warmwasser sofort laden"),
    "switch_on_difference": ("Switch-on difference", "Einschaltdifferenz"),
    "priority": ("Priority", "Priorität"),
    "requested_power": ("Requested power", "Angeforderte Leistung"),
    "boiler_state": ("Boiler state", "Kesselzustand"),
    "boiler_temperature": ("Boiler temperature", "Kesseltemperatur"),
    "boiler_target_temperature": ("Boiler target temperature", "Kessel-Solltemperatur"),
    "boiler_return_temperature": (
        "Boiler return temperature",
        "Kessel-Rücklauftemperatur",
    ),
    "flue_gas_temperature": ("Flue gas temperature", "Abgastemperatur"),
    "residual_oxygen": ("Residual oxygen", "Restsauerstoff"),
    "boiler_pressure": ("Boiler pressure", "Kesseldruck"),
    "requested_temperature": ("Requested temperature", "Angeforderte Temperatur"),
    "flue_gas_fan_speed": ("Flue gas fan speed", "Abgasgebläse-Drehzahl"),
    "boiler_pump": ("Boiler pump", "Kesselpumpe"),
    "stoker_screw": ("Stoker screw", "Stokerschnecke"),
    "ignition": ("Ignition", "Zündung"),
    "suction_turbine": ("Suction turbine", "Saugturbine"),
    "ash_box": ("Ash box", "Aschebox"),
    "pellet_container": ("Pellet container", "Pelletsbehälter"),
    "pellet_container_content": ("Pellet container content", "Inhalt Pelletsbehälter"),
    "total_consumption": ("Total consumption", "Gesamtverbrauch"),
    "consumption_since_ash_box_emptied": (
        "Consumption since ash box emptied",
        "Verbrauch seit Aschebox leeren",
    ),
    "consumption_since_deashing": (
        "Consumption since de-ashing",
        "Verbrauch seit Entaschung",
    ),
    "empty_ash_box_after": ("Empty ash box after", "Aschebox leeren nach"),
    "full_load_hours": ("Full-load hours", "Volllaststunden"),
    "full_load_hours_since_service": (
        "Full-load hours since service",
        "Volllaststunden seit Wartung",
    ),
    "full_load_hours_since_cleaning": (
        "Full-load hours since cleaning",
        "Volllaststunden seit Reinigung",
    ),
    "ignition_count": ("Ignitions", "Zündungen"),
    "heating_run_count": ("Heating runs", "Heizbetriebe"),
    "fill_pellet_container": ("Fill pellet container", "Pelletsbehälter auffüllen"),
    "discharge_state": ("Discharge state", "Austragung"),
    "pellet_stock": ("Pellet stock", "Pelletvorrat"),
    "pellet_stock_warning_limit": ("Pellet stock warning limit", "Vorrat-Warngrenze"),
    "discharge_screw": ("Discharge screw", "Austragschnecke"),
    "heating_circuit_state": ("State", "Zustand"),
    "operating_mode": ("Operating mode", "Betrieb"),
    "heating_circuit_pump": ("Pump", "Pumpe"),
    "curve_offset": ("Heating curve offset", "Schieberposition"),
    "flow_at_minus_10": ("Flow at minus 10 °C", "Vorlauf bei minus 10 °C"),
    "flow_at_plus_10": ("Flow at plus 10 °C", "Vorlauf bei plus 10 °C"),
    "setback_reduction": ("Setback reduction", "Vorlauf-Absenkung"),
    "heating_limit_day": ("Heating limit (heating)", "Heizgrenze Heizen"),
    "heating_limit_night": ("Heating limit (setback)", "Heizgrenze Absenken"),
    "heat_button": ("Heating mode", "Heizen"),
    "auto_button": ("Automatic mode", "Automatik"),
    "setback_button": ("Setback mode", "Absenken"),
    "come_button": ("Coming home", "Kommen"),
    "go_button": ("Leaving home", "Gehen"),
    "hot_water_state": ("State", "Zustand"),
    "hot_water_temperature": ("Hot water temperature", "Warmwassertemperatur"),
    "hot_water_bottom_temperature": (
        "Hot water bottom temperature",
        "Warmwasser unten",
    ),
    "hot_water_target_temperature": (
        "Hot water target temperature",
        "Warmwasser-Solltemperatur",
    ),
    "charge_now_target_temperature": (
        "Target temperature for charge now",
        "Solltemperatur für Sofort laden",
    ),
    "hot_water_charging_pump": ("Charging pump", "Ladepumpe"),
    "buffer_state": ("State", "Zustand"),
    "buffer_charge_level": ("Charge level", "Ladezustand"),
    "buffer_top_temperature": ("Top temperature", "Temperatur oben"),
    "buffer_bottom_temperature": ("Bottom temperature", "Temperatur unten"),
    "buffer_sensor_2_temperature": ("Sensor 2 temperature", "Fühler 2"),
    "buffer_sensor_3_temperature": ("Sensor 3 temperature", "Fühler 3"),
    "buffer_sensor_4_temperature": ("Sensor 4 temperature", "Fühler 4"),
    "buffer_top_target_temperature": ("Top target temperature", "Solltemperatur oben"),
    "buffer_charge_now": ("Charge now", "Sofort laden"),
    "buffer_charge_count": ("Charges", "Pufferladungen"),
    "solar_state": ("State", "Zustand"),
    "collector_temperature": ("Collector temperature", "Kollektortemperatur"),
    "collector_pump": ("Collector pump", "Kollektorpumpe"),
    "storage_1_bottom_temperature": (
        "Storage 1 bottom temperature",
        "Speicher 1 unten",
    ),
    "fault_status": ("Fault status", "Störmeldung"),
}

FIXED: dict[str, dict[str, tuple[str, str]]] = {
    "binary_sensor": {"problem": ("Problem", "Problem")},
    "sensor": {"active_errors": ("Active errors", "Aktive Störungen")},
    "button": {"rediscover": ("Rediscover", "Neu erkennen")},
    "select": {"mode": ("Mode", "Betriebsart")},
}

WEBSERVICE_HELP = (
    "Request LAN access on meinETA (Settings › Webservices), then enable the web service "
    "on the touch panel (System settings › Internet & interfaces).",
    "Beantrage den LAN-Zugriff in meinETA (Einstellungen › Webservices) und aktiviere den "
    "Webservice anschließend am Touch-Display (Systemeinstellungen › Internet & Schnittstellen).",
)

# path -> (English, German); "{help}" is replaced by WEBSERVICE_HELP
TEXTS: dict[str, tuple[str, str]] = {
    "config.flow_title": ("ETA heater ({host})", "ETA-Heizung ({host})"),
    "config.step.user.title": ("Connect to ETA heater", "Mit ETA-Heizung verbinden"),
    "config.step.user.data.host": ("Host", "Host"),
    "config.step.user.data_description.host": (
        "IP address or hostname of the ETAtouch panel.",
        "IP-Adresse oder Hostname des ETAtouch-Displays.",
    ),
    "config.step.reconfigure.title": ("Change connection", "Verbindung ändern"),
    "config.step.reconfigure.data.host": ("Host", "Host"),
    "config.step.discovery_confirm.title": ("ETA heater found", "ETA-Heizung gefunden"),
    "config.step.discovery_confirm.description": (
        "Set up the ETA heater at {host}?",
        "Die ETA-Heizung unter {host} einrichten?",
    ),
    "config.progress.discover": (
        "Reading the heater's configuration. This takes about half a minute.",
        "Die Konfiguration der Heizung wird gelesen. Das dauert etwa eine halbe Minute.",
    ),
    "config.error.webservice_disabled": (
        "The heater refused the connection; its web service is probably not enabled. {help}",
        "Die Heizung hat die Verbindung abgelehnt; der Webservice ist vermutlich nicht aktiviert. {help}",
    ),
    "config.error.cannot_connect": (
        "Cannot reach the heater. Check the address.",
        "Die Heizung ist nicht erreichbar. Prüfe die Adresse.",
    ),
    "config.error.not_eta_device": (
        "This device does not answer like an ETAtouch panel.",
        "Dieses Gerät antwortet nicht wie ein ETAtouch-Display.",
    ),
    "config.error.unsupported_api": (
        "The heater firmware is too old (ETAtouch API 1.2 or newer is required).",
        "Die Firmware der Heizung ist zu alt (ETAtouch-API 1.2 oder neuer erforderlich).",
    ),
    "config.error.unknown": ("Unexpected error.", "Unerwarteter Fehler."),
    "config.abort.already_configured": (
        "This heater is already configured.",
        "Diese Heizung ist bereits eingerichtet.",
    ),
    "config.abort.not_eta_device": (
        "The discovered device is not an ETAtouch panel.",
        "Das gefundene Gerät ist kein ETAtouch-Display.",
    ),
    "config.abort.no_components": (
        "No supported values were found on this heater.",
        "Auf dieser Heizung wurden keine unterstützten Werte gefunden.",
    ),
    "config.abort.discovery_failed": (
        "Reading the heater's configuration failed.",
        "Das Lesen der Konfiguration ist fehlgeschlagen.",
    ),
    "config.abort.wrong_device": (
        "This address belongs to a different heater.",
        "Diese Adresse gehört zu einer anderen Heizung.",
    ),
    "config.abort.reconfigure_successful": (
        "The connection was updated.",
        "Die Verbindung wurde aktualisiert.",
    ),
    "options.step.init.data.scan_interval": (
        "Update interval",
        "Aktualisierungsintervall",
    ),
    "options.step.init.data_description.scan_interval": (
        "Seconds between updates (ETA recommends at least 30).",
        "Sekunden zwischen Aktualisierungen (ETA empfiehlt mindestens 30).",
    ),
    "issues.webservice_unavailable.title": (
        "ETA web service unavailable",
        "ETA-Webservice nicht verfügbar",
    ),
    "issues.webservice_unavailable.description": (
        "The heater at {host} refuses connections. Check that its web service is still enabled. {help}",
        "Die Heizung unter {host} lehnt Verbindungen ab. Prüfe, ob der Webservice noch aktiviert ist. {help}",
    ),
    "exceptions.cannot_connect.message": (
        "Cannot connect to the heater: {error}",
        "Keine Verbindung zur Heizung: {error}",
    ),
    "exceptions.update_failed.message": (
        "Updating from the heater failed: {error}",
        "Aktualisierung von der Heizung fehlgeschlagen: {error}",
    ),
    "exceptions.webservice_unavailable.message": (
        "The heater's web service refused the connection.",
        "Der Webservice der Heizung hat die Verbindung abgelehnt.",
    ),
    "exceptions.write_failed.message": (
        "Writing to the heater failed: {error}",
        "Schreiben auf die Heizung fehlgeschlagen: {error}",
    ),
    "exceptions.rediscover_failed.message": (
        "Rediscovering the heater failed: {error}",
        "Neuerkennung der Heizung fehlgeschlagen: {error}",
    ),
}

PLATFORM_FOR_KIND = {
    Kind.SETTING: "number",
    Kind.SWITCH: "switch",
    Kind.SELECT: "select",
    Kind.ACTION: "button",
}

MODE_STATES: dict[str, tuple[str, str]] = {
    "auto": ("Automatic", "Automatik"),
    "heating": ("Heating", "Heizen"),
    "setback": ("Setback", "Absenken"),
}


# pyetatouch STATE_KEYS values: (English, German)
STATE_NAMES: dict[str, tuple[str, str]] = {
    "off": ("Off", "Aus"),
    "on": ("On", "Ein"),
    "ready": ("Ready", "Bereit"),
    "charged": ("Charged", "Geladen"),
    "full": ("Full", "Voll"),
    "deashing": ("De-ashing", "Entaschen"),
    "changing_position": ("Changing position", "Position wechseln"),
    "flushing": ("Flushing", "Spülen"),
    "starting": ("Starting", "Startvorgang"),
    "running": ("Running", "In Betrieb"),
    "conveying": ("Conveying", "Fördern"),
    "heating": ("Heating", "Heizen"),
    "setback": ("Setback", "Absenken"),
    "charging": ("Charging", "Laden"),
    "shutting_down": ("Shutting down", "Abstellen"),
    "ember_burnout": ("Ember burn-out", "Glutabbrand"),
    "fault": ("Fault", "Störung"),
    "locked": ("Locked", "Verriegelt"),
    "ember_burnout_locked": (
        "Ember burn-out (locked)",
        "Glutabbrand wegen Verriegelung",
    ),
    "pellet_mode": ("Pellet mode", "Pelletsbetrieb"),
    "switching_to_log_wood": (
        "Switching to log wood",
        "Umschaltung auf Stückholzbetrieb",
    ),
    "fuse_defective": ("Fuse defective", "Sicherung defekt"),
    "no_terminal": ("No terminal assigned", "Keine Klemme zugewiesen"),
    "terminal_unavailable": ("Terminal unavailable", "Klemme nicht verfügbar"),
    "no": ("No", "Nein"),
    "yes": ("Yes", "Ja"),
    "not_full": ("Not full", "Nicht voll"),
    "demand": ("Demand", "Bedarf"),
    "suction": ("Suction", "Saugen"),
    "discharge_overrun": ("Discharge overrun", "Austragung Nachlauf"),
    "turbine_overrun": ("Suction turbine overrun", "Saugturbine Nachlauf"),
    "overrun_standby": ("Overrun standby", "Nachlauf Standby"),
    "standby_boiler": ("Standby (boiler)", "Standby Kessel"),
    "standby_discharge": ("Standby (discharge)", "Standby Austragung"),
    "discharge_error": ("Discharge error", "Austragung Fehler"),
    "suction_time_exceeded": ("Maximum suction time exceeded", "Fehler Saugzeit Max"),
    "vacation": ("Vacation", "Urlaub"),
    "screed_drying": ("Screed drying", "Estrich"),
    "error": ("Error", "Fehler"),
    "ok": ("OK", "OK"),
    "low": ("Low", "Niedrig"),
    "medium": ("Medium", "Mittel"),
    "high": ("High", "Hoch"),
}


def _set(tree: dict[str, Any], path: str, text: str) -> None:
    *parents, leaf = path.split(".")
    for part in parents:
        tree = tree.setdefault(part, {})
    tree[leaf] = text


def build(lang: int) -> dict[str, Any]:
    """Build the translation tree for index 0 (en) or 1 (de)."""
    tree: dict[str, Any] = {}
    for path, texts in TEXTS.items():
        _set(tree, path, texts[lang].replace("{help}", WEBSERVICE_HELP[lang]))
    entity: dict[str, Any] = tree.setdefault("entity", {})
    states = {key: STATE_NAMES[key][lang] for key in sorted(set(STATE_KEYS.values()))}
    for entry in CATALOG:
        name = NAMES[entry.key][lang]
        sensor: dict[str, Any] = {"name": name}
        if entry.kind in (Kind.STATE, Kind.SELECT):
            sensor["state"] = states
        entity.setdefault("sensor", {})[entry.key] = sensor
        if platform := PLATFORM_FOR_KIND.get(entry.kind):
            item: dict[str, Any] = {"name": name}
            if entry.kind is Kind.SELECT:
                item["state"] = states
            entity.setdefault(platform, {})[entry.key] = item
    for platform, names in FIXED.items():
        for key, texts in names.items():
            entity.setdefault(platform, {})[key] = {"name": texts[lang]}
    entity["select"]["mode"]["state"] = {
        key: texts[lang] for key, texts in MODE_STATES.items()
    }
    return tree


def main() -> None:
    """Write the files."""
    en, de = build(0), build(1)
    (ROOT / "translations").mkdir(exist_ok=True)
    for path, data in (
        (ROOT / "strings.json", en),
        (ROOT / "translations" / "en.json", en),
        (ROOT / "translations" / "de.json", de),
    ):
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
