"""Data coordinator for Samsung MDC displays."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SamsungMDCClient, SamsungMDCError, SamsungMDCStatus
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SamsungMDCDataUpdateCoordinator(DataUpdateCoordinator[SamsungMDCStatus]):
    """Coordinator to keep MDC state in sync."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SamsungMDCClient,
        *,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=f"Samsung MDC {client.host}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> SamsungMDCStatus:
        """Fetch data from MDC."""
        try:
            return await self.client.async_get_status()
        except SamsungMDCError as err:
            raise UpdateFailed(str(err)) from err
