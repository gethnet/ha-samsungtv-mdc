"""Entity tests for Samsung MDC."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")
pytest.importorskip("homeassistant")
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import entity_registry as er

from samsungtv_mdc.api import SamsungMDCDeviceInfo, SamsungMDCStatus, SamsungMDCClient
from samsungtv_mdc.const import CONF_DISPLAY_ID, CONF_SCAN_INTERVAL, CONF_TIMEOUT, DOMAIN
from samsung_mdc.commands import INPUT_SOURCE, MUTE, PICTURE_ASPECT, POWER, VIRTUAL_REMOTE


@pytest.mark.asyncio
async def test_media_player_and_remote_commands(hass):
    """Ensure entities call through to client methods."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.10", CONF_PORT: 1515, CONF_DISPLAY_ID: 1},
        options={CONF_SCAN_INTERVAL: 10, CONF_TIMEOUT: 10},
        unique_id="192.168.1.10:1515:1",
    )

    status = SamsungMDCStatus(
        power_state=POWER.POWER_STATE.ON,
        volume=50,
        mute_state=MUTE.MUTE_STATE.OFF,
        input_source=INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
        picture_aspect=PICTURE_ASPECT.PICTURE_ASPECT_STATE.PC_16_9,
    )
    device_info = SamsungMDCDeviceInfo(model="DM65E", serial="SN123", software_version="1.0")

    client = MagicMock(spec=SamsungMDCClient)
    type(client).device_info = PropertyMock(return_value=device_info)
    client.host = entry.data[CONF_HOST]
    client.port = entry.data[CONF_PORT]
    client.display_id = entry.data[CONF_DISPLAY_ID]
    client.async_get_status = AsyncMock(return_value=status)
    client.async_ensure_device_info = AsyncMock()
    client.async_close = AsyncMock()
    client.async_set_power = AsyncMock()
    client.async_set_volume = AsyncMock()
    client.async_mute = AsyncMock()
    client.async_set_source = AsyncMock()
    client.async_send_keys = AsyncMock()
    client.async_set_manual_lamp = AsyncMock()
    client.async_set_color_temperature = AsyncMock()
    client.async_set_ticker = AsyncMock()

    with patch("samsungtv_mdc.__init__.SamsungMDCClient", return_value=client):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    media_player_entity_id = entity_reg.async_get_entity_id(
        "media_player", DOMAIN, f"{entry.unique_id}-media_player"
    )
    remote_entity_id = entity_reg.async_get_entity_id(
        "remote", DOMAIN, f"{entry.unique_id}-remote"
    )

    assert media_player_entity_id
    assert remote_entity_id

    await hass.services.async_call(
        "media_player", "turn_on", {"entity_id": media_player_entity_id}, blocking=True
    )
    await hass.services.async_call(
        "media_player",
        "set_volume_level",
        {"entity_id": media_player_entity_id, "volume_level": 0.6},
        blocking=True,
    )
    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": media_player_entity_id, "source": "Hdmi1"},
        blocking=True,
    )
    await hass.services.async_call(
        "media_player",
        "set_backlight",
        {"entity_id": media_player_entity_id, "brightness": 80},
        blocking=True,
    )
    await hass.services.async_call(
        "media_player",
        "set_color_temperature",
        {"entity_id": media_player_entity_id, "color_temperature": 50},
        blocking=True,
    )
    await hass.services.async_call(
        "media_player",
        "send_ticker",
        {
            "entity_id": media_player_entity_id,
            "message": "Hello",
            "position_horizontal": "left",
            "motion_on": True,
            "motion_direction": "right",
        },
        blocking=True,
    )
    await hass.services.async_call(
        "remote",
        "send_command",
        {"entity_id": remote_entity_id, "command": ["power"]},
        blocking=True,
    )

    client.async_set_power.assert_called_with(POWER.POWER_STATE.ON)
    client.async_set_volume.assert_called()
    client.async_set_source.assert_called()
    client.async_set_manual_lamp.assert_called_with(80)
    client.async_set_color_temperature.assert_called_with(50)
    client.async_set_ticker.assert_called()
    client.async_send_keys.assert_called_once()
    sent_keys = client.async_send_keys.call_args[0][0]
    assert list(sent_keys)[0] == VIRTUAL_REMOTE.KEY_CODE.KEY_POWER
