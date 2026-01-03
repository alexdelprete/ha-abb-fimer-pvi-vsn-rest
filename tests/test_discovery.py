"""Tests for discovery module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery import (
    DiscoveredDevice,
    DiscoveryResult,
    _extract_devices,
    _extract_logger_info,
    discover_vsn_device,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNConnectionError,
)


class TestDiscoveredDevice:
    """Tests for DiscoveredDevice dataclass."""

    def test_create_inverter_device(self) -> None:
        """Test creating an inverter device."""
        device = DiscoveredDevice(
            device_id="077909-3G82-3112",
            raw_device_id="077909-3G82-3112",
            device_type="inverter_3phases",
            device_model="PVI-10.0-OUTD",
            manufacturer="Power-One",
            firmware_version="C008",
            hardware_version=None,
            is_datalogger=False,
        )
        assert device.device_id == "077909-3G82-3112"
        assert device.device_type == "inverter_3phases"
        assert device.device_model == "PVI-10.0-OUTD"
        assert device.manufacturer == "Power-One"
        assert device.firmware_version == "C008"
        assert device.is_datalogger is False

    def test_create_datalogger_device(self) -> None:
        """Test creating a datalogger device."""
        device = DiscoveredDevice(
            device_id="111033-3N16-1421",
            raw_device_id="a4:06:e9:7f:42:49",
            device_type="datalogger",
            device_model="VSN300",
            manufacturer="ABB",
            firmware_version="1.9.2",
            hardware_version=None,
            is_datalogger=True,
        )
        assert device.device_id == "111033-3N16-1421"
        assert device.raw_device_id == "a4:06:e9:7f:42:49"
        assert device.device_type == "datalogger"
        assert device.is_datalogger is True

    def test_create_meter_device(self) -> None:
        """Test creating a meter device."""
        device = DiscoveredDevice(
            device_id="METER001",
            raw_device_id="METER001",
            device_type="meter",
            device_model=None,
            manufacturer=None,
            firmware_version=None,
            hardware_version=None,
            is_datalogger=False,
        )
        assert device.device_type == "meter"
        assert device.device_model is None


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    @pytest.fixture
    def sample_devices(self) -> list[DiscoveredDevice]:
        """Create sample devices."""
        return [
            DiscoveredDevice(
                device_id="111033-3N16-1421",
                raw_device_id="a4:06:e9:7f:42:49",
                device_type="datalogger",
                device_model="VSN300",
                manufacturer="ABB",
                firmware_version="1.9.2",
                hardware_version=None,
                is_datalogger=True,
            ),
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
        ]

    def test_get_title(self, sample_devices: list[DiscoveredDevice]) -> None:
        """Test get_title method."""
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname="ABB-077909-3G82-3112.local",
            devices=sample_devices,
            status_data={},
        )
        assert result.get_title() == "VSN300 (111033-3N16-1421)"

    def test_get_main_inverter(self, sample_devices: list[DiscoveredDevice]) -> None:
        """Test get_main_inverter method."""
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model=None,
            firmware_version=None,
            hostname=None,
            devices=sample_devices,
            status_data={},
        )
        inverter = result.get_main_inverter()
        assert inverter is not None
        assert inverter.device_type == "inverter_3phases"
        assert inverter.device_id == "077909-3G82-3112"

    def test_get_main_inverter_no_inverter(self) -> None:
        """Test get_main_inverter when no inverter exists."""
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model=None,
            firmware_version=None,
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="111033-3N16-1421",
                    raw_device_id="a4:06:e9:7f:42:49",
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
            ],
            status_data={},
        )
        assert result.get_main_inverter() is None


class TestExtractLoggerInfo:
    """Tests for _extract_logger_info function."""

    def test_extract_vsn300_logger_info(self) -> None:
        """Test extracting logger info for VSN300."""
        status_data = {
            "keys": {
                "logger.sn": {"value": "111033-3N16-1421"},
                "logger.board_model": {"value": "WIFI LOGGER CARD"},
                "fw.release_number": {"value": "1.9.2"},
                "logger.hostname": {"value": "ABB-077909-3G82-3112.local"},
            }
        }
        info = _extract_logger_info(status_data, "VSN300")
        assert info["logger_sn"] == "111033-3N16-1421"
        assert info["logger_model"] == "WIFI LOGGER CARD"
        assert info["firmware_version"] == "1.9.2"
        assert info["hostname"] == "ABB-077909-3G82-3112.local"

    def test_extract_vsn700_logger_info(self) -> None:
        """Test extracting logger info for VSN700."""
        status_data = {
            "keys": {
                "logger.loggerId": {"value": "ac:1f:0f:b0:50:b5"},
                "logger.board_model": {"value": "VSN700"},
                "fw.release_number": {"value": "2.0.0"},
            }
        }
        info = _extract_logger_info(status_data, "VSN700")
        assert info["logger_sn"] == "ac:1f:0f:b0:50:b5"
        assert info["logger_model"] == "VSN700"
        assert info["firmware_version"] == "2.0.0"

    def test_extract_missing_logger_sn(self) -> None:
        """Test extracting logger info with missing S/N."""
        status_data = {"keys": {}}
        info = _extract_logger_info(status_data, "VSN300")
        assert info["logger_sn"] == "Unknown"

    def test_extract_empty_status(self) -> None:
        """Test extracting logger info from empty status."""
        info = _extract_logger_info({}, "VSN300")
        assert info["logger_sn"] == "Unknown"
        assert info["logger_model"] is None
        assert info["firmware_version"] is None


class TestExtractDevices:
    """Tests for _extract_devices function."""

    def test_extract_vsn300_devices(self) -> None:
        """Test extracting devices for VSN300."""
        livedata: dict[str, Any] = {
            "077909-3G82-3112": {
                "device_type": "inverter_3phases",
                "points": [
                    {"name": "C_Mn", "value": "Power-One"},
                    {"name": "C_Vr", "value": "C008"},
                ],
            },
        }
        status_data = {
            "keys": {
                "logger.sn": {"value": "111033-3N16-1421"},
                "device.modelDesc": {"value": "PVI-10.0-OUTD"},
                "fw.release_number": {"value": "1.9.2"},
            }
        }
        devices = _extract_devices(livedata, "VSN300", status_data)

        # Should have datalogger + inverter
        assert len(devices) == 2

        # Check datalogger
        datalogger = next(d for d in devices if d.is_datalogger)
        assert datalogger.device_id == "111033-3N16-1421"
        assert datalogger.device_model == "VSN300"

        # Check inverter
        inverter = next(d for d in devices if not d.is_datalogger)
        assert inverter.device_id == "077909-3G82-3112"
        assert inverter.device_type == "inverter_3phases"
        assert inverter.manufacturer == "Power-One"
        assert inverter.firmware_version == "C008"
        assert inverter.device_model == "PVI-10.0-OUTD"

    def test_extract_vsn700_devices(self) -> None:
        """Test extracting devices for VSN700."""
        livedata: dict[str, Any] = {
            "123668-3P81-3821": {
                "device_type": "inverter_3phases",
                "device_model": "REACT2-5.0-TL",
                "points": [
                    {"name": "C_Mn", "value": "FIMER"},
                    {"name": "C_Vr", "value": "B185"},
                ],
            },
        }
        status_data = {
            "keys": {
                "logger.loggerId": {"value": "ac:1f:0f:b0:50:b5"},
            }
        }
        devices = _extract_devices(livedata, "VSN700", status_data)

        assert len(devices) == 2

        # Check datalogger
        datalogger = next(d for d in devices if d.is_datalogger)
        assert datalogger.device_id == "ac1f0fb050b5"  # Cleaned MAC
        assert datalogger.device_model == "VSN700"

        # Check inverter
        inverter = next(d for d in devices if not d.is_datalogger)
        assert inverter.device_id == "123668-3P81-3821"
        assert inverter.device_model == "REACT2-5.0-TL"
        assert inverter.manufacturer == "FIMER"

    def test_extract_datalogger_with_sn_point(self) -> None:
        """Test extracting datalogger with S/N point in livedata."""
        livedata: dict[str, Any] = {
            "a4:06:e9:7f:42:49": {
                "device_type": "unknown",
                "points": [
                    {"name": "sn", "value": "111033-3N16-1421"},
                    {"name": "fw_ver", "value": "1.9.2"},
                ],
            },
        }
        status_data = {
            "keys": {
                "logger.sn": {"value": "111033-3N16-1421"},
            }
        }
        devices = _extract_devices(livedata, "VSN300", status_data)

        # Find the device from livedata (not the synthetic one)
        livedata_device = next(
            d for d in devices if d.raw_device_id == "a4:06:e9:7f:42:49"
        )
        assert livedata_device.device_id == "111033-3N16-1421"
        assert livedata_device.firmware_version == "1.9.2"
        assert livedata_device.is_datalogger is True


class TestDiscoverVSNDevice:
    """Tests for discover_vsn_device function."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock aiohttp session."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_discover_vsn300_device(self, mock_session: MagicMock) -> None:
        """Test discovering a VSN300 device."""
        status_response = {
            "keys": {
                "logger.sn": {"value": "111033-3N16-1421"},
                "logger.board_model": {"value": "WIFI LOGGER CARD"},
                "fw.release_number": {"value": "1.9.2"},
                "logger.hostname": {"value": "ABB-077909-3G82-3112.local"},
            }
        }
        livedata_response: dict[str, Any] = {
            "077909-3G82-3112": {
                "device_type": "inverter_3phases",
                "points": [
                    {"name": "C_Mn", "value": "Power-One"},
                    {"name": "C_Vr", "value": "C008"},
                ],
            },
        }

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery.detect_vsn_model",
                new_callable=AsyncMock,
                return_value=("VSN300", True),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery._fetch_status",
                new_callable=AsyncMock,
                return_value=status_response,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery._fetch_livedata",
                new_callable=AsyncMock,
                return_value=livedata_response,
            ),
        ):
            result = await discover_vsn_device(
                mock_session, "http://192.168.1.100", "guest", ""
            )

        assert result.vsn_model == "VSN300"
        assert result.requires_auth is True
        assert result.logger_sn == "111033-3N16-1421"
        assert result.logger_model == "WIFI LOGGER CARD"
        assert result.firmware_version == "1.9.2"
        assert result.hostname == "ABB-077909-3G82-3112.local"
        assert len(result.devices) == 2  # datalogger + inverter

    @pytest.mark.asyncio
    async def test_discover_vsn700_device(self, mock_session: MagicMock) -> None:
        """Test discovering a VSN700 device."""
        status_response = {
            "keys": {
                "logger.loggerId": {"value": "ac:1f:0f:b0:50:b5"},
                "fw.release_number": {"value": "2.0.0"},
            }
        }
        livedata_response: dict[str, Any] = {
            "123668-3P81-3821": {
                "device_type": "inverter_3phases",
                "device_model": "REACT2-5.0-TL",
                "points": [],
            },
        }

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery.detect_vsn_model",
                new_callable=AsyncMock,
                return_value=("VSN700", False),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery._fetch_status",
                new_callable=AsyncMock,
                return_value=status_response,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery._fetch_livedata",
                new_callable=AsyncMock,
                return_value=livedata_response,
            ),
        ):
            result = await discover_vsn_device(
                mock_session, "http://192.168.1.100", "guest", ""
            )

        assert result.vsn_model == "VSN700"
        assert result.requires_auth is False
        assert result.logger_sn == "ac:1f:0f:b0:50:b5"
        assert len(result.devices) == 2

    @pytest.mark.asyncio
    async def test_discover_connection_error(self, mock_session: MagicMock) -> None:
        """Test discovery with connection error."""
        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery.detect_vsn_model",
                new_callable=AsyncMock,
                side_effect=VSNConnectionError("Connection failed"),
            ),
        ):
            with pytest.raises(VSNConnectionError, match="Connection failed"):
                await discover_vsn_device(
                    mock_session, "http://192.168.1.100", "guest", ""
                )
