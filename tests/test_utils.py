"""Tests for ABB FIMER PVI VSN REST utils module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.utils import (
    check_socket_connection,
)


class TestCheckSocketConnection:
    """Tests for check_socket_connection function."""

    @pytest.mark.asyncio
    async def test_successful_connection(self) -> None:
        """Test successful socket connection."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket):
            # Should not raise
            await check_socket_connection("http://192.168.1.100", timeout=5)

        mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_parses_http_url(self) -> None:
        """Test URL parsing for HTTP."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket) as mock_create:
            await check_socket_connection("http://192.168.1.100", timeout=5)

        # Should connect to port 80 for HTTP
        call_args = mock_create.call_args[0][0]
        assert call_args[0] == "192.168.1.100"
        assert call_args[1] == 80

    @pytest.mark.asyncio
    async def test_parses_https_url(self) -> None:
        """Test URL parsing for HTTPS."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket) as mock_create:
            await check_socket_connection("https://192.168.1.100", timeout=5)

        # Should connect to port 443 for HTTPS
        call_args = mock_create.call_args[0][0]
        assert call_args[0] == "192.168.1.100"
        assert call_args[1] == 443

    @pytest.mark.asyncio
    async def test_parses_custom_port(self) -> None:
        """Test URL parsing with custom port."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket) as mock_create:
            await check_socket_connection("http://192.168.1.100:8080", timeout=5)

        call_args = mock_create.call_args[0][0]
        assert call_args[0] == "192.168.1.100"
        assert call_args[1] == 8080

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test timeout raises VSNConnectionError."""
        with (
            patch(
                "socket.create_connection",
                side_effect=TimeoutError("Connection timed out"),
            ),
            pytest.raises(VSNConnectionError, match="Timeout"),
        ):
            await check_socket_connection("http://192.168.1.100", timeout=5)

    @pytest.mark.asyncio
    async def test_connection_refused_error(self) -> None:
        """Test connection refused raises VSNConnectionError."""
        with (
            patch(
                "socket.create_connection",
                side_effect=ConnectionRefusedError("Connection refused"),
            ),
            pytest.raises(VSNConnectionError, match="Cannot connect"),
        ):
            await check_socket_connection("http://192.168.1.100", timeout=5)

    @pytest.mark.asyncio
    async def test_os_error(self) -> None:
        """Test OS error raises VSNConnectionError."""
        with (
            patch(
                "socket.create_connection",
                side_effect=OSError("Network unreachable"),
            ),
            pytest.raises(VSNConnectionError, match="Cannot connect"),
        ):
            await check_socket_connection("http://192.168.1.100", timeout=5)

    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        """Test generic ConnectionError raises VSNConnectionError."""
        with (
            patch(
                "socket.create_connection",
                side_effect=ConnectionError("Connection failed"),
            ),
            pytest.raises(VSNConnectionError, match="Cannot connect"),
        ):
            await check_socket_connection("http://192.168.1.100", timeout=5)

    @pytest.mark.asyncio
    async def test_parses_hostname(self) -> None:
        """Test URL parsing with hostname."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket) as mock_create:
            await check_socket_connection("http://vsn300.local", timeout=5)

        call_args = mock_create.call_args[0][0]
        assert call_args[0] == "vsn300.local"
        assert call_args[1] == 80

    @pytest.mark.asyncio
    async def test_passes_timeout(self) -> None:
        """Test timeout is passed to socket.create_connection."""
        mock_socket = MagicMock()

        with patch("socket.create_connection", return_value=mock_socket) as mock_create:
            await check_socket_connection("http://192.168.1.100", timeout=10)

        # Check timeout was passed as kwarg
        call_kwargs = mock_create.call_args[1] if mock_create.call_args[1] else {}
        # Or passed as positional arg
        if not call_kwargs.get("timeout"):
            # Socket create_connection signature: (address, timeout=...)
            # Check if timeout is in the call
            assert mock_create.call_args[0][1] == 10 or "timeout" in str(mock_create.call_args)
