# ETA touch for Home Assistant

Local integration for ETA pellet and wood boilers with an **ETAtouch** panel, based on [pyetatouch](https://github.com/g4bri3lDev/pyetatouch).

- Setup needs only the heater's address (or one click when Home Assistant discovers it).
- One request per update; every function block (boiler, heating circuits, hot water, buffer, …) becomes its own device named like on the panel.
- Set-points, modes and switches can be controlled from Home Assistant.

## Requirements

The ETAtouch web service must be enabled: request LAN access on meinETA (Settings › Webservices), then enable it on the touch panel (System settings › Internet & interfaces).

## Missing a value?

Open a *Catalog request* in [pyetatouch](https://github.com/g4bri3lDev/pyetatouch/issues) and attach the output of `pyetatouch dump <heater-ip> -o eta-dump.json`.

## Brand assets

The icon and logo in `custom_components/eta_touch/brand/` are derived from the official ETA logo (source: [ETA Heiztechnik GmbH](https://www.eta.co.at)) and are used only in connection with ETA products. ETA and the η logo are trademarks of ETA Heiztechnik GmbH; this project is not affiliated with or endorsed by ETA.
