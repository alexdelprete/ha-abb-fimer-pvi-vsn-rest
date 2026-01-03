"""Tests for ABB FIMER PVI VSN REST coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.const import DEFAULT_FAILURES_THRESHOLD, DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.coordinator import ABBFimerPVIVSNRestCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import (
    TEST_INVERTER_SN,
    TEST_LOGGER_SN,
    TEST_SCAN_INTERVAL,
    TEST_VSN_MODEL,
    MockDiscoveryResult,
)


@pytest.fixture
def coordinator(
    mock_hass: MagicMock,
    mock_vsn_client: MagicMock,
    mock_discovery_result: MockDiscoveryResult,
) -> ABBFimerPVIVSNRestCoordinator:
    """Create a real coordinator for testing."""
    return ABBFimerPVIVSNRestCoordinator(
        hass=mock_hass,
        client=mock_vsn_client,
        update_interval=timedelta(seconds=TEST_SCAN_INTERVAL),
        discovery_result=mock_discovery_result,
    )


async def test_coordinator_init(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_discovery_result: MockDiscoveryResult,
) -> None:
    """Test coordinator initialization."""
    assert coordinator.vsn_model == TEST_VSN_MODEL
    assert coordinator.discovery_result == mock_discovery_result
    assert len(coordinator.discovered_devices) == 2
    assert coordinator._consecutive_failures == 0
    assert coordinator._repair_issue_created is False
    assert coordinator._failure_start_time is None


async def test_coordinator_update_success(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_vsn_client: MagicMock,
    mock_normalized_data: dict,
) -> None:
    """Test successful data update."""
    # Perform update
    data = await coordinator._async_update_data()

    # Verify client was called
    mock_vsn_client.get_normalized_data.assert_called_once()

    # Verify data was returned
    assert data == mock_normalized_data
    assert TEST_INVERTER_SN in data
    assert TEST_LOGGER_SN in data


async def test_coordinator_update_failure(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_vsn_client: MagicMock,
) -> None:
    """Test update failure raises UpdateFailed."""
    mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError(
        "Connection failed"
    )

    with pytest.raises(UpdateFailed, match="Connection failed"):
        await coordinator._async_update_data()


async def test_coordinator_consecutive_failures_tracking(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_vsn_client: MagicMock,
) -> None:
    """Test consecutive failures are tracked."""
    mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError(
        "Connection failed"
    )

    # Simulate multiple failures
    for i in range(DEFAULT_FAILURES_THRESHOLD):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._consecutive_failures == i + 1

    # After threshold, repair issue should be created
    assert coordinator._consecutive_failures == DEFAULT_FAILURES_THRESHOLD


async def test_coordinator_recovery_resets_failures(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_vsn_client: MagicMock,
    mock_normalized_data: dict,
) -> None:
    """Test successful update resets failure counter."""
    # Simulate some failures
    mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError(
        "Connection failed"
    )

    for _ in range(2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    assert coordinator._consecutive_failures == 2

    # Now simulate recovery
    mock_vsn_client.get_normalized_data.side_effect = None
    mock_vsn_client.get_normalized_data.return_value = mock_normalized_data

    data = await coordinator._async_update_data()

    assert data == mock_normalized_data
    assert coordinator._consecutive_failures == 0


async def test_coordinator_shutdown(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_vsn_client: MagicMock,
) -> None:
    """Test coordinator shutdown closes client."""
    await coordinator.async_shutdown()

    mock_vsn_client.close.assert_called_once()


async def test_coordinator_device_event_firing(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test device events are fired correctly."""
    # Set device_id
    coordinator.device_id = "test_device_id"

    # Call the event firing method
    coordinator._fire_device_event("device_recovered")

    # Verify event was fired
    mock_hass.bus.async_fire.assert_called_once()
    call_args = mock_hass.bus.async_fire.call_args
    assert call_args[0][0] == f"{DOMAIN}_event"
    assert call_args[0][1]["type"] == "device_recovered"
    assert call_args[0][1]["device_id"] == "test_device_id"


async def test_coordinator_no_event_without_device_id(
    coordinator: ABBFimerPVIVSNRestCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test no event is fired when device_id is not set."""
    # Ensure device_id is None
    coordinator.device_id = None

    # Call the event firing method
    coordinator._fire_device_event("device_recovered")

    # Verify no event was fired
    mock_hass.bus.async_fire.assert_not_called()


async def test_coordinator_format_downtime(
    coordinator: ABBFimerPVIVSNRestCoordinator,
) -> None:
    """Test downtime formatting."""
    # Test various durations
    assert coordinator._format_downtime(30) == "30 seconds"
    assert coordinator._format_downtime(60) == "1 minute"
    assert coordinator._format_downtime(90) == "1 minute 30 seconds"
    assert coordinator._format_downtime(3600) == "1 hour"
    assert coordinator._format_downtime(3661) == "1 hour 1 minute"
    assert coordinator._format_downtime(7200) == "2 hours"
    assert coordinator._format_downtime(7261) == "2 hours 1 minute"
