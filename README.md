# ETA touch for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/g4bri3lDev/eta-touch-hass)](https://github.com/g4bri3lDev/eta-touch-hass/releases)

Local Home Assistant integration for **ETA pellet and wood boilers** with an **ETAtouch** touch panel, built on the [pyetatouch](https://github.com/g4bri3lDev/pyetatouch) library.

- **No configuration choices:** enter the heater's address (or confirm when Home Assistant finds it) — that's it.
- **Structured like your panel:** every function block (boiler, heating circuits, hot water, buffer, solar, pellet store, …) becomes its own device, named as on the panel.
- **Efficient:** one request per update for all values.
- **Control:** heating-circuit mode, on/off, set-points, hot-water charging, pellet suction time and more.
- **Energy dashboard:** heat energy calculated from the pellet consumption.
- **Faults:** problem sensor, latest error and events for automations.
- **Local only:** talks directly to the panel in your network; no cloud.

> [!NOTE]
> This is an early release (0.x). Values are matched against a catalog that has so far been verified on an ETA PC 25. Other models and function blocks work, but may expose fewer values — see [Missing a value?](#missing-a-value)

## Requirements

- Home Assistant **2026.9** or newer
- An ETA heater with **ETAtouch** and firmware that provides the web service API **1.2** or newer
- The **ETAtouch web service** enabled:
  1. On [meinETA](https://www.meineta.at), open *Settings › Webservices* and request LAN access.
  2. On the touch panel, open *System settings › Internet & interfaces* and enable the web service.

The web service always listens on port 8080 in your local network.

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮) › *Custom repositories*.
2. Add `https://github.com/g4bri3lDev/eta-touch-hass` with category *Integration*.
3. Search for **ETA touch**, download it and restart Home Assistant.

### Manual

Copy `custom_components/eta_touch` into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

## Setup

Home Assistant usually discovers the heater on its own (*Settings › Devices & services* shows **ETA touch** as discovered). Otherwise:

1. *Settings › Devices & services › Add integration › ETA touch*
2. Enter the IP address or hostname of the touch panel.
3. The integration reads the heater's configuration. This takes about half a minute.

That's all — there is nothing to select. The setup dialog explains what to check if the web service is disabled, the device isn't an ETAtouch panel, or the firmware is too old.

To poll efficiently, the integration creates a *variable set* on the panel (a list of the values it reads). It is rebuilt whenever the integration starts and deleted when the integration is unloaded or removed.

## What you get

### Devices

| Device | Contains |
|---|---|
| **ETAtouch** | Problem, active errors, latest error, *Rediscover* button |
| One device per function block, e.g. **Kessel**, **HK**, **FBH**, **WW**, **PufferFlex**, **Solar**, **Lager**, **Sys** | The values of that block (the names are the ones configured on your panel) |

### Entities

Commonly used values are enabled by default; everything else is available but disabled (*device page › entities › show disabled*). Examples:

| Function block | Enabled by default |
|---|---|
| Boiler | state, boiler/return/flue-gas temperature, target temperature, pressure, pellet container state and content, total consumption, consumption since the ash box was emptied, full-load hours, heat energy, on/off switch, pellet suction time |
| Heating circuit | state, operating mode, flow temperature, **mode** (auto / heating / setback), heating-curve offset, on/off switch, *coming home* / *leaving home* buttons (disabled) |
| Hot water | state, temperature, target temperature, *charge now*, on/off switch |
| Buffer | state, charge level, top and bottom temperature, *charge now* |
| Solar | state, collector temperature, collector pump |
| Pellet store | discharge state, pellet stock |
| System | outdoor temperature |

The on/off switch of a function block carries the device's name (e.g. `switch.hk`); *on* means the block is switched on, not that it is currently heating.

States (e.g. *Ready*, *Charging*, *Not full*) are translated into your Home Assistant language, independent of the panel language.

### Controlling the heater

Numbers, switches, selects, time entities and buttons write directly to the heater. Values are checked against the limits the heater reports before they are sent.

> [!WARNING]
> These entities change real settings of your heating system. Only change what you understand, and be careful with automations that write frequently.

## Options

*Settings › Devices & services › ETA touch › Configure*

| Option | Default | Description |
|---|---|---|
| Update interval | 60 s | How often values are read (30–600 s). |
| Pellet calorific value | 4.8 kWh/kg | Used for the heat energy sensor. |

## Energy dashboard

Each boiler has a **Heat energy** sensor (kWh), calculated as *total pellet consumption × calorific value*. Home Assistant has no dedicated source type for pellet heating, so add it as a **gas source** (gas sources accept energy sensors in kWh):

1. *Settings › Dashboards › Energy*
2. Under **Gas consumption**, choose *Add gas source*.
3. **Gas usage:** select the boiler's *Heat energy* sensor.
4. **Name** (optional): e.g. *Pellet heating*, so the graphs don't just say "Gas".
5. **Gas flow rate:** leave empty — it only accepts volume flow sensors (m³/h, L/min) from gas meters.
6. **Costs** (optional): *Use a static price* per kWh (see below), or an entity that provides the price.

### Price per kWh

```
price per kWh = pellet price per tonne ÷ 1000 ÷ calorific value
```

Example: 350 €/t at 4.8 kWh/kg → 350 ÷ 1000 ÷ 4.8 ≈ **0.073 €/kWh**.

### Good to know

- The dashboard starts counting when the source is added (from the next full hour); past consumption is not imported.
- Set the **calorific value** (*Configure* on the integration, default 4.8 kWh/kg) to the value on your delivery note *before* adding the source — changing it later causes a one-time jump in the statistics.
- The sensor shows the energy contained in the burned pellets. The heat actually delivered is lower by the boiler efficiency (typically 90–95 %).

## Error events

When the heater reports a new fault, the integration fires `eta_touch_error_raised`; when it is cleared, `eta_touch_error_cleared`. Faults are checked every 5 minutes.

| Field | Example |
|---|---|
| `entry_id` | ID of the config entry |
| `component` | `Kessel` |
| `message` | `Wasserdruck zu niedrig` |
| `priority` | `Error` |
| `description` | detailed text from the panel |
| `time` | `2026-09-16T12:47:50` |

```yaml
automation:
  - alias: Notify about heater faults
    triggers:
      - trigger: event
        event_type: eta_touch_error_raised
    actions:
      - action: notify.mobile_app_phone
        data:
          title: "Heater: {{ trigger.event.data.component }}"
          message: "{{ trigger.event.data.message }}"
```

## Rediscover

After changing the heater's configuration (new function blocks, renamed blocks on the panel), press **Rediscover** on the ETAtouch device. Entities that no longer exist are removed automatically; your own renames in Home Assistant are kept.

## Troubleshooting

| Problem | What to do |
|---|---|
| Setup says the web service is probably not enabled | Enable it on meinETA and on the panel (see [Requirements](#requirements)). |
| "Firmware too old" | The panel needs web service API 1.2; update the heater's software. |
| A repair issue says the web service is unavailable | The panel refuses connections — check that the web service is still enabled. The issue disappears once the heater answers again. |
| All entities are briefly unavailable | Normal while the integration reloads (e.g. after enabling entities or changing options). |
| A value is missing | See [Missing a value?](#missing-a-value) |

For bug reports, attach the diagnostics (*Settings › Devices & services › ETA touch › ⋮ › Download diagnostics*); the address and MAC are removed automatically.

## Missing a value?

Values are matched against a catalog of known ETA variable IDs. If something you see on the panel is missing, create a structure report (no values, no addresses, no panel names) and open a *Catalog request* in [pyetatouch](https://github.com/g4bri3lDev/pyetatouch/issues/new/choose):

```bash
pip install pyetatouch
pyetatouch dump <heater-ip> -o eta-dump.json
```

## Limitations

- Heating and charging time windows can't be edited yet.
- Modbus TCP is not supported yet (only the web service).

## Removal

Delete the integration under *Settings › Devices & services*. Its variable set is removed from the heater automatically.

## Brand assets

The icon and logo in `custom_components/eta_touch/brand/` are derived from the official ETA logo (source: [ETA Heiztechnik GmbH](https://www.eta.co.at)) and are used only in connection with ETA products. ETA and the η logo are trademarks of ETA Heiztechnik GmbH; this project is not affiliated with or endorsed by ETA.
