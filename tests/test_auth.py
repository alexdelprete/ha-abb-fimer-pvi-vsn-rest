"""Tests for ABB FIMER PVI VSN REST authentication module."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth import (
    _detect_model_from_status,
    build_digest_header,
    calculate_digest_response,
    detect_vsn_model,
    get_vsn300_digest_header,
    get_vsn700_basic_auth,
    parse_digest_challenge,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNConnectionError,
    VSNDetectionError,
)


class TestCalculateDigestResponse:
    """Tests for calculate_digest_response function."""

    def test_simple_digest_without_qop(self) -> None:
        """Test digest calculation without qop."""
        result = calculate_digest_response(
            username="guest",
            password="password",
            realm="vsn300",
            nonce="abc123",
            method="GET",
            uri="/v1/livedata",
        )

        # Result should be a 32-character hex string (MD5)
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_digest_with_qop(self) -> None:
        """Test digest calculation with qop."""
        result = calculate_digest_response(
            username="guest",
            password="password",
            realm="vsn300",
            nonce="abc123",
            method="GET",
            uri="/v1/livedata",
            qop="auth",
            nc="00000001",
            cnonce="xyz789",
        )

        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_produce_different_outputs(self) -> None:
        """Test that different inputs produce different digests."""
        result1 = calculate_digest_response("user1", "pass1", "realm", "nonce", "GET", "/path")
        result2 = calculate_digest_response("user2", "pass2", "realm", "nonce", "GET", "/path")

        assert result1 != result2


class TestParseDigestChallenge:
    """Tests for parse_digest_challenge function."""

    def test_parse_standard_digest_challenge(self) -> None:
        """Test parsing standard Digest challenge."""
        challenge = 'Digest realm="vsn300", nonce="abc123", qop="auth"'
        result = parse_digest_challenge(challenge)

        assert result["realm"] == "vsn300"
        assert result["nonce"] == "abc123"
        assert result["qop"] == "auth"

    def test_parse_x_digest_challenge(self) -> None:
        """Test parsing X-Digest challenge."""
        challenge = 'X-Digest realm="vsn300", nonce="abc123"'
        result = parse_digest_challenge(challenge)

        assert result["realm"] == "vsn300"
        assert result["nonce"] == "abc123"

    def test_parse_unquoted_values(self) -> None:
        """Test parsing challenge with unquoted values."""
        challenge = "Digest realm=vsn300, nonce=abc123"
        result = parse_digest_challenge(challenge)

        assert result["realm"] == "vsn300"
        assert result["nonce"] == "abc123"

    def test_parse_with_opaque(self) -> None:
        """Test parsing challenge with opaque parameter."""
        challenge = 'Digest realm="vsn300", nonce="abc123", opaque="xyz789"'
        result = parse_digest_challenge(challenge)

        assert result["opaque"] == "xyz789"

    def test_parse_with_algorithm(self) -> None:
        """Test parsing challenge with algorithm parameter."""
        challenge = 'Digest realm="vsn300", nonce="abc123", algorithm="MD5"'
        result = parse_digest_challenge(challenge)

        assert result["algorithm"] == "MD5"


class TestBuildDigestHeader:
    """Tests for build_digest_header function."""

    def test_build_header_without_qop(self) -> None:
        """Test building header without qop."""
        challenge_params = {
            "realm": "vsn300",
            "nonce": "abc123",
        }

        result = build_digest_header(
            username="guest",
            password="password",
            challenge_params=challenge_params,
            method="GET",
            uri="/v1/livedata",
        )

        assert 'username="guest"' in result
        assert 'realm="vsn300"' in result
        assert 'nonce="abc123"' in result
        assert 'uri="/v1/livedata"' in result
        assert 'response="' in result

    def test_build_header_with_qop(self) -> None:
        """Test building header with qop."""
        challenge_params = {
            "realm": "vsn300",
            "nonce": "abc123",
            "qop": "auth",
        }

        result = build_digest_header(
            username="guest",
            password="password",
            challenge_params=challenge_params,
            method="GET",
            uri="/v1/livedata",
        )

        assert 'username="guest"' in result
        assert "qop=auth" in result  # qop without quotes
        assert "nc=" in result
        assert 'cnonce="' in result
        assert 'algorithm="MD5"' in result

    def test_build_header_with_opaque(self) -> None:
        """Test building header with opaque."""
        challenge_params = {
            "realm": "vsn300",
            "nonce": "abc123",
            "opaque": "xyz789",
        }

        result = build_digest_header(
            username="guest",
            password="password",
            challenge_params=challenge_params,
            method="GET",
            uri="/v1/livedata",
        )

        assert 'opaque="xyz789"' in result


class TestGetVSN700BasicAuth:
    """Tests for get_vsn700_basic_auth function."""

    def test_basic_auth_encoding(self) -> None:
        """Test basic auth credentials are base64 encoded."""
        result = get_vsn700_basic_auth("guest", "password")

        # Base64 of "guest:password"
        expected = base64.b64encode(b"guest:password").decode("utf-8")
        assert result == expected

    def test_basic_auth_empty_password(self) -> None:
        """Test basic auth with empty password."""
        result = get_vsn700_basic_auth("guest", "")

        expected = base64.b64encode(b"guest:").decode("utf-8")
        assert result == expected

    def test_basic_auth_special_characters(self) -> None:
        """Test basic auth with special characters."""
        result = get_vsn700_basic_auth("user@domain", "p@ss:word!")

        expected = base64.b64encode(b"user@domain:p@ss:word!").decode("utf-8")
        assert result == expected


class TestDetectModelFromStatus:
    """Tests for _detect_model_from_status function."""

    def test_detect_vsn300_by_board_model(self) -> None:
        """Test detecting VSN300 by board_model."""
        status_data = {
            "keys": {
                "logger.board_model": {"value": "WIFI LOGGER CARD"},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN300"

    def test_detect_vsn300_by_serial_format(self) -> None:
        """Test detecting VSN300 by serial number format."""
        status_data = {
            "keys": {
                "logger.sn": {"value": "111033-3N16-1421"},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN300"

    def test_detect_vsn700_by_mac_format(self) -> None:
        """Test detecting VSN700 by MAC address format."""
        status_data = {
            "keys": {
                "logger.loggerId": {"value": "ac:1f:0f:b0:50:b5"},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN700"

    def test_detect_vsn300_by_many_keys(self) -> None:
        """Test detecting VSN300 by rich status data."""
        status_data = {"keys": {f"key_{i}": {"value": i} for i in range(15)}}

        result = _detect_model_from_status(status_data)
        assert result == "VSN300"

    def test_detect_vsn700_by_few_keys(self) -> None:
        """Test detecting VSN700 by minimal status data."""
        status_data = {
            "keys": {
                "key1": {"value": 1},
                "key2": {"value": 2},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN700"

    def test_detect_fails_with_ambiguous_data(self) -> None:
        """Test detection fails with ambiguous data."""
        status_data = {"keys": {f"key_{i}": {"value": i} for i in range(5)}}

        with pytest.raises(VSNDetectionError, match="Could not determine"):
            _detect_model_from_status(status_data)


class TestGetVSN300DigestHeader:
    """Tests for get_vsn300_digest_header function."""

    @pytest.mark.asyncio
    async def test_successful_digest_challenge(self) -> None:
        """Test successful digest challenge and response."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.headers = {"WWW-Authenticate": 'Digest realm="vsn300", nonce="abc123"'}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            result = await get_vsn300_digest_header(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert 'username="guest"' in result
        assert 'realm="vsn300"' in result

    @pytest.mark.asyncio
    async def test_non_401_response_raises_error(self) -> None:
        """Test non-401 response raises authentication error."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNAuthenticationError, match="Expected 401"),
        ):
            await get_vsn300_digest_header(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_missing_www_authenticate_raises_error(self) -> None:
        """Test missing WWW-Authenticate header raises error."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.headers = {}  # No WWW-Authenticate
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNAuthenticationError, match="challenge missing"),
        ):
            await get_vsn300_digest_header(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        """Test connection error is wrapped."""
        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNConnectionError, match="challenge request failed"),
        ):
            await get_vsn300_digest_header(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )


class TestDetectVSNModel:
    """Tests for detect_vsn_model function."""

    @pytest.mark.asyncio
    async def test_detect_vsn300_from_digest_auth(self) -> None:
        """Test detecting VSN300 from digest authentication."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.headers = {"WWW-Authenticate": 'Digest realm="vsn300", nonce="abc123"'}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            model, requires_auth = await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert model == "VSN300"
        assert requires_auth is True

    @pytest.mark.asyncio
    async def test_detect_vsn700_from_basic_auth(self) -> None:
        """Test detecting VSN700 from basic authentication."""
        # First request: 401 without digest
        mock_response_401 = MagicMock()
        mock_response_401.status = 401
        mock_response_401.headers = {"WWW-Authenticate": "Basic realm=vsn700"}
        mock_response_401.__aenter__ = AsyncMock(return_value=mock_response_401)
        mock_response_401.__aexit__ = AsyncMock(return_value=None)

        # Second request with basic auth: 200
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_response_200.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[mock_response_401, mock_response_200])

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            model, requires_auth = await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert model == "VSN700"
        assert requires_auth is True

    @pytest.mark.asyncio
    async def test_detect_model_no_auth_required(self) -> None:
        """Test detecting model when no auth is required."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(
            return_value={
                "keys": {
                    "logger.board_model": {"value": "WIFI LOGGER CARD"},
                }
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            model, requires_auth = await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert model == "VSN300"
        assert requires_auth is False

    @pytest.mark.asyncio
    async def test_detect_unexpected_status_raises_error(self) -> None:
        """Test unexpected status code raises detection error."""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNDetectionError, match="Unexpected response status"),
        ):
            await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_detect_preemptive_auth_fails_non_200(self) -> None:
        """Test preemptive basic auth that returns non-success status."""
        # First request: 401 without digest (basic auth challenge)
        mock_response_401 = MagicMock()
        mock_response_401.status = 401
        mock_response_401.headers = {"WWW-Authenticate": "Basic realm=vsn700"}
        mock_response_401.__aenter__ = AsyncMock(return_value=mock_response_401)
        mock_response_401.__aexit__ = AsyncMock(return_value=None)

        # Second request with basic auth: 403 Forbidden
        mock_response_403 = MagicMock()
        mock_response_403.status = 403
        mock_response_403.__aenter__ = AsyncMock(return_value=mock_response_403)
        mock_response_403.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[mock_response_401, mock_response_403])

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNDetectionError, match="authentication failed"),
        ):
            await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_detect_preemptive_auth_connection_error(self) -> None:
        """Test preemptive basic auth with connection error."""
        # First request: 401 without digest
        mock_response_401 = MagicMock()
        mock_response_401.status = 401
        mock_response_401.headers = {"WWW-Authenticate": "Basic realm=vsn700"}
        mock_response_401.__aenter__ = AsyncMock(return_value=mock_response_401)
        mock_response_401.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        # First call returns 401, second call raises connection error
        mock_session.get = MagicMock(
            side_effect=[mock_response_401, aiohttp.ClientError("Connection lost")]
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNDetectionError, match="connection failed"),
        ):
            await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_detect_model_json_parse_error(self) -> None:
        """Test model detection with JSON parse error on 200 response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNDetectionError, match="Failed to parse"),
        ):
            await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_detect_vsn700_from_x_digest_header(self) -> None:
        """Test detecting VSN300 from X-Digest header variation."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.headers = {"WWW-Authenticate": 'X-Digest realm="vsn300", nonce="abc123"'}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            model, requires_auth = await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert model == "VSN300"
        assert requires_auth is True

    @pytest.mark.asyncio
    async def test_detect_vsn700_no_auth_from_mac_address(self) -> None:
        """Test detecting VSN700 from MAC address in status when no auth required."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(
            return_value={
                "keys": {
                    "logger.loggerId": {"value": "ac:1f:0f:b0:50:b5"},
                }
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
            new_callable=AsyncMock,
        ):
            model, requires_auth = await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )

        assert model == "VSN700"
        assert requires_auth is False


class TestDetectModelFromStatusAdditional:
    """Additional tests for _detect_model_from_status function edge cases."""

    def test_detect_vsn300_by_serial_format_variant(self) -> None:
        """Test detecting VSN300 by serial number format with letters."""
        status_data = {
            "keys": {
                "logger.sn": {"value": "123456-ABCD-5678"},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN300"

    def test_detect_vsn700_by_minimal_keys(self) -> None:
        """Test detecting VSN700 with exactly 3 keys."""
        status_data = {
            "keys": {
                "key1": {"value": 1},
                "key2": {"value": 2},
                "key3": {"value": 3},
            }
        }

        result = _detect_model_from_status(status_data)
        assert result == "VSN700"

    def test_empty_keys_detects_vsn700(self) -> None:
        """Test empty keys dict is detected as VSN700 (minimal data)."""
        status_data = {"keys": {}}

        # Empty keys (len=0) falls into the "len(keys) <= 3" branch
        # which returns VSN700 for minimal status data
        result = _detect_model_from_status(status_data)
        assert result == "VSN700"

    @pytest.mark.asyncio
    async def test_detect_connection_error(self) -> None:
        """Test connection error is wrapped."""
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.auth.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNConnectionError, match="connection error"),
        ):
            await detect_vsn_model(
                session=mock_session,
                base_url="http://192.168.1.100",
                username="guest",
                password="password",
            )
