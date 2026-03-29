"""Tests for ABB FIMER PVI VSN REST coordinator."""

from __future__ import annotations

from datetime import timedelta
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_KNOWN_DEVICES,
    CONF_RECOVERY_SCRIPT,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DOMAIN,
)
from custom_components.abb_fimer_pvi_vsn_rest.coordinator import ABBFimerPVIVSNRestCoordinator
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import (
    TEST_HOST,
    TEST_INVERTER_SN,
    TEST_LOGGER_SN,
    TEST_SCAN_INTERVAL,
    TEST_VSN_MODEL,
    MockDiscoveredDevice,
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


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry with options."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.options = {
        CONF_ENABLE_REPAIR_NOTIFICATION: True,
        CONF_FAILURES_THRESHOLD: DEFAULT_FAILURES_THRESHOLD,
        CONF_RECOVERY_SCRIPT: "",
    }
    return entry


@pytest.fixture
def coordinator_with_entry_id(
    mock_hass: MagicMock,
    mock_vsn_client: MagicMock,
    mock_discovery_result: MockDiscoveryResult,
    mock_config_entry: MagicMock,
) -> ABBFimerPVIVSNRestCoordinator:
    """Create a coordinator with entry_id for repair issue testing."""
    return ABBFimerPVIVSNRestCoordinator(
        hass=mock_hass,
        client=mock_vsn_client,
        update_interval=timedelta(seconds=TEST_SCAN_INTERVAL),
        discovery_result=mock_discovery_result,
        entry_id="test_entry_id",
        host=TEST_HOST,
        config_entry=mock_config_entry,
    )


class TestCoordinatorInit:
    """Tests for coordinator initialization."""

    async def test_init_with_discovery_result(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test coordinator initialization with discovery result."""
        assert coordinator.vsn_model == TEST_VSN_MODEL
        assert coordinator.discovery_result == mock_discovery_result
        assert len(coordinator.discovered_devices) == 2
        assert coordinator._consecutive_failures == 0
        assert coordinator._repair_issue_created is False
        assert coordinator._failure_start_time is None

    async def test_init_without_discovery_result(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test coordinator initialization without discovery result."""
        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=None,
        )

        assert coordinator.vsn_model is None
        assert coordinator.discovery_result is None
        assert coordinator.discovered_devices == []

    async def test_init_with_entry_id_and_host(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test coordinator initialization with entry_id and host."""
        assert coordinator_with_entry_id._entry_id == "test_entry_id"
        assert coordinator_with_entry_id._host == TEST_HOST


class TestCoordinatorUpdate:
    """Tests for coordinator data updates."""

    async def test_update_success(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test successful data update."""
        data = await coordinator._async_update_data()

        mock_vsn_client.get_normalized_data.assert_called_once()
        assert data == mock_normalized_data
        assert "devices" in data
        assert TEST_INVERTER_SN in data["devices"]
        assert TEST_LOGGER_SN in data["devices"]

    async def test_update_connects_if_no_model(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test update connects client if vsn_model is not set."""
        mock_vsn_client.connect = AsyncMock(return_value="VSN300")

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=None,
        )

        await coordinator._async_update_data()

        mock_vsn_client.connect.assert_called_once()
        assert coordinator.vsn_model == "VSN300"

    async def test_update_failure_connection_error(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test update failure with connection error."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Connection failed")

        with pytest.raises(UpdateFailed, match="Connection error"):
            await coordinator._async_update_data()

    async def test_update_failure_auth_error(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test update failure with authentication error."""
        mock_vsn_client.get_normalized_data.side_effect = VSNAuthenticationError("Auth failed")

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()

    async def test_update_failure_client_error(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test update failure with client error."""
        mock_vsn_client.get_normalized_data.side_effect = VSNClientError("Client error")

        with pytest.raises(UpdateFailed, match="Client error"):
            await coordinator._async_update_data()

    async def test_update_failure_unexpected_error(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test update failure with unexpected error."""
        mock_vsn_client.get_normalized_data.side_effect = ValueError("Unexpected")

        with pytest.raises(UpdateFailed, match="Unexpected error"):
            await coordinator._async_update_data()


class TestFailureTracking:
    """Tests for failure tracking and repair issues."""

    async def test_consecutive_failures_increment(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test consecutive failures are tracked."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        for i in range(3):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
            assert coordinator._consecutive_failures == i + 1

    async def test_failures_reset_on_success(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test failure counter resets on successful update."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        for _ in range(2):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

        assert coordinator._consecutive_failures == 2

        # Recovery
        mock_vsn_client.get_normalized_data.side_effect = None
        mock_vsn_client.get_normalized_data.return_value = mock_normalized_data

        await coordinator._async_update_data()

        assert coordinator._consecutive_failures == 0

    async def test_repair_issue_created_at_threshold(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test repair issue is created when threshold is reached."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"
        ) as mock_create:
            for _ in range(DEFAULT_FAILURES_THRESHOLD):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

            mock_create.assert_called_once()
            assert coordinator_with_entry_id._repair_issue_created is True

    async def test_repair_issue_not_created_twice(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test repair issue is not created again after already created."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"
        ) as mock_create:
            # Hit threshold
            for _ in range(DEFAULT_FAILURES_THRESHOLD):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

            # Continue failing
            for _ in range(5):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

            # Should only be called once
            mock_create.assert_called_once()


class TestRecovery:
    """Tests for recovery handling."""

    async def test_recovery_clears_repair_issue(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test recovery clears repair issue and creates notification."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"):
            for _ in range(DEFAULT_FAILURES_THRESHOLD):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

        assert coordinator_with_entry_id._repair_issue_created is True

        # Recovery
        mock_vsn_client.get_normalized_data.side_effect = None
        mock_vsn_client.get_normalized_data.return_value = mock_normalized_data

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.delete_connection_issue"
            ) as mock_delete,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_recovery_notification"
            ) as mock_notify,
        ):
            await coordinator_with_entry_id._async_update_data()

            mock_delete.assert_called_once()
            mock_notify.assert_called_once()
            assert coordinator_with_entry_id._repair_issue_created is False

    async def test_recovery_fires_device_event(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
        mock_normalized_data: dict,
        mock_hass: MagicMock,
    ) -> None:
        """Test recovery fires device_recovered event."""
        coordinator_with_entry_id.device_id = "test_device"
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"):
            for _ in range(DEFAULT_FAILURES_THRESHOLD):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

        mock_hass.bus.async_fire.reset_mock()

        # Recovery
        mock_vsn_client.get_normalized_data.side_effect = None
        mock_vsn_client.get_normalized_data.return_value = mock_normalized_data

        with (
            patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.delete_connection_issue"),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_recovery_notification"
            ),
        ):
            await coordinator_with_entry_id._async_update_data()

        # Check device_recovered event was fired
        calls = mock_hass.bus.async_fire.call_args_list
        event_types = [call[0][1].get("type") for call in calls]
        assert "device_recovered" in event_types


class TestDeviceEvents:
    """Tests for device event firing."""

    async def test_fire_event_with_device_id(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_hass: MagicMock,
    ) -> None:
        """Test event is fired when device_id is set."""
        coordinator.device_id = "test_device_id"

        coordinator._fire_device_event("device_recovered")

        mock_hass.bus.async_fire.assert_called_once()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == f"{DOMAIN}_event"
        assert call_args[0][1]["type"] == "device_recovered"
        assert call_args[0][1]["device_id"] == "test_device_id"

    async def test_no_event_without_device_id(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_hass: MagicMock,
    ) -> None:
        """Test no event is fired when device_id is not set."""
        coordinator.device_id = None

        coordinator._fire_device_event("device_recovered")

        mock_hass.bus.async_fire.assert_not_called()

    async def test_fire_event_with_extra_data(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_hass: MagicMock,
    ) -> None:
        """Test event includes extra data."""
        coordinator.device_id = "test_device_id"

        coordinator._fire_device_event("device_unreachable", {"error": "Connection failed"})

        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][1]["error"] == "Connection failed"

    async def test_fire_event_includes_discovery_info(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_hass: MagicMock,
    ) -> None:
        """Test event includes discovery result info."""
        coordinator.device_id = "test_device_id"

        coordinator._fire_device_event("test_event")

        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][1]["vsn_model"] == TEST_VSN_MODEL
        assert call_args[0][1]["logger_sn"] == TEST_LOGGER_SN


class TestFormatDowntime:
    """Tests for downtime formatting."""

    async def test_format_seconds(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test formatting seconds only."""
        assert coordinator._format_downtime(30) == "30s"
        assert coordinator._format_downtime(1) == "1s"
        assert coordinator._format_downtime(59) == "59s"

    async def test_format_minutes(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test formatting minutes."""
        assert coordinator._format_downtime(60) == "1m"
        assert coordinator._format_downtime(120) == "2m"

    async def test_format_minutes_and_seconds(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test formatting minutes and seconds."""
        assert coordinator._format_downtime(90) == "1m 30s"
        assert coordinator._format_downtime(125) == "2m 5s"

    async def test_format_hours(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test formatting hours."""
        assert coordinator._format_downtime(3600) == "1h"
        assert coordinator._format_downtime(7200) == "2h"

    async def test_format_hours_and_minutes(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test formatting hours and minutes."""
        assert coordinator._format_downtime(3660) == "1h 1m"
        assert coordinator._format_downtime(3661) == "1h 1m"
        assert coordinator._format_downtime(7261) == "2h 1m"


class TestGetDeviceName:
    """Tests for _get_device_name method."""

    async def test_device_name_with_discovery(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test device name from discovery result."""
        name = coordinator._get_device_name()
        assert TEST_VSN_MODEL in name
        assert TEST_LOGGER_SN in name

    async def test_device_name_with_host(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test device name includes host."""
        coordinator_with_entry_id.discovery_result = None
        name = coordinator_with_entry_id._get_device_name()
        assert name == TEST_HOST

    async def test_device_name_fallback(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test device name fallback."""
        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=None,
        )
        name = coordinator._get_device_name()
        assert name == "VSN Device"


class TestShutdown:
    """Tests for coordinator shutdown."""

    async def test_shutdown_closes_client(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
    ) -> None:
        """Test shutdown closes the client."""
        await coordinator.async_shutdown()

        mock_vsn_client.close.assert_called_once()


class TestConfigurableOptions:
    """Tests for configurable notification options."""

    async def test_default_options_without_config_entry(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test default options are used when no config_entry is provided."""
        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=None,
        )

        assert coordinator._enable_repair_notification == DEFAULT_ENABLE_REPAIR_NOTIFICATION
        assert coordinator._failures_threshold == DEFAULT_FAILURES_THRESHOLD
        assert coordinator._recovery_script == DEFAULT_RECOVERY_SCRIPT

    async def test_options_from_config_entry(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test options are read from config_entry."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: False,
            CONF_FAILURES_THRESHOLD: 5,
            CONF_RECOVERY_SCRIPT: "script.restart_router",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        assert coordinator._enable_repair_notification is False
        assert coordinator._failures_threshold == 5
        assert coordinator._recovery_script == "script.restart_router"

    async def test_custom_failures_threshold(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test custom failures threshold is used."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 5,
            CONF_RECOVERY_SCRIPT: "",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"
        ) as mock_create:
            # Fail 4 times (below threshold of 5)
            for _ in range(4):
                with pytest.raises(UpdateFailed):
                    await coordinator._async_update_data()

            mock_create.assert_not_called()

            # 5th failure reaches threshold
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

            mock_create.assert_called_once()

    async def test_notifications_disabled(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test repair issue not created when notifications are disabled."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: False,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"
        ) as mock_create:
            for _ in range(5):
                with pytest.raises(UpdateFailed):
                    await coordinator._async_update_data()

            # Repair issue should NOT be created when notifications disabled
            mock_create.assert_not_called()
            # But internal tracking should still work
            assert coordinator._repair_issue_created is True


class TestRecoveryScript:
    """Tests for recovery script execution."""

    async def test_recovery_script_executed(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test recovery script is executed when configured."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "script.restart_router",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")
        mock_hass.async_create_task = MagicMock()

        with patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"):
            for _ in range(3):
                with pytest.raises(UpdateFailed):
                    await coordinator._async_update_data()

        # async_create_task should be called to execute recovery script
        mock_hass.async_create_task.assert_called()

    async def test_no_recovery_script_when_not_configured(
        self,
        coordinator_with_entry_id: ABBFimerPVIVSNRestCoordinator,
        mock_vsn_client: MagicMock,
        mock_hass: MagicMock,
    ) -> None:
        """Test no recovery script execution when not configured."""
        mock_vsn_client.get_normalized_data.side_effect = VSNConnectionError("Failed")
        mock_hass.async_create_task = MagicMock()

        with patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_connection_issue"):
            for _ in range(DEFAULT_FAILURES_THRESHOLD):
                with pytest.raises(UpdateFailed):
                    await coordinator_with_entry_id._async_update_data()

        # async_create_task should NOT be called for recovery script
        # (but may be called for other purposes, so we check the call args)
        if mock_hass.async_create_task.called:
            # Verify none of the calls are for _execute_recovery_script
            for call in mock_hass.async_create_task.call_args_list:
                # The coroutine name should not be _execute_recovery_script
                coro = call[0][0]
                assert "_execute_recovery_script" not in str(coro)

    async def test_execute_recovery_script_method(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _execute_recovery_script method directly."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "script.my_script",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_hass.services.async_call = AsyncMock()

        await coordinator._execute_recovery_script()

        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert call_args[1]["domain"] == "script"
        assert call_args[1]["service"] == "my_script"
        assert coordinator._recovery_script_executed is True
        assert coordinator._script_executed_time is not None

    async def test_execute_recovery_script_empty(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _execute_recovery_script does nothing when script is empty."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_hass.services.async_call = AsyncMock()

        await coordinator._execute_recovery_script()

        mock_hass.services.async_call.assert_not_called()
        assert coordinator._recovery_script_executed is False

    @pytest.mark.asyncio
    async def test_execute_recovery_script_failure(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _execute_recovery_script handles HomeAssistantError gracefully."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "script.my_script",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        mock_hass.services.async_call = AsyncMock(
            side_effect=HomeAssistantError("Script not found")
        )

        await coordinator._execute_recovery_script()

        mock_hass.services.async_call.assert_called_once()
        # Script should NOT be marked as executed on failure
        assert coordinator._recovery_script_executed is False

    @pytest.mark.asyncio
    async def test_handle_recovery_with_script_executed(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _handle_recovery formats script_executed_at when script was run."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "script.my_script",
        }

        coordinator = ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=60),
            discovery_result=mock_discovery_result,
            entry_id="test_entry",
            host=TEST_HOST,
            config_entry=config_entry,
        )

        # Simulate script was executed during failure
        coordinator._recovery_script_executed = True
        coordinator._script_executed_time = time.time()
        coordinator._failure_start_time = time.time() - 120
        coordinator._repair_issue_created = True
        coordinator._consecutive_failures = 3

        with (
            patch("custom_components.abb_fimer_pvi_vsn_rest.coordinator.delete_connection_issue"),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_recovery_notification"
            ) as mock_notify,
        ):
            await coordinator._handle_recovery()

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        # script_name should be set when script was executed
        assert call_kwargs["script_name"] == "script.my_script"
        # script_executed_at should be a formatted time string
        assert call_kwargs["script_executed_at"] is not None


class TestAttemptRediscovery:
    """Tests for _attempt_rediscovery and related helper methods."""

    @pytest.fixture
    def coordinator_with_missing(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> ABBFimerPVIVSNRestCoordinator:
        """Create coordinator with missing devices."""
        # Add client attributes needed by _attempt_rediscovery
        mock_vsn_client.session = MagicMock()
        mock_vsn_client.base_url = f"http://{TEST_HOST}"
        mock_vsn_client.username = "guest"
        mock_vsn_client.password = ""
        mock_vsn_client.timeout = 10
        mock_vsn_client.update_discovered_devices = MagicMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: DEFAULT_FAILURES_THRESHOLD,
            CONF_RECOVERY_SCRIPT: "",
        }
        entry.data = {
            CONF_KNOWN_DEVICES: [
                {"device_id": TEST_LOGGER_SN, "device_type": "datalogger", "is_datalogger": True},
                {
                    "device_id": TEST_INVERTER_SN,
                    "device_type": "inverter_3phases",
                    "is_datalogger": False,
                },
            ],
        }
        return ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=TEST_SCAN_INTERVAL),
            discovery_result=mock_discovery_result,
            entry_id="test_entry_id",
            host=TEST_HOST,
            config_entry=entry,
            missing_devices={TEST_INVERTER_SN},
        )

    @pytest.mark.asyncio
    async def test_attempt_rediscovery_devices_still_missing(
        self, coordinator_with_missing: ABBFimerPVIVSNRestCoordinator
    ) -> None:
        """Test re-discovery when devices are still missing."""
        # Discovery returns only datalogger
        datalogger_only = MockDiscoveryResult(
            vsn_model=TEST_VSN_MODEL,
            logger_sn=TEST_LOGGER_SN,
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                MockDiscoveredDevice(
                    device_id=TEST_LOGGER_SN,
                    raw_device_id=TEST_LOGGER_SN,
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
            ],
            status_data={},
        )

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.discover_vsn_device",
            new_callable=AsyncMock,
            return_value=datalogger_only,
        ):
            await coordinator_with_missing._attempt_rediscovery()

        # Inverter still missing
        assert TEST_INVERTER_SN in coordinator_with_missing._missing_devices
        assert not coordinator_with_missing._reload_scheduled

    @pytest.mark.asyncio
    async def test_attempt_rediscovery_full_recovery(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test re-discovery when all devices recover."""
        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.coordinator.delete_partial_discovery_issue",
            ) as mock_delete,
        ):
            await coordinator_with_missing._attempt_rediscovery()

        assert len(coordinator_with_missing._missing_devices) == 0
        assert coordinator_with_missing._reload_scheduled is True
        mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_attempt_rediscovery_skips_when_no_missing(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test re-discovery is skipped when no devices are missing."""
        coordinator_with_missing._missing_devices = set()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.discover_vsn_device",
            new_callable=AsyncMock,
        ) as mock_discover:
            await coordinator_with_missing._attempt_rediscovery()

        mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_attempt_rediscovery_skips_when_reload_scheduled(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test re-discovery is skipped when reload already scheduled."""
        coordinator_with_missing._reload_scheduled = True

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.discover_vsn_device",
            new_callable=AsyncMock,
        ) as mock_discover:
            await coordinator_with_missing._attempt_rediscovery()

        mock_discover.assert_not_called()

    @pytest.mark.asyncio
    async def test_attempt_rediscovery_handles_connection_error(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test re-discovery gracefully handles connection errors."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.discover_vsn_device",
            new_callable=AsyncMock,
            side_effect=VSNConnectionError("Connection refused"),
        ):
            await coordinator_with_missing._attempt_rediscovery()

        # Should not crash, devices still missing
        assert TEST_INVERTER_SN in coordinator_with_missing._missing_devices
        assert not coordinator_with_missing._reload_scheduled

    def test_update_discovery_state_syncs_client(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _update_discovery_state syncs coordinator and client."""
        coordinator_with_missing._update_discovery_state(mock_discovery_result)

        assert coordinator_with_missing.discovery_result == mock_discovery_result
        assert coordinator_with_missing.discovered_devices == mock_discovery_result.devices
        # Client should have been updated
        coordinator_with_missing.client.update_discovered_devices.assert_called_once_with(
            mock_discovery_result.devices
        )

    def test_sync_known_devices_adds_new(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test _sync_known_devices adds new devices to config entry."""
        new_device = MockDiscoveredDevice(
            device_id="new-device-001",
            raw_device_id="new-device-001",
            device_type="meter",
            device_model="Meter-1",
            manufacturer="ABB",
            firmware_version="1.0",
            hardware_version=None,
            is_datalogger=False,
        )
        new_result = MockDiscoveryResult(
            vsn_model=TEST_VSN_MODEL,
            logger_sn=TEST_LOGGER_SN,
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname=None,
            devices=[*coordinator_with_missing.discovered_devices, new_device],
            status_data={},
        )

        coordinator_with_missing._sync_known_devices(new_result)

        # Config entry should have been updated
        call_args = coordinator_with_missing.hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        known = new_data[CONF_KNOWN_DEVICES]
        device_ids = {d["device_id"] for d in known}
        assert "new-device-001" in device_ids

    def test_sync_known_devices_updates_device_type(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
        mock_discovery_result: MockDiscoveryResult,
    ) -> None:
        """Test _sync_known_devices updates stale device_type."""
        # Set inverter type to "unknown" (as migration would)
        coordinator_with_missing._config_entry.data[CONF_KNOWN_DEVICES][1]["device_type"] = (
            "unknown"
        )

        coordinator_with_missing._sync_known_devices(mock_discovery_result)

        call_args = coordinator_with_missing.hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        inverter = next(
            d for d in new_data[CONF_KNOWN_DEVICES] if d["device_id"] == TEST_INVERTER_SN
        )
        assert inverter["device_type"] == "inverter_3phases"

    def test_handle_full_recovery(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test _handle_full_recovery clears issue and schedules reload."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.delete_partial_discovery_issue",
        ) as mock_delete:
            coordinator_with_missing._handle_full_recovery()

        mock_delete.assert_called_once_with(coordinator_with_missing.hass, "test_entry_id")
        assert coordinator_with_missing._reload_scheduled is True

    def test_handle_partial_recovery(
        self,
        coordinator_with_missing: ABBFimerPVIVSNRestCoordinator,
    ) -> None:
        """Test _handle_partial_recovery updates repair issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.coordinator.create_partial_discovery_issue",
        ) as mock_create:
            coordinator_with_missing._handle_partial_recovery()

        mock_create.assert_called_once()


class TestIdempotencyCheck:
    """Tests for unknown device detection in _async_update_data."""

    @pytest.fixture
    def coordinator_with_known(
        self,
        mock_hass: MagicMock,
        mock_vsn_client: MagicMock,
        mock_discovery_result: MockDiscoveryResult,
    ) -> ABBFimerPVIVSNRestCoordinator:
        """Create coordinator with known_devices configured."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.options = {
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: DEFAULT_FAILURES_THRESHOLD,
            CONF_RECOVERY_SCRIPT: "",
        }
        entry.data = {
            CONF_KNOWN_DEVICES: [
                {"device_id": TEST_LOGGER_SN, "device_type": "datalogger", "is_datalogger": True},
            ],
        }
        return ABBFimerPVIVSNRestCoordinator(
            hass=mock_hass,
            client=mock_vsn_client,
            update_interval=timedelta(seconds=TEST_SCAN_INTERVAL),
            discovery_result=mock_discovery_result,
            entry_id="test_entry_id",
            host=TEST_HOST,
            config_entry=entry,
        )

    @pytest.mark.asyncio
    async def test_unknown_device_triggers_reload(
        self,
        coordinator_with_known: ABBFimerPVIVSNRestCoordinator,
        mock_normalized_data: dict,
    ) -> None:
        """Test that unknown devices in data trigger a reload."""
        # Data contains inverter, but known_devices only has datalogger
        coordinator_with_known.client.get_normalized_data = AsyncMock(
            return_value=mock_normalized_data
        )

        await coordinator_with_known._async_update_data()

        assert coordinator_with_known._reload_scheduled is True
        coordinator_with_known.hass.async_create_task.assert_called()
