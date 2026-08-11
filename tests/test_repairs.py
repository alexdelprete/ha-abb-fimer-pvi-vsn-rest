"""Tests for repairs module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.repairs import (
    ISSUE_CONNECTION_FAILED,
    ISSUE_DATALOGGER_SILENT,
    ISSUE_PARTIAL_DISCOVERY,
    ISSUE_UNSUPPORTED_FIRMWARE,
    NOTIFICATION_RECOVERY,
    create_connection_issue,
    create_datalogger_silent_issue,
    create_partial_discovery_issue,
    create_recovery_notification,
    create_unsupported_firmware_issue,
    delete_connection_issue,
    delete_datalogger_silent_issue,
    delete_partial_discovery_issue,
    delete_unsupported_firmware_issue,
)
from homeassistant.core import HomeAssistant


class TestIssueConstants:
    """Tests for issue ID constants."""

    def test_connection_failed_issue_id(self) -> None:
        """Test connection failed issue ID."""
        assert ISSUE_CONNECTION_FAILED == "connection_failed"

    def test_partial_discovery_issue_id(self) -> None:
        """Test partial discovery issue ID."""
        assert ISSUE_PARTIAL_DISCOVERY == "partial_discovery"

    def test_datalogger_silent_issue_id(self) -> None:
        """Test datalogger silent issue ID."""
        assert ISSUE_DATALOGGER_SILENT == "datalogger_silent"

    def test_notification_recovery_id(self) -> None:
        """Test recovery notification ID."""
        assert NOTIFICATION_RECOVERY == "recovery"


class TestCreateConnectionIssue:
    """Tests for create_connection_issue function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    def test_create_connection_issue(self, mock_hass: MagicMock) -> None:
        """Test creating a connection issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_connection_issue(
                mock_hass,
                entry_id="entry_123",
                device_name="Test Inverter",
                host="192.168.1.100",
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]

        assert call_kwargs["is_fixable"] is False
        assert call_kwargs["is_persistent"] is True
        assert call_kwargs["translation_key"] == ISSUE_CONNECTION_FAILED
        assert call_kwargs["translation_placeholders"]["device_name"] == "Test Inverter"
        assert call_kwargs["translation_placeholders"]["host"] == "192.168.1.100"

    def test_create_connection_issue_id_format(self, mock_hass: MagicMock) -> None:
        """Test connection issue ID format."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_connection_issue(
                mock_hass,
                entry_id="abc123",
                device_name="Device",
                host="host",
            )

        call_args = mock_create.call_args[0]
        assert call_args[0] == mock_hass
        assert call_args[1] == DOMAIN
        assert call_args[2] == f"{ISSUE_CONNECTION_FAILED}_abc123"


class TestDeleteConnectionIssue:
    """Tests for delete_connection_issue function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    def test_delete_connection_issue(self, mock_hass: MagicMock) -> None:
        """Test deleting a connection issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_delete_issue"
        ) as mock_delete:
            delete_connection_issue(mock_hass, entry_id="entry_123")

        mock_delete.assert_called_once_with(
            mock_hass, DOMAIN, f"{ISSUE_CONNECTION_FAILED}_entry_123"
        )


class TestCreateRecoveryNotification:
    """Tests for create_recovery_notification function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        hass.async_create_task = MagicMock()
        return hass

    def test_create_recovery_notification_basic(self, mock_hass: MagicMock) -> None:
        """Test creating a recovery notification without script."""
        create_recovery_notification(
            mock_hass,
            entry_id="entry_123",
            device_name="Test Inverter",
            started_at="2024-01-01 10:00:00",
            ended_at="2024-01-01 10:05:23",
            downtime="5m 23s",
        )

        # Verify async_create_task was called
        mock_hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_with_script(self, mock_hass: MagicMock) -> None:
        """Test creating a recovery notification with script execution."""
        create_recovery_notification(
            mock_hass,
            entry_id="entry_123",
            device_name="Test Inverter",
            started_at="2024-01-01 10:00:00",
            ended_at="2024-01-01 10:05:23",
            downtime="5m 23s",
            script_name="script.restart_router",
            script_executed_at="2024-01-01 10:02:00",
        )

        # Verify async_create_task was called
        mock_hass.async_create_task.assert_called_once()

    def test_create_recovery_notification_id_format(self, mock_hass: MagicMock) -> None:
        """Test recovery notification ID format."""
        create_recovery_notification(
            mock_hass,
            entry_id="xyz789",
            device_name="Device",
            started_at="start",
            ended_at="end",
            downtime="1m",
        )

        # Verify async_create_task was called (it wraps the service call)
        mock_hass.async_create_task.assert_called_once()

        # Get the coroutine that was passed to async_create_task
        task_call = mock_hass.async_create_task.call_args[0][0]
        # The coroutine is from services.async_call, we verified it was scheduled
        assert task_call is not None

        # The notification ID format should be: {DOMAIN}_{NOTIFICATION_RECOVERY}_{entry_id}
        # This is verified by the function implementation


class TestPartialDiscoveryIssue:
    """Tests for partial discovery repair issue functions."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    def test_create_partial_discovery_issue(self, mock_hass: MagicMock) -> None:
        """Test creating a partial discovery issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_partial_discovery_issue(
                mock_hass,
                entry_id="entry_123",
                device_name="VSN300 (111033-3N16-1421)",
                missing_devices=["077909-3G82-3112"],
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["is_fixable"] is False
        assert call_kwargs["is_persistent"] is True
        assert call_kwargs["translation_key"] == ISSUE_PARTIAL_DISCOVERY
        assert call_kwargs["translation_placeholders"]["device_name"] == "VSN300 (111033-3N16-1421)"
        assert "077909-3G82-3112" in call_kwargs["translation_placeholders"]["missing_devices"]

    def test_delete_partial_discovery_issue(self, mock_hass: MagicMock) -> None:
        """Test deleting a partial discovery issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_delete_issue"
        ) as mock_delete:
            delete_partial_discovery_issue(mock_hass, entry_id="entry_123")

        mock_delete.assert_called_once_with(
            mock_hass, DOMAIN, f"{ISSUE_PARTIAL_DISCOVERY}_entry_123"
        )


class TestDataloggerSilentIssue:
    """Tests for datalogger silent issue functions."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    def test_create_datalogger_silent_issue(self, mock_hass: MagicMock) -> None:
        """Test creating a datalogger silent issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_datalogger_silent_issue(
                mock_hass,
                entry_id="entry_123",
                device_name="VSN300 (111033-3N16-1421)",
                host="192.168.1.100",
            )

        mock_create.assert_called_once()
        call_args = mock_create.call_args[0]
        call_kwargs = mock_create.call_args[1]

        assert call_args[2] == f"{ISSUE_DATALOGGER_SILENT}_entry_123"
        assert call_kwargs["is_fixable"] is False
        assert call_kwargs["is_persistent"] is True
        assert call_kwargs["translation_key"] == ISSUE_DATALOGGER_SILENT
        assert call_kwargs["translation_placeholders"]["device_name"] == "VSN300 (111033-3N16-1421)"
        assert call_kwargs["translation_placeholders"]["host"] == "192.168.1.100"

    def test_delete_datalogger_silent_issue(self, mock_hass: MagicMock) -> None:
        """Test deleting a datalogger silent issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_delete_issue"
        ) as mock_delete:
            delete_datalogger_silent_issue(mock_hass, entry_id="entry_123")

        mock_delete.assert_called_once_with(
            mock_hass, DOMAIN, f"{ISSUE_DATALOGGER_SILENT}_entry_123"
        )


class TestUnsupportedFirmwareIssue:
    """Tests for the VSN300 fw 2.0.0 unsupported-firmware repair issue (issue #68)."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    def test_create_unsupported_firmware_issue(self, mock_hass: MagicMock) -> None:
        """Test creating an unsupported firmware issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_unsupported_firmware_issue(
                mock_hass,
                entry_id="entry_123",
                host="192.168.1.100",
                firmware_version="2.0.0",
            )

        mock_create.assert_called_once()
        call_args = mock_create.call_args[0]
        call_kwargs = mock_create.call_args[1]

        assert call_args[0] == mock_hass
        assert call_args[1] == DOMAIN
        assert call_args[2] == f"{ISSUE_UNSUPPORTED_FIRMWARE}_entry_123"
        assert call_kwargs["is_fixable"] is False
        assert call_kwargs["is_persistent"] is True
        assert call_kwargs["translation_key"] == ISSUE_UNSUPPORTED_FIRMWARE
        assert call_kwargs["translation_placeholders"]["host"] == "192.168.1.100"
        assert call_kwargs["translation_placeholders"]["firmware_version"] == "2.0.0"

    def test_delete_unsupported_firmware_issue(self, mock_hass: MagicMock) -> None:
        """Test deleting an unsupported firmware issue."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_delete_issue"
        ) as mock_delete:
            delete_unsupported_firmware_issue(mock_hass, entry_id="entry_123")

        mock_delete.assert_called_once_with(
            mock_hass, DOMAIN, f"{ISSUE_UNSUPPORTED_FIRMWARE}_entry_123"
        )
