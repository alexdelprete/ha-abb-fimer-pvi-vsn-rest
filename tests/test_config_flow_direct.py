"""Direct unit tests for ABB FIMER PVI VSN REST config flow.

These tests don't require full HA integration loading - they test the
config flow logic directly using mocks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.config_flow import (
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
    validate_connection,
)

from .conftest import (
    TEST_HOST,
    TEST_LOGGER_SN,
    TEST_PASSWORD,
    TEST_USERNAME,
    TEST_VSN_MODEL,
    MockDiscoveredDevice,
    MockDiscoveryResult,
)


class TestValidateConnection:
    """Tests for validate_connection function."""

    @pytest.fixture
    def mock_discovery_result(self) -> MockDiscoveryResult:
        """Create a mock discovery result."""
        return MockDiscoveryResult(
            vsn_model=TEST_VSN_MODEL,
            logger_sn=TEST_LOGGER_SN,
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname=f"ABB-{TEST_LOGGER_SN}.local",
            devices=[
                MockDiscoveredDevice(
                    device_id=TEST_LOGGER_SN,
                    raw_device_id=TEST_LOGGER_SN,
                    device_type="datalogger",
                    device_model="WIFI LOGGER CARD",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
            ],
            status_data={},
            requires_auth=False,
        )

    @pytest.mark.asyncio
    async def test_validate_connection_success(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test successful connection validation."""
        mock_hass = MagicMock()
        mock_session = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
                return_value=mock_session,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
        ):
            result = await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

        assert result["vsn_model"] == TEST_VSN_MODEL
        assert result["logger_sn"] == TEST_LOGGER_SN
        assert result["title"] == mock_discovery_result.get_title()
        assert result["requires_auth"] is False

    @pytest.mark.asyncio
    async def test_validate_connection_adds_http_prefix(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test http:// is added to host if not present."""
        mock_hass = MagicMock()
        mock_session = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ) as mock_socket,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
                return_value=mock_session,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
        ):
            await validate_connection(mock_hass, "192.168.1.100", TEST_USERNAME, TEST_PASSWORD)

        # Verify http:// was added
        mock_socket.assert_called_once()
        call_args = mock_socket.call_args[0][0]
        assert call_args == "http://192.168.1.100"

    @pytest.mark.asyncio
    async def test_validate_connection_preserves_https(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test https:// prefix is preserved."""
        mock_hass = MagicMock()
        mock_session = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ) as mock_socket,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
                return_value=mock_session,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
        ):
            await validate_connection(
                mock_hass, "https://192.168.1.100", TEST_USERNAME, TEST_PASSWORD
            )

        call_args = mock_socket.call_args[0][0]
        assert call_args == "https://192.168.1.100"

    @pytest.mark.asyncio
    async def test_validate_connection_auth_error(self) -> None:
        """Test authentication error is propagated."""
        mock_hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                side_effect=VSNAuthenticationError("Invalid credentials"),
            ),
            pytest.raises(VSNAuthenticationError),
        ):
            await validate_connection(mock_hass, TEST_HOST, "wrong", "wrong")

    @pytest.mark.asyncio
    async def test_validate_connection_connection_error(self) -> None:
        """Test connection error is propagated."""
        mock_hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("Connection refused"),
            ),
            pytest.raises(VSNConnectionError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_unexpected_error(self) -> None:
        """Test unexpected errors are wrapped in VSNClientError."""
        mock_hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                side_effect=ValueError("Unexpected error"),
            ),
            pytest.raises(VSNClientError, match="Unexpected error"),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_default_username(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test empty username defaults to guest."""
        mock_hass = MagicMock()
        mock_session = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.async_get_clientsession",
                return_value=mock_session,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ) as mock_discover,
        ):
            await validate_connection(mock_hass, TEST_HOST, "", "")

        # Verify default username was used
        call_kwargs = mock_discover.call_args[1]
        assert call_kwargs["username"] == "guest"


class TestErrorCodes:
    """Tests for error code constants."""

    def test_error_codes_defined(self) -> None:
        """Test error codes are properly defined."""
        assert ERROR_CANNOT_CONNECT == "cannot_connect"
        assert ERROR_INVALID_AUTH == "invalid_auth"
        assert ERROR_TIMEOUT == "timeout"
        assert ERROR_UNKNOWN == "unknown"


class TestMockDiscoveryResult:
    """Tests for MockDiscoveryResult fixture."""

    def test_get_title(self) -> None:
        """Test get_title returns correct format."""
        result = MockDiscoveryResult(
            vsn_model="VSN300",
            logger_sn="111033-3N16-1421",
            logger_model=None,
            firmware_version=None,
            hostname=None,
            devices=[],
            status_data={},
        )

        assert result.get_title() == "VSN300 (111033-3N16-1421)"

    def test_requires_auth_default(self) -> None:
        """Test requires_auth defaults to False."""
        result = MockDiscoveryResult(
            vsn_model="VSN300",
            logger_sn="111033-3N16-1421",
            logger_model=None,
            firmware_version=None,
            hostname=None,
            devices=[],
            status_data={},
        )

        assert result.requires_auth is False

    def test_requires_auth_true(self) -> None:
        """Test requires_auth can be set to True."""
        result = MockDiscoveryResult(
            vsn_model="VSN300",
            logger_sn="111033-3N16-1421",
            logger_model=None,
            firmware_version=None,
            hostname=None,
            devices=[],
            status_data={},
            requires_auth=True,
        )

        assert result.requires_auth is True
