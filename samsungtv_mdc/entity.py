"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SamsungMDCClient
from .const import DOMAIN
from .coordinator import SamsungMDCDataUpdateCoordinator


class SamsungMDCEntity(CoordinatorEntity[SamsungMDCDataUpdateCoordinator]):
    """Base entity for Samsung MDC."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        unique_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._unique_id = unique_id
        self._attr_name = name
        self._device_name = name

    @property
    def client(self) -> SamsungMDCClient:
        """Return MDC client."""
        return self.coordinator.client

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata."""
        device = self.client.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.host}:{self.client.port}:{self.client.display_id}")},
            manufacturer="Samsung",
            model=device.model if device else None,
            name=self._device_name,
            sw_version=device.software_version if device else None,
            serial_number=device.serial if device else None,
        )
