"""Constants for the Samsung TV MDC integration."""

from datetime import timedelta

DOMAIN = "samsungtv_mdc"

CONF_DISPLAY_ID = "display_id"
CONF_PIN = "pin"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PORT = "port"
DEFAULT_PORT = 1515
DEFAULT_TIMEOUT = 5
DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)
MIN_SCAN_INTERVAL = timedelta(minutes=5)
MAX_SCAN_INTERVAL = timedelta(minutes=15)
