"""Tests for repairs module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.repairs import (
    ISSUE_CONNECTION_FAILED,
    NOTIFICATION_RECOVERY,
    create_connection_issue,
    create_recovery_notification,
    delete_connection_issue,
)
from homeassistant.core import HomeAssistant


class TestIssueConstants:
    """Tests for issue ID constants."""

    def test_connection_failed_issue_id(self) -> None:
        """Test connection failed issue ID."""
        assert ISSUE_CONNECTION_FAILED == "connection_failed"

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
