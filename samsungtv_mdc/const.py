"""Constants for the SamsungTV MDC integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "samsungtv_mdc"
PLATFORMS: Final[list[Platform]] = [Platform.MEDIA_PLAYER, Platform.REMOTE]

CONF_DISPLAY_ID: Final = "display_id"
CONF_PIN: Final = "pin"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TIMEOUT: Final = "timeout"

DEFAULT_NAME: Final = "Samsung MDC Display"
DEFAULT_PORT: Final = 1515
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
DEFAULT_TIMEOUT: Final = 10
