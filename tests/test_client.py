"""Tests for VSN REST API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client import (
    ABBFimerVSNRestClient,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery import (
    DiscoveredDevice,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNConnectionError,
)


class TestABBFimerVSNRestClientInit:
    """Tests for ABBFimerVSNRestClient initialization."""

    def test_init_default_values(self) -> None:
        """Test client initialization with default values."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(
            session=session,
            base_url="http://192.168.1.100",
        )
        assert client.base_url == "http://192.168.1.100"
        assert client.username == "guest"
        assert client.password == ""
        assert client.vsn_model is None
        assert client.timeout == 10
        assert client.requires_auth is True
        assert client._normalizer is None
        assert client._discovered_devices == []

    def test_init_with_custom_values(self) -> None:
        """Test client initialization with custom values."""
        session = MagicMock(spec=aiohttp.ClientSession)
        discovered_devices = [
            DiscoveredDevice(
                device_id="test",
                raw_device_id="test",
                device_type="inverter",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            )
        ]
        client = ABBFimerVSNRestClient(
            session=session,
            base_url="http://192.168.1.100/",  # Trailing slash
            username="admin",
            password="secret",  # noqa: S106
            vsn_model="VSN300",
            timeout=30,
            discovered_devices=discovered_devices,
            requires_auth=False,
        )
        assert client.base_url == "http://192.168.1.100"  # Trailing slash stripped
        assert client.username == "admin"
        assert client.password == "secret"  # noqa: S105
        assert client.vsn_model == "VSN300"
        assert client.timeout == 30
        assert client.requires_auth is False
        assert len(client._discovered_devices) == 1


class TestABBFimerVSNRestClientConnect:
    """Tests for ABBFimerVSNRestClient connect method."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock aiohttp session."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_connect_auto_detect_vsn300(self, mock_session: MagicMock) -> None:
        """Test connect with auto-detection returns VSN300."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.detect_vsn_model",
                new_callable=AsyncMock,
                return_value=("VSN300", True),
            ),
            patch.object(
                client,
                "_normalizer",
                None,
            ),
        ):
            # Mock the normalizer initialization
            mock_normalizer = MagicMock()
            mock_normalizer.async_load = AsyncMock()

            with patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.VSNDataNormalizer",
                return_value=mock_normalizer,
            ):
                result = await client.connect()

        assert result == "VSN300"
        assert client.vsn_model == "VSN300"
        assert client.requires_auth is True

    @pytest.mark.asyncio
    async def test_connect_with_preset_model(self, mock_session: MagicMock) -> None:
        """Test connect skips detection when model is preset."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN700",
        )

        mock_normalizer = MagicMock()
        mock_normalizer.async_load = AsyncMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.VSNDataNormalizer",
            return_value=mock_normalizer,
        ):
            result = await client.connect()

        assert result == "VSN700"
        mock_normalizer.async_load.assert_called_once()


class TestABBFimerVSNRestClientGetLivedata:
    """Tests for ABBFimerVSNRestClient get_livedata method."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock aiohttp session."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def sample_livedata(self) -> dict[str, Any]:
        """Sample livedata response."""
        return {
            "077909-3G82-3112": {
                "device_type": "inverter_3phases",
                "points": [
                    {"name": "W", "value": 5000},
                    {"name": "Wh", "value": 123456},
                ],
            },
        }

    @pytest.mark.asyncio
    async def test_get_livedata_vsn300(
        self, mock_session: MagicMock, sample_livedata: dict[str, Any]
    ) -> None:
        """Test get_livedata for VSN300."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN300",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_livedata)
        mock_response.headers = {}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.get_vsn300_digest_header",
                new_callable=AsyncMock,
                return_value="digest_value",
            ),
        ):
            result = await client.get_livedata()

        assert result == sample_livedata

    @pytest.mark.asyncio
    async def test_get_livedata_vsn700(
        self, mock_session: MagicMock, sample_livedata: dict[str, Any]
    ) -> None:
        """Test get_livedata for VSN700."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN700",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_livedata)
        mock_response.headers = {}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
            new_callable=AsyncMock,
        ):
            result = await client.get_livedata()

        assert result == sample_livedata

    @pytest.mark.asyncio
    async def test_get_livedata_no_auth_required(
        self, mock_session: MagicMock, sample_livedata: dict[str, Any]
    ) -> None:
        """Test get_livedata when no authentication is required."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN700",
            requires_auth=False,
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_livedata)
        mock_response.headers = {}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
            new_callable=AsyncMock,
        ):
            result = await client.get_livedata()

        assert result == sample_livedata

    @pytest.mark.asyncio
    async def test_get_livedata_401_error(self, mock_session: MagicMock) -> None:
        """Test get_livedata returns 401 authentication error."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN300",
        )

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.headers = {"WWW-Authenticate": "Digest"}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.get_vsn300_digest_header",
                new_callable=AsyncMock,
                return_value="digest_value",
            ),
            pytest.raises(VSNAuthenticationError, match="Authentication failed"),
        ):
            await client.get_livedata()

    @pytest.mark.asyncio
    async def test_get_livedata_http_error(self, mock_session: MagicMock) -> None:
        """Test get_livedata returns HTTP error."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN700",
        )

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.headers = {}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNConnectionError, match="HTTP 500"),
        ):
            await client.get_livedata()

    @pytest.mark.asyncio
    async def test_get_livedata_connection_error(self, mock_session: MagicMock) -> None:
        """Test get_livedata with connection error."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN700",
        )

        mock_session.get = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
            )
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
                new_callable=AsyncMock,
            ),
            pytest.raises(VSNConnectionError, match="Livedata request error"),
        ):
            await client.get_livedata()

    @pytest.mark.asyncio
    async def test_get_livedata_auto_connect(self, mock_session: MagicMock) -> None:
        """Test get_livedata triggers connect if not connected."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
        )

        sample_data: dict[str, Any] = {"device": {"points": []}}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_data)
        mock_response.headers = {}

        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with (
            patch.object(
                client, "connect", new_callable=AsyncMock, return_value="VSN300"
            ) as mock_connect,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.check_socket_connection",
                new_callable=AsyncMock,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.client.get_vsn300_digest_header",
                new_callable=AsyncMock,
                return_value="digest_value",
            ),
        ):
            # First call should trigger connect
            client.vsn_model = None
            await client.get_livedata()
            mock_connect.assert_called_once()


class TestABBFimerVSNRestClientGetNormalizedData:
    """Tests for ABBFimerVSNRestClient get_normalized_data method."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock aiohttp session."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_get_normalized_data(self, mock_session: MagicMock) -> None:
        """Test get_normalized_data returns normalized data."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN300",
        )

        raw_data: dict[str, Any] = {
            "077909-3G82-3112": {
                "device_type": "inverter_3phases",
                "points": [{"name": "W", "value": 5000}],
            }
        }

        normalized_data = {
            "devices": {
                "077909-3G82-3112": {
                    "device_type": "inverter_3phases",
                    "points": {"watts": {"value": 5000}},
                }
            }
        }

        # Set up normalizer mock
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = MagicMock(return_value=normalized_data)
        client._normalizer = mock_normalizer

        with patch.object(client, "get_livedata", new_callable=AsyncMock, return_value=raw_data):
            result = await client.get_normalized_data()

        assert result == normalized_data
        mock_normalizer.normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_normalized_data_connects_if_needed(self, mock_session: MagicMock) -> None:
        """Test get_normalized_data connects if normalizer not set."""
        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
        )

        raw_data: dict[str, Any] = {"device": {"points": []}}
        normalized_data: dict[str, Any] = {"devices": {}}

        mock_normalizer = MagicMock()
        mock_normalizer.normalize = MagicMock(return_value=normalized_data)

        async def mock_connect() -> str:
            client._normalizer = mock_normalizer
            client.vsn_model = "VSN300"
            return "VSN300"

        with (
            patch.object(client, "connect", new_callable=AsyncMock, side_effect=mock_connect),
            patch.object(client, "get_livedata", new_callable=AsyncMock, return_value=raw_data),
        ):
            result = await client.get_normalized_data()

        assert result == normalized_data

    @pytest.mark.asyncio
    async def test_get_normalized_data_injects_device_type(self, mock_session: MagicMock) -> None:
        """Test get_normalized_data injects device_type from discovered devices."""
        discovered_devices = [
            DiscoveredDevice(
                device_id="077909-3G82-3112",
                raw_device_id="077909-3G82-3112",
                device_type="inverter_3phases",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            )
        ]

        client = ABBFimerVSNRestClient(
            session=mock_session,
            base_url="http://192.168.1.100",
            vsn_model="VSN300",
            discovered_devices=discovered_devices,
        )

        raw_data: dict[str, Any] = {
            "077909-3G82-3112": {
                "points": [{"name": "W", "value": 5000}],
            }
        }

        normalized_data: dict[str, Any] = {"devices": {}}

        mock_normalizer = MagicMock()
        mock_normalizer.normalize = MagicMock(return_value=normalized_data)
        client._normalizer = mock_normalizer

        with patch.object(client, "get_livedata", new_callable=AsyncMock, return_value=raw_data):
            await client.get_normalized_data()

        # Check that device_type was injected
        call_args = mock_normalizer.normalize.call_args[0][0]
        assert call_args["077909-3G82-3112"]["device_type"] == "inverter_3phases"


class TestABBFimerVSNRestClientClose:
    """Tests for ABBFimerVSNRestClient close method."""

    @pytest.mark.asyncio
    async def test_close_clears_normalizer(self) -> None:
        """Test close clears the normalizer."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(
            session=session,
            base_url="http://192.168.1.100",
        )

        # Set a mock normalizer
        client._normalizer = MagicMock()

        await client.close()

        assert client._normalizer is None


class TestUpdateDiscoveredDevices:
    """Tests for update_discovered_devices method."""

    def test_updates_device_list(self) -> None:
        """Test that update_discovered_devices replaces the device list."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")

        new_devices = [
            DiscoveredDevice(
                device_id="new-device",
                raw_device_id="new-device",
                device_type="meter",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            )
        ]
        client.update_discovered_devices(new_devices)

        assert client._discovered_devices == new_devices

    def test_invalidates_device_type_map(self) -> None:
        """Test that update_discovered_devices invalidates the cached map."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")
        # Simulate a cached map
        client._device_type_map = {"old-key": "old-type"}

        client.update_discovered_devices([])

        assert client._device_type_map is None


class TestDeviceTypeInjection:
    """Tests for _ensure_device_type_map and _inject_device_types."""

    def test_ensure_device_type_map_builds_from_devices(self) -> None:
        """Test map is built from discovered devices."""
        session = MagicMock(spec=aiohttp.ClientSession)
        devices = [
            DiscoveredDevice(
                device_id="inv-001",
                raw_device_id="inv-001",
                device_type="inverter_3phases",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            ),
            DiscoveredDevice(
                device_id="logger-sn",
                raw_device_id="logger-sn",
                device_type="datalogger",
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=True,
                livedata_device_id="aa:bb:cc:dd:ee:ff",
            ),
        ]
        client = ABBFimerVSNRestClient(
            session=session, base_url="http://test", discovered_devices=devices
        )

        client._ensure_device_type_map()

        assert client._device_type_map is not None
        assert client._device_type_map["inv-001"] == "inverter_3phases"
        assert client._device_type_map["logger-sn"] == "datalogger"
        assert client._device_type_map["aa:bb:cc:dd:ee:ff"] == "datalogger"

    def test_ensure_device_type_map_skips_if_cached(self) -> None:
        """Test map is not rebuilt if already cached."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")
        client._device_type_map = {"existing": "type"}

        client._ensure_device_type_map()

        assert client._device_type_map == {"existing": "type"}

    def test_ensure_device_type_map_skips_if_no_devices(self) -> None:
        """Test map is not built if no discovered devices."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")

        client._ensure_device_type_map()

        assert client._device_type_map is None

    def test_inject_device_types(self) -> None:
        """Test device types are injected into raw data."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")
        client._device_type_map = {
            "inv-001": "inverter_3phases",
            "aa:bb:cc:dd:ee:ff": "datalogger",
        }

        raw_data = {
            "inv-001": {"points": []},
            "aa:bb:cc:dd:ee:ff": {"points": []},
            "unknown-device": {"points": []},
        }

        client._inject_device_types(raw_data)

        assert raw_data["inv-001"]["device_type"] == "inverter_3phases"
        assert raw_data["aa:bb:cc:dd:ee:ff"]["device_type"] == "datalogger"
        assert "device_type" not in raw_data["unknown-device"]

    def test_inject_device_types_noop_when_no_map(self) -> None:
        """Test injection is a no-op when map is empty."""
        session = MagicMock(spec=aiohttp.ClientSession)
        client = ABBFimerVSNRestClient(session=session, base_url="http://test")
        client._device_type_map = {}

        raw_data = {"inv-001": {"points": []}}
        client._inject_device_types(raw_data)

        assert "device_type" not in raw_data["inv-001"]

    def test_ensure_device_type_map_skips_device_without_type(self) -> None:
        """Test map skips devices with no device_type."""
        session = MagicMock(spec=aiohttp.ClientSession)
        devices = [
            DiscoveredDevice(
                device_id="no-type-device",
                raw_device_id="no-type-device",
                device_type="",  # Empty device_type
                device_model=None,
                manufacturer=None,
                firmware_version=None,
                hardware_version=None,
                is_datalogger=False,
            ),
        ]
        client = ABBFimerVSNRestClient(
            session=session, base_url="http://test", discovered_devices=devices
        )

        client._ensure_device_type_map()

        assert client._device_type_map == {}
