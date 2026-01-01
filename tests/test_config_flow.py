"""Tests for the Samsung MDC config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType

from samsungtv_mdc.api import (
    SamsungMDCAuthError,
    SamsungMDCConnectionError,
    SamsungMDCDeviceInfo,
    SamsungMDCStatus,
    SamsungMDCTlsRequired,
)
from samsungtv_mdc.const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from samsung_mdc.commands import INPUT_SOURCE, MUTE, PICTURE_ASPECT, POWER


@pytest.mark.asyncio
async def test_form_success(hass):
    """Test successful user form."""
    user_input = {
        CONF_HOST: "192.168.1.10",
        CONF_PORT: DEFAULT_PORT,
        CONF_DISPLAY_ID: 1,
        CONF_PIN: "1234",
        CONF_NAME: "Lobby Display",
    }
    status = SamsungMDCStatus(
        power_state=POWER.POWER_STATE.ON,
        volume=10,
        mute_state=MUTE.MUTE_STATE.OFF,
        input_source=INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
        picture_aspect=PICTURE_ASPECT.PICTURE_ASPECT_STATE.PC_16_9,
    )
    device_info = SamsungMDCDeviceInfo(model="DM65E", serial="SN123", software_version="1.0")

    with patch(
        "samsungtv_mdc.config_flow.SamsungMDCClient",
        autospec=True,
    ) as mock_client:
        instance = mock_client.return_value
        instance.async_get_status = AsyncMock(return_value=status)
        instance.async_get_device_info = AsyncMock(return_value=device_info)
        instance.async_close = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "DM65E (192.168.1.10)"
    assert result["data"] == user_input
    assert result["options"] == {
        CONF_SCAN_INTERVAL: int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
    }


@pytest.mark.asyncio
async def test_form_cannot_connect(hass):
    """Test connection errors are handled."""
    user_input = {
        CONF_HOST: "192.168.1.10",
        CONF_PORT: DEFAULT_PORT,
        CONF_DISPLAY_ID: 1,
    }
    with patch(
        "samsungtv_mdc.config_flow.SamsungMDCClient",
        autospec=True,
    ) as mock_client:
        instance = mock_client.return_value
        instance.async_get_status.side_effect = SamsungMDCConnectionError("boom")
        instance.async_close = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_form_tls_required(hass):
    """Test TLS requirement is surfaced."""
    user_input = {
        CONF_HOST: "192.168.1.10",
        CONF_PORT: DEFAULT_PORT,
        CONF_DISPLAY_ID: 1,
    }
    with patch(
        "samsungtv_mdc.config_flow.SamsungMDCClient",
        autospec=True,
    ) as mock_client:
        instance = mock_client.return_value
        instance.async_get_status.side_effect = SamsungMDCTlsRequired("tls")
        instance.async_close = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "tls_required"


@pytest.mark.asyncio
async def test_form_invalid_auth(hass):
    """Test invalid pin path."""
    user_input = {
        CONF_HOST: "192.168.1.10",
        CONF_PORT: DEFAULT_PORT,
        CONF_DISPLAY_ID: 1,
        CONF_PIN: "9999",
    }
    with patch(
        "samsungtv_mdc.config_flow.SamsungMDCClient",
        autospec=True,
    ) as mock_client:
        instance = mock_client.return_value
        instance.async_get_status.side_effect = SamsungMDCAuthError("bad pin")
        instance.async_close = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}, data=user_input
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_options_flow(hass):
    """Test options are stored."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.10", CONF_PORT: 1515, CONF_DISPLAY_ID: 1},
        options={CONF_SCAN_INTERVAL: 30, CONF_TIMEOUT: 10},
        unique_id="192.168.1.10:1515:1",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL: 45, CONF_TIMEOUT: 20}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_SCAN_INTERVAL: 45, CONF_TIMEOUT: 20}
