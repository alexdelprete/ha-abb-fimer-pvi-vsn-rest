"""Tests for diagnostics module."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery import (
    DiscoveredDevice,
    DiscoveryResult,
)
from custom_components.abb_fimer_pvi_vsn_rest.const import CONF_SCAN_INTERVAL, CONF_VSN_MODEL
from custom_components.abb_fimer_pvi_vsn_rest.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)


class TestToRedact:
    """Tests for TO_REDACT constant."""

    def test_contains_sensitive_fields(self) -> None:
        """Test TO_REDACT contains expected sensitive fields."""
        assert "host" in TO_REDACT
        assert "password" in TO_REDACT
        assert "username" in TO_REDACT
        assert "sn" in TO_REDACT
        assert "serial_number" in TO_REDACT
        assert "ip" in TO_REDACT
        assert "mac" in TO_REDACT
        assert "hostname" in TO_REDACT


class TestAsyncGetConfigEntryDiagnostics:
    """Tests for async_get_config_entry_diagnostics function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock()

    @pytest.fixture
    def mock_discovery_result(self) -> DiscoveryResult:
        """Create mock discovery result."""
        return DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname="ABB-077909-3G82-3112.local",
            devices=[
                DiscoveredDevice(
                    device_id="077909-3G82-3112",
                    raw_device_id="077909-3G82-3112",
                    device_type="inverter_3phases",
                    device_model="PVI-10.0-OUTD",
                    manufacturer="Power-One",
                    firmware_version="C008",
                    hardware_version=None,
                    is_datalogger=False,
                ),
            ],
            status_data={},
        )

    @pytest.fixture
    def mock_config_entry(self, mock_discovery_result: DiscoveryResult) -> MagicMock:
        """Create mock config entry with runtime data."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.version = 1
        entry.data = {
            "host": "192.168.1.100",
            "username": "guest",
            "password": "secret",
            CONF_VSN_MODEL: "VSN300",
        }
        entry.options = {
            CONF_SCAN_INTERVAL: 60,
        }

        # Mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.discovery_result = mock_discovery_result
        mock_coordinator.last_update_success = True
        mock_coordinator.update_interval = timedelta(seconds=60)
        mock_coordinator.data = {
            "077909-3G82-3112": {
                "watts": {"value": 5000},
                "wh": {"value": 123456},
            }
        }

        # Mock runtime data
        mock_runtime_data = MagicMock()
        mock_runtime_data.coordinator = mock_coordinator
        entry.runtime_data = mock_runtime_data

        return entry

    @pytest.mark.asyncio
    async def test_diagnostics_returns_config(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics returns config data."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert "config" in result
        assert result["config"]["entry_id"] == "test_entry_id"
        assert result["config"]["version"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_redacts_sensitive_data(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics redacts sensitive data in config."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        # Sensitive fields should be redacted
        config_data = result["config"]["data"]
        assert config_data.get("host") == "**REDACTED**"
        assert config_data.get("username") == "**REDACTED**"
        assert config_data.get("password") == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_returns_discovery_data(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics returns discovery data."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert "discovery" in result
        discovery = result["discovery"]
        assert discovery["vsn_model"] == "VSN300"
        assert discovery["logger_model"] == "WIFI LOGGER CARD"
        assert discovery["device_count"] == 1
        # Sensitive fields should be redacted
        assert discovery["logger_sn"] == "**REDACTED**"
        assert discovery["hostname"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_returns_device_info(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics returns device info without sensitive data."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        devices = result["discovery"]["devices"]
        assert len(devices) == 1
        device = devices[0]
        assert device["device_type"] == "inverter_3phases"
        assert device["device_model"] == "PVI-10.0-OUTD"
        assert device["manufacturer"] == "Power-One"
        assert device["device_id"] == "**REDACTED**"

    @pytest.mark.asyncio
    async def test_diagnostics_returns_coordinator_data(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics returns coordinator state."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert "coordinator" in result
        coordinator = result["coordinator"]
        assert coordinator["last_update_success"] is True
        assert coordinator["update_interval_seconds"] == 60.0
        assert coordinator["vsn_model"] == "VSN300"

    @pytest.mark.asyncio
    async def test_diagnostics_returns_sensor_summary(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics returns sensor summary."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert "sensor_summary" in result
        # Should have summary with point counts, not actual values
        assert len(result["sensor_summary"]) > 0

    @pytest.mark.asyncio
    async def test_diagnostics_no_discovery_result(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics when no discovery result."""
        mock_config_entry.runtime_data.coordinator.discovery_result = None

        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert result["discovery"] == {}

    @pytest.mark.asyncio
    async def test_diagnostics_no_coordinator_data(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics when coordinator has no data."""
        mock_config_entry.runtime_data.coordinator.data = None

        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert result["sensor_summary"] == {}

    @pytest.mark.asyncio
    async def test_diagnostics_no_update_interval(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test diagnostics when update_interval is None."""
        mock_config_entry.runtime_data.coordinator.update_interval = None

        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        assert result["coordinator"]["update_interval_seconds"] is None
