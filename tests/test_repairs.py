"""Tests for repairs module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.repairs import (
    ISSUE_CONNECTION_FAILED,
    ISSUE_RECOVERY_SUCCESS,
    async_create_fix_flow,
    create_connection_issue,
    create_recovery_notification,
    delete_connection_issue,
)
from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.core import HomeAssistant


class TestIssueConstants:
    """Tests for issue ID constants."""

    def test_connection_failed_issue_id(self) -> None:
        """Test connection failed issue ID."""
        assert ISSUE_CONNECTION_FAILED == "connection_failed"

    def test_recovery_success_issue_id(self) -> None:
        """Test recovery success issue ID."""
        assert ISSUE_RECOVERY_SUCCESS == "recovery_success"


class TestAsyncCreateFixFlow:
    """Tests for async_create_fix_flow function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.mark.asyncio
    async def test_create_fix_flow_returns_confirm_flow(self, mock_hass: MagicMock) -> None:
        """Test async_create_fix_flow returns ConfirmRepairFlow."""
        result = await async_create_fix_flow(mock_hass, "test_issue", None)
        assert isinstance(result, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_create_fix_flow_with_data(self, mock_hass: MagicMock) -> None:
        """Test async_create_fix_flow with data parameter."""
        data = {"device_name": "Test Device", "downtime": "5m 23s"}
        result = await async_create_fix_flow(mock_hass, "recovery_success_123", data)
        assert isinstance(result, ConfirmRepairFlow)


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
        return MagicMock(spec=HomeAssistant)

    def test_create_recovery_notification(self, mock_hass: MagicMock) -> None:
        """Test creating a recovery notification."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_recovery_notification(
                mock_hass,
                entry_id="entry_123",
                device_name="Test Inverter",
                started_at="2024-01-01 10:00:00",
                ended_at="2024-01-01 10:05:23",
                downtime="5m 23s",
            )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]

        assert call_kwargs["is_fixable"] is True
        assert call_kwargs["is_persistent"] is True
        assert call_kwargs["translation_key"] == ISSUE_RECOVERY_SUCCESS
        placeholders = call_kwargs["translation_placeholders"]
        assert placeholders["device_name"] == "Test Inverter"
        assert placeholders["started_at"] == "2024-01-01 10:00:00"
        assert placeholders["ended_at"] == "2024-01-01 10:05:23"
        assert placeholders["downtime"] == "5m 23s"

    def test_create_recovery_notification_id_format(self, mock_hass: MagicMock) -> None:
        """Test recovery notification ID format."""
        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.repairs.ir.async_create_issue"
        ) as mock_create:
            create_recovery_notification(
                mock_hass,
                entry_id="xyz789",
                device_name="Device",
                started_at="start",
                ended_at="end",
                downtime="1m",
            )

        call_args = mock_create.call_args[0]
        assert call_args[1] == DOMAIN
        assert call_args[2] == f"{ISSUE_RECOVERY_SUCCESS}_xyz789"
