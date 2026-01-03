"""Tests for ABB FIMER PVI VSN REST integration setup."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest import (
    STARTUP_LOGGED_KEY,
    async_setup_entry,
    async_unload_entry,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


async def test_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry,
    mock_discover_vsn_device: AsyncMock,
    mock_vsn_client: MagicMock,
) -> None:
    """Test successful setup of config entry."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
            return_value=mock_vsn_client,
        ),
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
            mock_discover_vsn_device,
        ),
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry",
        ),
    ):
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.runtime_data is not None
    assert mock_config_entry.runtime_data.coordinator is not None


async def test_setup_entry_discovery_failure(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test setup fails when discovery fails."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
        side_effect=Exception("Discovery failed"),
    ), pytest.raises(ConfigEntryNotReady, match="Discovery failed"):
        await async_setup_entry(hass, mock_config_entry)


async def test_setup_entry_first_refresh_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_discover_vsn_device: AsyncMock,
    mock_vsn_client: MagicMock,
) -> None:
    """Test setup fails when first data refresh fails."""
    mock_config_entry.add_to_hass(hass)

    # Make first refresh fail
    mock_vsn_client.get_normalized_data.side_effect = Exception("Fetch failed")

    with (
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
            return_value=mock_vsn_client,
        ),
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
            mock_discover_vsn_device,
        ),pytest.raises(ConfigEntryNotReady, match="Failed to fetch data")
    ):
        await async_setup_entry(hass, mock_config_entry)


async def test_unload_entry_success(
    hass: HomeAssistant,
    mock_config_entry,
    mock_coordinator,
) -> None:
    """Test successful unload of config entry."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    # Mock async_shutdown
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    mock_coordinator.async_shutdown.assert_called_once()


async def test_unload_entry_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_coordinator,
) -> None:
    """Test failed unload of config entry."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    # Mock async_shutdown
    mock_coordinator.async_shutdown = AsyncMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    # Shutdown should not be called on failed unload
    mock_coordinator.async_shutdown.assert_not_called()


async def test_startup_message_logged_once(
    hass: HomeAssistant,
    mock_config_entry,
    mock_discover_vsn_device: AsyncMock,
    mock_vsn_client: MagicMock,
) -> None:
    """Test startup message is only logged once per HA session."""
    mock_config_entry.add_to_hass(hass)

    # First setup - should log startup message
    with (
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
            return_value=mock_vsn_client,
        ),
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
            mock_discover_vsn_device,
        ),
        patch(
            "custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry",
        ),
    ):
        await async_setup_entry(hass, mock_config_entry)

    # Verify startup was logged
    assert hass.data.get(STARTUP_LOGGED_KEY) is True
