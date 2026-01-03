"""Tests for ABB FIMER PVI VSN REST diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

from custom_components.abb_fimer_pvi_vsn_rest.diagnostics import async_get_config_entry_diagnostics

from .conftest import TEST_HOST, TEST_LOGGER_SN, TEST_VSN_MODEL


async def test_diagnostics_redacts_sensitive_data(
    hass,
    mock_config_entry,
    mock_coordinator: MagicMock,
    mock_normalized_data: dict,
) -> None:
    """Test that diagnostics redacts sensitive information."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_coordinator.data = mock_normalized_data
    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Check structure
    assert "config_entry" in diagnostics
    assert "coordinator" in diagnostics

    # Verify password is redacted
    config_data = diagnostics["config_entry"]["data"]
    assert config_data.get("password") == "**REDACTED**"

    # Verify other data is present
    assert config_data.get("host") == TEST_HOST


async def test_diagnostics_includes_coordinator_data(
    hass,
    mock_config_entry,
    mock_coordinator: MagicMock,
    mock_normalized_data: dict,
) -> None:
    """Test that diagnostics includes coordinator information."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_coordinator.data = mock_normalized_data
    mock_coordinator.last_update_success = True
    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Check coordinator info
    coordinator_info = diagnostics["coordinator"]
    assert "vsn_model" in coordinator_info
    assert coordinator_info["vsn_model"] == TEST_VSN_MODEL
    assert "last_update_success" in coordinator_info


async def test_diagnostics_includes_discovery_result(
    hass,
    mock_config_entry,
    mock_coordinator: MagicMock,
    mock_discovery_result,
    mock_normalized_data: dict,
) -> None:
    """Test that diagnostics includes discovery result."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_coordinator.data = mock_normalized_data
    mock_coordinator.discovery_result = mock_discovery_result
    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Check discovery result
    assert "discovery_result" in diagnostics["coordinator"]
    discovery = diagnostics["coordinator"]["discovery_result"]
    assert discovery["logger_sn"] == TEST_LOGGER_SN
    assert discovery["vsn_model"] == TEST_VSN_MODEL
