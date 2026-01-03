"""Buttons for Samsung TV MDC."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import SamsungMDCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SamsungTVMDCConfigEntry
    from .coordinator import SamsungMDCDataUpdateCoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC buttons."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [SamsungMDCRefreshButton(coordinator, entry.runtime_data.device_id)]
    )


class SamsungMDCRefreshButton(SamsungMDCEntity, ButtonEntity):
    """Button to trigger immediate refresh."""

    _attr_translation_key = "refresh"
    _attr_name = "Refresh now"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize refresh button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-refresh"

    async def async_press(self) -> None:
        """Request a data refresh."""
        await self.coordinator.async_request_refresh()
