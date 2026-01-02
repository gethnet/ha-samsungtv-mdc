"""Binary sensors for Samsung TV MDC."""

from __future__ import annotations

from samsung_mdc import commands

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungTVMDCConfigEntry
from .entity import SamsungMDCEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [SamsungMDCPowerBinarySensor(coordinator, entry.runtime_data.device_id)]
    )


class SamsungMDCPowerBinarySensor(SamsungMDCEntity, BinarySensorEntity):
    """Binary sensor tracking display power state."""

    _attr_translation_key = "power"
    _attr_name = "Power"

    def __init__(self, coordinator, device_id: str) -> None:
        """Initialize power binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-power"

    @property
    def is_on(self) -> bool:
        """Return whether the display is on."""
        return self.coordinator.data.power == commands.POWER.POWER_STATE.ON
