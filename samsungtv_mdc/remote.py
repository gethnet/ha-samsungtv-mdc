"""Remote entity for Samsung MDC virtual remote."""

from __future__ import annotations

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from samsung_mdc.commands import VIRTUAL_REMOTE

from .entity import SamsungMDCEntity
from .coordinator import SamsungMDCDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung MDC remote."""
    data = entry.runtime_data
    assert data is not None
    coordinator = data.coordinator
    async_add_entities(
        [
            SamsungMDCRemote(
                coordinator=coordinator,
                unique_id=f"{entry.unique_id}-remote",
                name=f"{entry.title} Remote",
            )
        ]
    )


class SamsungMDCRemote(SamsungMDCEntity, RemoteEntity):
    """Send remote commands via MDC."""

    def __init__(
        self,
        *,
        coordinator: SamsungMDCDataUpdateCoordinator,
        unique_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, unique_id, name)
        self._attr_should_poll = False

    @property
    def available(self) -> bool:
        """Return availability."""
        return self.coordinator.last_update_success

    async def async_send_command(self, commands: list[str], **kwargs) -> None:
        """Send commands via virtual remote."""
        key_codes: list[VIRTUAL_REMOTE.KEY_CODE] = []
        for command in commands:
            normalized = command.upper().strip()
            if normalized != "DISCRET_POWER_OFF" and not normalized.startswith("KEY_"):
                normalized = f"KEY_{normalized}"
            try:
                key_codes.append(VIRTUAL_REMOTE.KEY_CODE[normalized])
            except KeyError as err:
                raise ValueError(f"Unsupported command: {command}") from err

        await self.client.async_send_keys(key_codes)
        await self.coordinator.async_request_refresh()
