"""Direct unit tests for ABB FIMER PVI VSN REST config flow.

These tests don't require full HA integration loading - they test the
config flow logic directly using mocks.
"""

from __future__ import annotations

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
    ABBFimerPVIVSNRestConfigFlow,
    ABBFimerPVIVSNRestOptionsFlow,
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


class TestValidateConnectionSSLErrors:
    """Tests for SSL/TLS error handling in validate_connection."""

    @pytest.mark.asyncio
    async def test_validate_connection_ssl_error(self) -> None:
        """Test SSL certificate error is logged appropriately."""
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
                side_effect=VSNConnectionError("SSL certificate verify failed"),
            ),
            pytest.raises(VSNConnectionError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_self_signed_cert_error(self) -> None:
        """Test self-signed certificate error is logged appropriately."""
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
                side_effect=VSNConnectionError("self-signed certificate in chain"),
            ),
            pytest.raises(VSNConnectionError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_client_error(self) -> None:
        """Test VSNClientError is propagated correctly."""
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
                side_effect=VSNClientError("Client error occurred"),
            ),
            pytest.raises(VSNClientError, match="Client error occurred"),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_auth_error_with_debug_hint(self) -> None:
        """Test auth error with Enable debug logging already in message."""
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
                side_effect=VSNAuthenticationError(
                    "Invalid credentials. Enable debug logging for details"
                ),
            ),
            pytest.raises(VSNAuthenticationError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_client_error_with_debug_hint(self) -> None:
        """Test client error with Enable debug logging already in message."""
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
                side_effect=VSNClientError("Error. Enable debug logging for details"),
            ),
            pytest.raises(VSNClientError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)

    @pytest.mark.asyncio
    async def test_validate_connection_connection_error_with_debug_hint(self) -> None:
        """Test connection error with Enable debug logging already in message."""
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
                side_effect=VSNConnectionError("Error. Enable debug logging for more"),
            ),
            pytest.raises(VSNConnectionError),
        ):
            await validate_connection(mock_hass, TEST_HOST, TEST_USERNAME, TEST_PASSWORD)


class TestConfigFlowAsyncStepUser:
    """Tests for ABBFimerPVIVSNRestConfigFlow.async_step_user."""

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
    async def test_step_user_show_form(self) -> None:
        """Test showing the initial form."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_step_user_timeout_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling timeout error in user step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("Connection timeout occurred"),
            ),
        ):
            result = await flow.async_step_user(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_TIMEOUT

    @pytest.mark.asyncio
    async def test_step_user_connection_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling connection error in user step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("Connection refused"),
            ),
        ):
            result = await flow.async_step_user(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_CANNOT_CONNECT

    @pytest.mark.asyncio
    async def test_step_user_auth_error(self, mock_discovery_result: MockDiscoveryResult) -> None:
        """Test handling authentication error in user step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNAuthenticationError("Invalid credentials"),
            ),
        ):
            result = await flow.async_step_user(
                user_input={
                    "host": TEST_HOST,
                    "username": "wrong",
                    "password": "wrong",
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_INVALID_AUTH

    @pytest.mark.asyncio
    async def test_step_user_client_error(self, mock_discovery_result: MockDiscoveryResult) -> None:
        """Test handling client error in user step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNClientError("Client error"),
            ),
        ):
            result = await flow.async_step_user(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_UNKNOWN

    @pytest.mark.asyncio
    async def test_step_user_unexpected_exception(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling unexpected exception in user step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Unexpected"),
            ),
        ):
            result = await flow.async_step_user(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_UNKNOWN


class TestConfigFlowAsyncStepReconfigure:
    """Tests for ABBFimerPVIVSNRestConfigFlow.async_step_reconfigure."""

    @pytest.fixture
    def mock_discovery_result(self) -> MockDiscoveryResult:
        """Create a mock discovery result."""
        return MockDiscoveryResult(
            vsn_model=TEST_VSN_MODEL,
            logger_sn=TEST_LOGGER_SN,
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname=f"ABB-{TEST_LOGGER_SN}.local",
            devices=[],
            status_data={},
            requires_auth=True,
        )

    @pytest.mark.asyncio
    async def test_step_reconfigure_show_form(self) -> None:
        """Test showing the reconfigure form."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {
            "host": TEST_HOST,
            "username": TEST_USERNAME,
        }

        with patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry):
            result = await flow.async_step_reconfigure(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure"

    @pytest.mark.asyncio
    async def test_step_reconfigure_timeout_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling timeout error in reconfigure step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {"host": TEST_HOST, "username": TEST_USERNAME}

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("timeout error"),
            ),
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_TIMEOUT

    @pytest.mark.asyncio
    async def test_step_reconfigure_connection_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling connection error in reconfigure step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {"host": TEST_HOST, "username": TEST_USERNAME}

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("Connection refused"),
            ),
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_CANNOT_CONNECT

    @pytest.mark.asyncio
    async def test_step_reconfigure_auth_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling auth error in reconfigure step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {"host": TEST_HOST, "username": TEST_USERNAME}

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNAuthenticationError("Invalid credentials"),
            ),
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "host": TEST_HOST,
                    "username": "wrong",
                    "password": "wrong",
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_INVALID_AUTH

    @pytest.mark.asyncio
    async def test_step_reconfigure_client_error(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling client error in reconfigure step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {"host": TEST_HOST, "username": TEST_USERNAME}

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=VSNClientError("Client error"),
            ),
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_UNKNOWN

    @pytest.mark.asyncio
    async def test_step_reconfigure_unexpected_exception(
        self, mock_discovery_result: MockDiscoveryResult
    ) -> None:
        """Test handling unexpected exception in reconfigure step."""

        flow = ABBFimerPVIVSNRestConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {"host": TEST_HOST, "username": TEST_USERNAME}

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.validate_connection",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Unexpected"),
            ),
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "host": TEST_HOST,
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == ERROR_UNKNOWN


class TestOptionsFlow:
    """Tests for ABBFimerPVIVSNRestOptionsFlow."""

    @pytest.mark.asyncio
    async def test_options_step_init_show_form(self) -> None:
        """Test showing the options form."""

        mock_entry = MagicMock()
        mock_entry.options = {"scan_interval": 60}
        mock_entry.runtime_data = None  # No runtime data

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        with patch.object(
            ABBFimerPVIVSNRestOptionsFlow,
            "config_entry",
            new_callable=lambda: property(lambda self: mock_entry),
        ):
            result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_step_init_with_runtime_data(self) -> None:
        """Test options form with discovered devices."""

        # Create mock coordinator with discovered devices
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [
            MockDiscoveredDevice(
                device_id="111033-3N16-1421",
                raw_device_id="111033-3N16-1421",
                device_type="datalogger",
                device_model="VSN300",
                manufacturer="ABB",
                firmware_version="1.9.2",
                hardware_version=None,
                is_datalogger=True,
            ),
            MockDiscoveredDevice(
                device_id="077909-3G82-3112",
                raw_device_id="077909-3G82-3112",
                device_type="inverter_3phases",
                device_model="PVI-10.0-OUTD",
                manufacturer="Power-One",
                firmware_version="C008",
                hardware_version=None,
                is_datalogger=False,
            ),
        ]

        mock_runtime_data = MagicMock()
        mock_runtime_data.coordinator = mock_coordinator

        mock_entry = MagicMock()
        mock_entry.options = {"scan_interval": 60}
        mock_entry.runtime_data = mock_runtime_data

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        with patch.object(
            ABBFimerPVIVSNRestOptionsFlow,
            "config_entry",
            new_callable=lambda: property(lambda self: mock_entry),
        ):
            result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_step_init_submit(self) -> None:
        """Test submitting options form."""

        mock_entry = MagicMock()
        mock_entry.options = {"scan_interval": 60}
        mock_entry.runtime_data = None

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        with patch.object(
            ABBFimerPVIVSNRestOptionsFlow,
            "config_entry",
            new_callable=lambda: property(lambda self: mock_entry),
        ):
            result = await flow.async_step_init(user_input={"scan_interval": 120})

        assert result["type"] == "create_entry"
        assert result["data"]["scan_interval"] == 120

    @pytest.mark.asyncio
    async def test_options_step_init_with_meter_device(self) -> None:
        """Test options form with meter device discovered."""

        # Create mock coordinator with meter device
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [
            MockDiscoveredDevice(
                device_id="METER001",
                raw_device_id="METER001",
                device_type="meter",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            ),
        ]

        mock_runtime_data = MagicMock()
        mock_runtime_data.coordinator = mock_coordinator

        mock_entry = MagicMock()
        mock_entry.options = {"scan_interval": 60}
        mock_entry.runtime_data = mock_runtime_data

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        with patch.object(
            ABBFimerPVIVSNRestOptionsFlow,
            "config_entry",
            new_callable=lambda: property(lambda self: mock_entry),
        ):
            result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_step_init_with_battery_device(self) -> None:
        """Test options form with battery device discovered."""

        # Create mock coordinator with battery device
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [
            MockDiscoveredDevice(
                device_id="BATTERY001",
                raw_device_id="BATTERY001",
                device_type="battery",
                device_model="REACT2-5.0-TL",
                manufacturer="FIMER",
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            ),
        ]

        mock_runtime_data = MagicMock()
        mock_runtime_data.coordinator = mock_coordinator

        mock_entry = MagicMock()
        mock_entry.options = {"scan_interval": 60}
        mock_entry.runtime_data = mock_runtime_data

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        with patch.object(
            ABBFimerPVIVSNRestOptionsFlow,
            "config_entry",
            new_callable=lambda: property(lambda self: mock_entry),
        ):
            result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"


class TestOptionsFlowRegenerateEntityIds:
    """Tests for _regenerate_entity_ids in options flow."""

    @pytest.mark.asyncio
    async def test_regenerate_entity_ids_no_prefix(self) -> None:
        """Test regenerate entity IDs with no custom prefix does nothing."""

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=None)

        with (
            patch.object(
                ABBFimerPVIVSNRestOptionsFlow,
                "config_entry",
                new_callable=lambda: property(lambda self: mock_entry),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_entries_for_config_entry",
                return_value=[],
            ),
        ):
            await flow._regenerate_entity_ids({})

        # Should not fail even with no entities

    @pytest.mark.asyncio
    async def test_regenerate_entity_ids_with_prefix(self) -> None:
        """Test regenerate entity IDs with custom prefix."""

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=None)  # Target doesn't exist
        mock_registry.async_update_entity = MagicMock()

        with (
            patch.object(
                ABBFimerPVIVSNRestOptionsFlow,
                "config_entry",
                new_callable=lambda: property(lambda self: mock_entry),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
        ):
            await flow._regenerate_entity_ids({"prefix_inverter": "My Solar"})

        mock_registry.async_update_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_entity_ids_target_exists(self) -> None:
        """Test regenerate entity IDs when target already exists."""

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"

        mock_registry = MagicMock()
        # Target already exists
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_update_entity = MagicMock()

        with (
            patch.object(
                ABBFimerPVIVSNRestOptionsFlow,
                "config_entry",
                new_callable=lambda: property(lambda self: mock_entry),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
        ):
            await flow._regenerate_entity_ids({"prefix_inverter": "My Solar"})

        # Should not update because target exists
        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_regenerate_entity_ids_short_unique_id(self) -> None:
        """Test regenerate entity IDs skips entities with short unique_id."""

        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"

        flow = ABBFimerPVIVSNRestOptionsFlow()
        flow.hass = MagicMock()

        mock_entity = MagicMock()
        mock_entity.unique_id = "short_id"  # Too short, only 2 parts
        mock_entity.entity_id = "sensor.short_id"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch.object(
                ABBFimerPVIVSNRestOptionsFlow,
                "config_entry",
                new_callable=lambda: property(lambda self: mock_entry),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.config_flow.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
        ):
            await flow._regenerate_entity_ids({"prefix_inverter": "My Solar"})

        # Should not update because unique_id doesn't have enough parts
        mock_registry.async_update_entity.assert_not_called()
