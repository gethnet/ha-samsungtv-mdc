"""Constants for the Samsung TV MDC integration."""

from datetime import timedelta
from enum import StrEnum

DOMAIN = "samsungtv_mdc"

CONF_DISPLAY_ID = "display_id"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PORT = "port"
DEFAULT_PORT = 1515
DEFAULT_TIMEOUT = 3
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
MIN_SCAN_INTERVAL = timedelta(seconds=15)
MAX_SCAN_INTERVAL = timedelta(minutes=15)


class PanelState(StrEnum):
    """Display panel power states."""

    OFF = "off"
    STARTING = "starting"
    ON = "on"
