"""Shared test fixtures."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest_asyncio
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component import plugins
from pytest_homeassistant_custom_component.common import async_test_home_assistant

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from homeassistant.core import HomeAssistant


@pytest_asyncio.fixture
async def hass_asyncio() -> AsyncGenerator[HomeAssistant]:
    """Provide hass fixture compatible with pytest-asyncio strict mode."""
    loop = asyncio.get_running_loop()
    async with async_test_home_assistant(loop) as hass:
        yield hass

        loaded_entries = [
            entry
            for entry in hass.config_entries.async_entries()
            if entry.state is ConfigEntryState.LOADED
        ]
        if loaded_entries:
            await asyncio.gather(
                *(
                    plugins.create_eager_task(
                        hass.config_entries.async_unload(config_entry.entry_id),
                        loop=hass.loop,
                    )
                    for config_entry in loaded_entries
                )
            )
        await hass.async_stop(force=True)
