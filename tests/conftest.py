"""Common fixtures for ABB FIMER PVI VSN REST tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import (
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    VSN_MODEL_300,
)
from custom_components.abb_fimer_pvi_vsn_rest.coordinator import ABBFimerPVIVSNRestCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import CoreState, HomeAssistant

# Test configuration values
TEST_HOST = "192.168.1.100"
TEST_USERNAME = DEFAULT_USERNAME
TEST_PASSWORD = ""
TEST_VSN_MODEL = VSN_MODEL_300
TEST_SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL
TEST_LOGGER_SN = "111033-3N16-1421"
TEST_INVERTER_SN = "077909-3G82-3112"


@dataclass
class MockDiscoveredDevice:
    """Mock DiscoveredDevice for testing."""

    device_id: str
    raw_device_id: str
    device_type: str
    device_model: str | None
    manufacturer: str | None
    firmware_version: str | None
    hardware_version: str | None
    is_datalogger: bool


@dataclass
class MockDiscoveryResult:
    """Mock DiscoveryResult for testing."""

    vsn_model: str
    logger_sn: str
    logger_model: str | None
    firmware_version: str | None
    hostname: str | None
    devices: list[MockDiscoveredDevice]
    status_data: dict[str, Any]
    requires_auth: bool = False

    def get_title(self) -> str:
        """Return a title for the device."""
        return f"{self.vsn_model} ({self.logger_sn})"


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return {
        CONF_HOST: TEST_HOST,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_VSN_MODEL: TEST_VSN_MODEL,
    }


@pytest.fixture
def mock_config_entry_options() -> dict:
    """Return mock config entry options."""
    return {
        CONF_SCAN_INTERVAL: TEST_SCAN_INTERVAL,
    }


@pytest.fixture
def mock_discovered_devices() -> list[MockDiscoveredDevice]:
    """Return mock discovered devices."""
    return [
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
        MockDiscoveredDevice(
            device_id=TEST_INVERTER_SN,
            raw_device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            device_model="PVI-10.0-OUTD",
            manufacturer="Power-One",
            firmware_version="C008",
            hardware_version=None,
            is_datalogger=False,
        ),
    ]


@pytest.fixture
def mock_discovery_result(
    mock_discovered_devices: list[MockDiscoveredDevice],
) -> MockDiscoveryResult:
    """Return mock discovery result."""
    return MockDiscoveryResult(
        vsn_model=TEST_VSN_MODEL,
        logger_sn=TEST_LOGGER_SN,
        logger_model="WIFI LOGGER CARD",
        firmware_version="1.9.2",
        hostname=f"ABB-{TEST_LOGGER_SN}.local",
        devices=mock_discovered_devices,
        status_data={},
        requires_auth=False,
    )


@pytest.fixture
def mock_normalized_data() -> dict[str, Any]:
    """Return mock normalized data from the client.

    The coordinator data structure is:
    {
        "devices": {
            "<device_id>": {
                "points": {
                    "<point_name>": {"value": ..., ...}
                }
            }
        }
    }
    """
    return {
        "devices": {
            TEST_INVERTER_SN: {
                "points": {
                    "watts": {
                        "value": 5000,
                        "ha_display_name": "Power AC",
                        "ha_unit_of_measurement": "W",
                        "ha_device_class": "power",
                        "ha_state_class": "measurement",
                        "label": "AC Power",
                        "description": "AC Power output",
                        "vsn300_name": "m103_1_W",
                        "vsn700_name": "Pgrid",
                        "category": "Inverter",
                        "model": "M103",
                        "sunspec_name": "W",
                    },
                    "watthours": {
                        "value": 123456789,
                        "ha_display_name": "Energy AC - Produced (Lifetime)",
                        "ha_unit_of_measurement": "Wh",
                        "ha_device_class": "energy",
                        "ha_state_class": "total_increasing",
                        "label": "Lifetime Energy",
                        "description": "Total energy produced",
                        "vsn300_name": "m103_1_WH",
                        "vsn700_name": "Etot",
                        "category": "Inverter",
                        "model": "M103",
                        "sunspec_name": "WH",
                    },
                    "cabinet_temperature": {
                        "value": 45.5,
                        "ha_display_name": "Temperature - Cabinet",
                        "ha_unit_of_measurement": "°C",
                        "ha_device_class": "temperature",
                        "ha_state_class": "measurement",
                        "label": "Cabinet Temperature",
                        "description": "Inverter cabinet temperature",
                        "vsn300_name": "m64061_1_TmpCab",
                        "vsn700_name": "Tcab",
                        "category": "Inverter",
                        "model": "M64061",
                        "sunspec_name": "TmpCab",
                    },
                },
            },
            TEST_LOGGER_SN: {
                "points": {
                    "firmware_version": {
                        "value": "1.9.2",
                        "ha_display_name": "Firmware Version",
                        "ha_unit_of_measurement": None,
                        "ha_device_class": None,
                        "ha_state_class": None,
                        "label": "Firmware Version",
                        "description": "Datalogger firmware version",
                        "vsn300_name": "fw_ver",
                        "vsn700_name": "fw_ver",
                        "category": "System",
                        "entity_category": "diagnostic",
                        "model": "",
                        "sunspec_name": "fw_ver",
                    },
                },
            },
        },
    }


@pytest.fixture
def mock_vsn_client(
    mock_normalized_data: dict[str, dict[str, Any]],
    mock_discovered_devices: list[MockDiscoveredDevice],
) -> Generator[MagicMock]:
    """Mock ABBFimerVSNRestClient."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.vsn_model = TEST_VSN_MODEL
        mock_client.discovered_devices = mock_discovered_devices
        mock_client.get_normalized_data = AsyncMock(return_value=mock_normalized_data)
        mock_client.close = AsyncMock()
        yield mock_client


@pytest.fixture
def mock_discover_vsn_device(
    mock_discovery_result: MockDiscoveryResult,
) -> Generator[AsyncMock]:
    """Mock discover_vsn_device function."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
        return_value=mock_discovery_result,
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_discover_vsn_device_config_flow(
    mock_discovery_result: MockDiscoveryResult,
) -> Generator[AsyncMock]:
    """Mock discover_vsn_device function for config flow tests."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        return_value=mock_discovery_result,
    ) as mock_discover:
        yield mock_discover


@pytest.fixture
def mock_check_socket_connection() -> Generator[AsyncMock]:
    """Mock check_socket_connection function."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.check_socket_connection",
        return_value=None,
    ) as mock_check:
        yield mock_check


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture
def mock_config_entry(
    hass: HomeAssistant,
    mock_config_entry_data: dict,
    mock_config_entry_options: dict,
) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = mock_config_entry_data
    entry.options = mock_config_entry_options
    entry.unique_id = TEST_LOGGER_SN.lower()
    entry.title = f"{TEST_VSN_MODEL} ({TEST_LOGGER_SN})"
    entry.version = 1
    return entry


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock HomeAssistant instance for direct unit tests.

    This fixture is used for tests that don't require full HA integration loading.
    It provides a minimal mock that can be used to test coordinator and other
    component logic directly without needing the real HA event bus/services.

    Note: For integration tests, use the built-in `hass` fixture from
    pytest_homeassistant_custom_component instead.
    """
    mock = MagicMock(spec=HomeAssistant)
    mock.config_entries = MagicMock()
    mock.config_entries.async_entries = MagicMock(return_value=[])
    mock.data = {}  # Required for enable_custom_integrations fixture

    # Add state for coordinator base class checks
    mock.state = CoreState.running

    # Add loop for async operations (required by DataUpdateCoordinator)
    mock.loop = asyncio.get_event_loop()

    # Add bus for event firing
    mock.bus = MagicMock()
    mock.bus.async_fire = MagicMock()

    # Add config for path resolution
    mock.config = MagicMock()
    mock.config.is_allowed_path = MagicMock(return_value=True)

    # Add services
    mock.services = MagicMock()
    mock.services.async_call = AsyncMock()

    return mock


@pytest.fixture
def mock_coordinator(
    mock_hass: MagicMock,
    mock_vsn_client: MagicMock,
    mock_discovery_result: MockDiscoveryResult,
) -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=ABBFimerPVIVSNRestCoordinator)
    coordinator.hass = mock_hass
    coordinator.client = mock_vsn_client
    coordinator.vsn_model = TEST_VSN_MODEL
    coordinator.discovery_result = mock_discovery_result
    coordinator.discovered_devices = mock_discovery_result.devices
    coordinator.update_interval = timedelta(seconds=TEST_SCAN_INTERVAL)
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.device_id = None
    coordinator._consecutive_failures = 0
    coordinator._repair_issue_created = False
    coordinator._failure_start_time = None

    return coordinator
