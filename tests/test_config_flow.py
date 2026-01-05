"""Tests for the Samsung MDC config flow."""
# ruff: noqa: S101, ANN202

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsungtv_mdc import config_flow
from custom_components.samsungtv_mdc.config_flow import (
    CannotConnect,
    ConfigFlow,
    InvalidAuth,
    OptionsFlowHandler,
)
from custom_components.samsungtv_mdc.const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.asyncio


def _user_input(
    host: str = "10.0.0.1",
    display_id: int = 1,
    port: int = DEFAULT_PORT,
    pin: str = "1234",
    scan_interval: int = 10,
):
    return {
        CONF_HOST: host,
        CONF_DISPLAY_ID: display_id,
        CONF_PORT: port,
        CONF_PIN: pin,
        CONF_SCAN_INTERVAL: scan_interval,
    }


async def test_user_flow_success(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """A successful user step creates the entry with normalized values."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return f"{_host}:{_port} (ok)"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.handler = DOMAIN
    flow.context = {"source": "user"}

    result = await flow.async_step_user(_user_input())

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.0.0.1:1515 (ok)"
    assert result["data"][CONF_PIN] == "1234"
    assert result["data"][CONF_PORT] == DEFAULT_PORT
    assert result["data"][CONF_DISPLAY_ID] == 1


async def test_user_flow_invalid_pin(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Invalid pin returns form error and does not call connector."""
    called = False

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        nonlocal called
        called = True
        return "ignored"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.handler = DOMAIN
    flow.context = {"source": config_entries.SOURCE_USER}

    bad_input = _user_input(pin="abcd")
    result = await flow.async_step_user(bad_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["pin"] == "invalid_pin"
    assert called is False


async def test_user_flow_cannot_connect(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Connection errors surface as cannot_connect."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        raise CannotConnect

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.handler = DOMAIN
    flow.context = {"source": "user"}

    result = await flow.async_step_user(_user_input())

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_flow_invalid_auth(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Auth errors surface as invalid_auth."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        raise InvalidAuth

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.handler = DOMAIN
    flow.context = {"source": "user"}

    result = await flow.async_step_user(_user_input())

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_flow_already_configured(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Existing entry aborts new flow with same unique ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "10.0.0.1",
            CONF_DISPLAY_ID: 1,
            CONF_PORT: DEFAULT_PORT,
            CONF_PIN: "9999",
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        unique_id="10.0.0.1-1",
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_hass(hass_asyncio)

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return "ok"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.handler = DOMAIN
    flow.context = {"source": "user"}

    with pytest.raises(data_entry_flow.AbortFlow):
        await flow.async_step_user(_user_input(pin="1234"))
    assert entry.data[CONF_PIN] == "1234"
    assert entry.data[CONF_PORT] == DEFAULT_PORT


async def test_options_flow_updates_settings(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Options flow saves updated connection values."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return "ok"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_user_input(scan_interval=DEFAULT_SCAN_INTERVAL),
        options={CONF_SCAN_INTERVAL: 7},
    )
    entry.add_to_hass(hass_asyncio)
    flow = OptionsFlowHandler(entry)
    flow.hass = hass_asyncio
    expected_display_id = 2
    expected_port = 1516
    expected_scan = 6
    new_input = _user_input(
        host="10.0.0.2",
        display_id=expected_display_id,
        port=expected_port,
        scan_interval=expected_scan,
    )

    result = await flow.async_step_init(new_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "10.0.0.2"
    assert result["data"][CONF_DISPLAY_ID] == expected_display_id
    assert result["data"][CONF_PORT] == expected_port
    assert result["data"][CONF_PIN] == "1234"
    assert result["data"][CONF_SCAN_INTERVAL] == expected_scan


async def test_options_flow_invalid_pin(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Options flow rejects invalid pin."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return "ok"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    entry = MockConfigEntry(domain=DOMAIN, data=_user_input())
    flow = OptionsFlowHandler(entry)
    flow.hass = hass_asyncio

    result = await flow.async_step_init(_user_input(pin="bad"))

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["pin"] == "invalid_pin"


async def test_reconfigure_updates_entry(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Reconfigure step stores new settings and aborts with success."""
    updated_settings = {}

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return "ok"

    def _fake_update(
        _hass: HomeAssistant, _entry: MockConfigEntry, settings: dict
    ) -> None:
        updated_settings.update(settings)

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    monkeypatch.setattr(config_flow, "_update_entry_configuration", _fake_update)
    entry = MockConfigEntry(domain=DOMAIN, data=_user_input())
    entry.add_to_hass(hass_asyncio)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.context = {"entry_id": entry.entry_id}
    new_input = _user_input(
        host="10.0.0.3", display_id=3, port=1517, pin="5678", scan_interval=5
    )

    result = await flow.async_step_reconfigure(new_input)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert updated_settings == new_input


async def test_reconfigure_invalid_pin(
    monkeypatch: pytest.MonkeyPatch, hass_asyncio: HomeAssistant
) -> None:
    """Reconfigure step returns form errors on invalid pin."""

    async def _fake_try(_host: str, _display_id: int, _port: int, _pin: str) -> str:
        return "ok"

    monkeypatch.setattr(config_flow, "_try_connect", _fake_try)
    entry = MockConfigEntry(domain=DOMAIN, data=_user_input())
    entry.add_to_hass(hass_asyncio)
    flow = ConfigFlow()
    flow.hass = hass_asyncio
    flow.context = {"entry_id": entry.entry_id}

    result = await flow.async_step_reconfigure(_user_input(pin="bad"))

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["pin"] == "invalid_pin"
