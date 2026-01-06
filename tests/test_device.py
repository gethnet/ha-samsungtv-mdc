"""Tests for Samsung MDC device wrapper."""
# ruff: noqa: S101,FBT001,FBT002,ARG001,EM101,ANN202

from __future__ import annotations

import pytest
from samsung_mdc import commands
from samsung_mdc.exceptions import MDCResponseError, MDCTimeoutError

from custom_components.samsungtv_mdc import coordinator
from custom_components.samsungtv_mdc.const import DEFAULT_PORT, DEFAULT_TIMEOUT
from custom_components.samsungtv_mdc.coordinator import SamsungMDCDevice

_EMPTY_RESPONSE_ARGS = ("Empty response", b"")
EXPECTED_CLIENTS_AFTER_RETRY = 2


class _DummyClient:
    """Simple MDC client stub."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.writer: object | None = object()
        self.closed = False
        self.calls: list[str] = []

    async def status(self, _display_id: int):
        """Return status or raise on first attempt."""
        self.calls.append("status")
        if self.should_fail:
            raise MDCTimeoutError("timeout")
        return (
            commands.POWER.POWER_STATE.ON,
            12,
            commands.MUTE.MUTE_STATE.OFF,
            commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
            None,
            None,
        )

    async def close(self):
        """Close the stub."""
        self.writer = None
        self.closed = True


@pytest.mark.asyncio
async def test_device_reconnects_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Device recreates client after a recoverable MDC timeout."""
    created_clients: list[_DummyClient] = []

    def _client_factory(
        target: str, timeout: float | None = None, pin: str | None = None
    ):
        client = _DummyClient(should_fail=len(created_clients) == 0)
        created_clients.append(client)
        return client

    monkeypatch.setattr(coordinator, "MDC", _client_factory)

    device = SamsungMDCDevice("example.com", 1, DEFAULT_PORT, None, DEFAULT_TIMEOUT)

    status = await device.async_status()

    expected_clients = EXPECTED_CLIENTS_AFTER_RETRY
    assert status[0] == commands.POWER.POWER_STATE.ON
    assert len(created_clients) == expected_clients
    assert created_clients[0].closed
    assert created_clients[1].calls == ["status"]


@pytest.mark.asyncio
async def test_device_ignores_empty_response_when_setting_power(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty response errors on power commands do not surface to callers."""
    created_clients: list[_DummyClient] = []

    class _PowerClient(_DummyClient):
        def __init__(self) -> None:
            super().__init__()
            self.should_fail = True

        async def power(self, display_id: int, data: list[commands.POWER.POWER_STATE]):
            self.calls.append(("power", display_id, data))
            if self.should_fail:
                self.should_fail = False
                raise MDCResponseError(*_EMPTY_RESPONSE_ARGS)

    def _client_factory(
        target: str, timeout: float | None = None, pin: str | None = None
    ):
        client = _PowerClient()
        created_clients.append(client)
        return client

    monkeypatch.setattr(coordinator, "MDC", _client_factory)

    device = SamsungMDCDevice("example.com", 1, DEFAULT_PORT, None, DEFAULT_TIMEOUT)

    await device.async_set_power(commands.POWER.POWER_STATE.ON)

    assert len(created_clients) == EXPECTED_CLIENTS_AFTER_RETRY
    assert created_clients[0].closed
    assert created_clients[0].calls == [("power", 1, [commands.POWER.POWER_STATE.ON])]
    assert created_clients[1].calls == []


@pytest.mark.asyncio
async def test_device_suppresses_connection_refused_when_setting_power(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection refused errors on power commands are treated as a one-off success."""
    created_clients: list[_DummyClient] = []

    class _RefusedClient(_DummyClient):
        def __init__(self) -> None:
            super().__init__()
            self.should_fail = True

        async def power(self, display_id: int, data: list[commands.POWER.POWER_STATE]):
            self.calls.append(("power", display_id, data))
            if self.should_fail:
                self.should_fail = False
                raise ConnectionRefusedError(111, "Connect call failed")

    def _client_factory(
        target: str, timeout: float | None = None, pin: str | None = None
    ):
        client = _RefusedClient()
        created_clients.append(client)
        return client

    monkeypatch.setattr(coordinator, "MDC", _client_factory)

    device = SamsungMDCDevice("example.com", 1, DEFAULT_PORT, None, DEFAULT_TIMEOUT)

    await device.async_set_power(commands.POWER.POWER_STATE.ON)

    assert len(created_clients) == EXPECTED_CLIENTS_AFTER_RETRY
    assert created_clients[0].closed
    assert created_clients[0].calls == [("power", 1, [commands.POWER.POWER_STATE.ON])]
    assert created_clients[1].calls == []
