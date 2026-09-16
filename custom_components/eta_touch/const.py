"""Constants for the ETA touch integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "eta_touch"
MANUFACTURER: Final = "ETA Heiztechnik"

CONF_INSTALLATION: Final = "installation"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 600
ERRORS_INTERVAL: Final = timedelta(minutes=5)

EVENT_ERROR_RAISED: Final = f"{DOMAIN}_error_raised"
EVENT_ERROR_CLEARED: Final = f"{DOMAIN}_error_cleared"
