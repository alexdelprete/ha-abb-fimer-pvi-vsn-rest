"""Tests for helper functions."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.helpers import (
    build_prefix_by_device,
    load_entity_name_translations,
    log_debug,
    log_error,
    log_info,
    log_warning,
)


class TestLogDebug:
    """Tests for log_debug function."""

    def test_log_debug_basic(self) -> None:
        """Test basic debug logging."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_debug(mock_logger, "TestContext", "Test message")
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]
        assert "TestContext" in call_args[1]
        assert "Test message" in call_args[2]

    def test_log_debug_with_kwargs(self) -> None:
        """Test debug logging with keyword arguments."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_debug(mock_logger, "Context", "Message", key1="value1", key2="value2")
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]
        assert "key1=value1" in call_args[3]
        assert "key2=value2" in call_args[3]


class TestLogInfo:
    """Tests for log_info function."""

    def test_log_info_basic(self) -> None:
        """Test basic info logging."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_info(mock_logger, "TestContext", "Test message")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]
        assert "TestContext" in call_args[1]
        assert "Test message" in call_args[2]

    def test_log_info_with_kwargs(self) -> None:
        """Test info logging with keyword arguments."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_info(mock_logger, "Context", "Message", device_id="123")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]
        assert "device_id=123" in call_args[3]


class TestLogWarning:
    """Tests for log_warning function."""

    def test_log_warning_basic(self) -> None:
        """Test basic warning logging."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_warning(mock_logger, "TestContext", "Warning message")
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0]
        assert "TestContext" in call_args[1]
        assert "Warning message" in call_args[2]

    def test_log_warning_with_kwargs(self) -> None:
        """Test warning logging with keyword arguments."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_warning(mock_logger, "Context", "Message", error_code=500)
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0]
        assert "error_code=500" in call_args[3]


class TestLogError:
    """Tests for log_error function."""

    def test_log_error_basic(self) -> None:
        """Test basic error logging."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_error(mock_logger, "TestContext", "Error message")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "TestContext" in call_args[1]
        assert "Error message" in call_args[2]

    def test_log_error_with_kwargs(self) -> None:
        """Test error logging with keyword arguments."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_error(mock_logger, "Context", "Message", exception="ValueError")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "exception=ValueError" in call_args[3]

    def test_log_error_empty_kwargs(self) -> None:
        """Test error logging with no extra kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        log_error(mock_logger, "Context", "Message")
        mock_logger.error.assert_called_once()
        # Extra should be empty string
        call_args = mock_logger.error.call_args[0]
        assert call_args[3] == ""


class TestBuildPrefixByDevice:
    """Tests for build_prefix_by_device function."""

    def _make_device(
        self, device_id: str, device_type: str, is_datalogger: bool = False
    ) -> MagicMock:
        """Create a mock DiscoveredDevice."""
        device = MagicMock()
        device.device_id = device_id
        device.device_type = device_type
        device.is_datalogger = is_datalogger
        return device

    def test_single_device_with_prefix(self) -> None:
        """Test single device per type gets prefix from base key."""
        devices = [self._make_device("077909-3G82-3112", "inverter_3phases")]
        options = {"prefix_inverter": "My Inverter"}

        result = build_prefix_by_device(devices, options)

        assert result == {"0779093g823112": "My Inverter"}

    def test_single_device_empty_prefix(self) -> None:
        """Test single device with empty prefix returns empty dict."""
        devices = [self._make_device("077909-3G82-3112", "inverter_3phases")]
        options = {"prefix_inverter": ""}

        result = build_prefix_by_device(devices, options)

        assert result == {}

    def test_multi_device_with_indexed_prefixes(self) -> None:
        """Test multiple devices of same type use indexed prefix keys."""
        devices = [
            self._make_device("AAA-111", "battery"),
            self._make_device("BBB-222", "battery"),
        ]
        options = {
            "prefix_battery_1": "Battery East",
            "prefix_battery_2": "Battery West",
        }

        result = build_prefix_by_device(devices, options)

        # Devices sorted by device_id: AAA-111 first, BBB-222 second
        assert result == {"aaa111": "Battery East", "bbb222": "Battery West"}

    def test_multi_device_partial_prefixes(self) -> None:
        """Test multi-device where only some have prefixes set."""
        devices = [
            self._make_device("AAA-111", "battery"),
            self._make_device("BBB-222", "battery"),
        ]
        options = {
            "prefix_battery_1": "Battery East",
            "prefix_battery_2": "",  # Empty — not included
        }

        result = build_prefix_by_device(devices, options)

        assert result == {"aaa111": "Battery East"}

    def test_unknown_device_type_skipped(self) -> None:
        """Test device type not in TYPE_TO_CONF_PREFIX is skipped."""
        devices = [self._make_device("XXX-999", "unknown_type")]
        options = {}

        result = build_prefix_by_device(devices, options)

        assert result == {}

    def test_datalogger_device_prefix(self) -> None:
        """Test datalogger device gets prefix from datalogger key."""
        devices = [self._make_device("111033-3N16-1421", "datalogger", is_datalogger=True)]
        options = {"prefix_datalogger": "My Logger"}

        result = build_prefix_by_device(devices, options)

        assert result == {"1110333n161421": "My Logger"}


class TestLoadEntityNameTranslations:
    """Tests for load_entity_name_translations function."""

    @pytest.mark.asyncio
    async def test_loads_and_parses_translations(self) -> None:
        """Test translations are loaded and parsed into point_name → name dict."""
        mock_hass = MagicMock()
        mock_translations = {
            "component.abb_fimer_pvi_vsn_rest.entity.sensor.watts.name": "Power AC",
            "component.abb_fimer_pvi_vsn_rest.entity.sensor.alarm_st.name": "Alarm Status",
            "component.abb_fimer_pvi_vsn_rest.entity.sensor.serial_number.name": "Serial number",
            "component.other_domain.entity.sensor.test.name": "Other Domain",
        }

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.helpers.async_get_translations",
            new_callable=AsyncMock,
            return_value=mock_translations,
        ):
            result = await load_entity_name_translations(mock_hass, "abb_fimer_pvi_vsn_rest")

        assert result == {
            "watts": "Power AC",
            "alarm_st": "Alarm Status",
            "serial_number": "Serial number",
        }

    @pytest.mark.asyncio
    async def test_empty_translations(self) -> None:
        """Test empty translations return empty dict."""
        mock_hass = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.helpers.async_get_translations",
            new_callable=AsyncMock,
            return_value={},
        ):
            result = await load_entity_name_translations(mock_hass, "abb_fimer_pvi_vsn_rest")

        assert result == {}
