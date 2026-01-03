"""Tests for ABB FIMER PVI VSN REST exceptions."""

from __future__ import annotations

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
    VSNDetectionError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_vsn_client_error_is_exception(self) -> None:
        """Test VSNClientError inherits from Exception."""
        assert issubclass(VSNClientError, Exception)

    def test_vsn_connection_error_is_client_error(self) -> None:
        """Test VSNConnectionError inherits from VSNClientError."""
        assert issubclass(VSNConnectionError, VSNClientError)

    def test_vsn_authentication_error_is_client_error(self) -> None:
        """Test VSNAuthenticationError inherits from VSNClientError."""
        assert issubclass(VSNAuthenticationError, VSNClientError)

    def test_vsn_detection_error_is_client_error(self) -> None:
        """Test VSNDetectionError inherits from VSNClientError."""
        assert issubclass(VSNDetectionError, VSNClientError)


class TestExceptionInstantiation:
    """Tests for exception instantiation."""

    def test_vsn_client_error_message(self) -> None:
        """Test VSNClientError can be raised with message."""
        with pytest.raises(VSNClientError, match="Test error"):
            raise VSNClientError("Test error")

    def test_vsn_connection_error_message(self) -> None:
        """Test VSNConnectionError can be raised with message."""
        with pytest.raises(VSNConnectionError, match="Connection failed"):
            raise VSNConnectionError("Connection failed")

    def test_vsn_authentication_error_message(self) -> None:
        """Test VSNAuthenticationError can be raised with message."""
        with pytest.raises(VSNAuthenticationError, match="Invalid credentials"):
            raise VSNAuthenticationError("Invalid credentials")

    def test_vsn_detection_error_message(self) -> None:
        """Test VSNDetectionError can be raised with message."""
        with pytest.raises(VSNDetectionError, match="Could not detect"):
            raise VSNDetectionError("Could not detect model")


class TestExceptionCatching:
    """Tests for catching exceptions at different levels."""

    def test_catch_connection_as_client(self) -> None:
        """Test VSNConnectionError can be caught as VSNClientError."""
        with pytest.raises(VSNClientError, match="Connection failed"):
            raise VSNConnectionError("Connection failed")

    def test_catch_auth_as_client(self) -> None:
        """Test VSNAuthenticationError can be caught as VSNClientError."""
        with pytest.raises(VSNClientError, match="Invalid auth"):
            raise VSNAuthenticationError("Invalid auth")

    def test_catch_detection_as_client(self) -> None:
        """Test VSNDetectionError can be caught as VSNClientError."""
        with pytest.raises(VSNClientError, match="Detection failed"):
            raise VSNDetectionError("Detection failed")

    def test_catch_specific_over_general(self) -> None:
        """Test specific exceptions are caught before general."""
        # Verify VSNConnectionError is caught as specific type first
        with pytest.raises(VSNConnectionError, match="Connection failed"):
            raise VSNConnectionError("Connection failed")
