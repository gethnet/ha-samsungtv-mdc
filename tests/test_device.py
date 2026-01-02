"""Tests for Samsung MDC device wrapper."""

from __future__ import annotations

import pytest
from samsung_mdc import commands
from samsung_mdc.exceptions import MDCTimeoutError

from custom_components.samsungtv_mdc.const import DEFAULT_PORT, DEFAULT_TIMEOUT
from custom_components.samsungtv_mdc import coordinator
from custom_components.samsungtv_mdc.coordinator import SamsungMDCDevice


class _DummyClient:
    """Simple MDC client stub."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.writer: object | None = object()
        self.closed = False
        self.calls: list[str] = []

    async def status(self, display_id: int):
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

    assert status[0] == commands.POWER.POWER_STATE.ON
    assert len(created_clients) == 2  # initial failure + recreated client
    assert created_clients[0].closed
    assert created_clients[1].calls == ["status"]
