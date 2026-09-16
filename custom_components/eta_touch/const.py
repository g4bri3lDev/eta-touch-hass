"""Constants for the ETA touch integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "eta_touch"
MANUFACTURER: Final = "ETA Heiztechnik"
MEINETA_URL: Final = "https://www.meineta.at"

CONF_INSTALLATION: Final = "installation"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CALORIFIC_VALUE: Final = "calorific_value"

DEFAULT_SCAN_INTERVAL: Final = 60
# kWh per kg of wood pellets (ENplus A1: about 4.6-5.3; ETA and common practice use 4.8)
DEFAULT_CALORIFIC_VALUE: Final = 4.8
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 600
ERRORS_INTERVAL: Final = timedelta(minutes=5)

EVENT_ERROR_RAISED: Final = f"{DOMAIN}_error_raised"
EVENT_ERROR_CLEARED: Final = f"{DOMAIN}_error_cleared"
