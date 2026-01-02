"""Base entity for Samsung TV MDC."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungMDCDataUpdateCoordinator


class SamsungMDCEntity(CoordinatorEntity[SamsungMDCDataUpdateCoordinator]):
    """Common entity for Samsung MDC."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        state = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Samsung",
            name=state.device_name or f"Samsung MDC {self._device_id}",
            model=state.model_number,
            serial_number=state.serial_number,
            sw_version=state.software_version,
        )
