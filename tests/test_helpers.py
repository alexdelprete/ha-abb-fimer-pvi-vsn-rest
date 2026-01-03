"""Tests for helper functions."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from custom_components.abb_fimer_pvi_vsn_rest.helpers import (
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
