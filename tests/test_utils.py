"""Tests for ABB FIMER PVI VSN REST utils module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.utils import (
    check_socket_connection,
    read_json_lenient,
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
        call_kwargs = mock_create.call_args[1] or {}
        # Or passed as positional arg
        if not call_kwargs.get("timeout"):
            # Socket create_connection signature: (address, timeout=...)
            # Check if timeout is in the call
            assert mock_create.call_args[0][1] == 10 or "timeout" in str(mock_create.call_args)


class TestReadJsonLenient:
    """Tests for read_json_lenient — UTF-8 first, latin-1 fallback (issue #68)."""

    @pytest.mark.asyncio
    async def test_falls_back_to_latin1_on_non_utf8_byte(self) -> None:
        """A body with 0xB4 (Latin-1 acute accent) parses via the latin-1 fallback."""
        # 0xB4 is a lone high byte that is invalid UTF-8; valid in Latin-1 (´).
        raw = b'{"label": "caf\xb4"}'
        response = MagicMock()
        response.read = AsyncMock(return_value=raw)

        result = await read_json_lenient(response)

        assert result == {"label": "caf\xb4"}

    @pytest.mark.asyncio
    async def test_utf8_wins_for_multibyte_body(self) -> None:
        """A genuine multibyte UTF-8 body decodes as UTF-8, not mojibake latin-1."""
        # "café" with é as the two-byte UTF-8 sequence 0xC3 0xA9.
        raw = '{"label": "café"}'.encode()
        response = MagicMock()
        response.read = AsyncMock(return_value=raw)

        result = await read_json_lenient(response)

        assert result == {"label": "café"}

    @pytest.mark.asyncio
    async def test_ascii_body_parses(self) -> None:
        """A plain ASCII body (the common case) parses unchanged."""
        raw = b'{"m101_1_W": 1737.9, "units": "kW"}'
        response = MagicMock()
        response.read = AsyncMock(return_value=raw)

        result = await read_json_lenient(response)

        assert result == {"m101_1_W": 1737.9, "units": "kW"}

    @pytest.mark.asyncio
    async def test_real_vsn300_fw201_utf8_config_decodes_correctly(self) -> None:
        """Regression: real fw 2.0.1 /v1/config with an accented plant name.

        Captured from VSN300 firmware 2.0.1 (gseguin_vsn300_fw201_config_utf8.json),
        the accented character in a user-entered plant name comes back as genuine
        two-byte UTF-8 (é -> 0xC3 0xA9), with Content-Type application/json and no
        charset. read_json_lenient must decode it as UTF-8 ("Café Test") — a forced
        latin-1 decode would mojibake it to "CafÃ© Test". See issue #68.
        """
        sample = (
            Path(__file__).parent.parent
            / "docs"
            / "vsn-data"
            / "vsn300-data"
            / "gseguin_vsn300_fw201_config_utf8.json"
        )
        raw = sample.read_bytes()
        # Sanity-check the fixture still carries the genuine two-byte UTF-8 é.
        assert b"\xc3\xa9" in raw

        response = MagicMock()
        response.read = AsyncMock(return_value=raw)

        result = await read_json_lenient(response)

        assert result["keys"]["plant.name"]["value"] == "Café Test"
        # Guard the failure mode explicitly: forced latin-1 would have mojibaked it.
        assert result["keys"]["plant.name"]["value"] != "CafÃ© Test"
