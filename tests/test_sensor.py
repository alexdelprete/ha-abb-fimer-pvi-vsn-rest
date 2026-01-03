"""Tests for ABB FIMER PVI VSN REST sensor platform."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.sensor import VSNSensor, async_setup_entry
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .conftest import TEST_INVERTER_SN, MockDiscoveredDevice

# Skip reason for tests requiring full integration loading
SKIP_INTEGRATION_LOADING = (
    "Skipped: HA integration loading fails in CI due to editable install path issues"
)


@pytest.fixture
def mock_add_entities() -> MagicMock:
    """Mock async_add_entities callback."""
    return MagicMock()


@pytest.fixture
def sample_point_data() -> dict:
    """Return sample point data for a sensor."""
    return {
        "value": 5000,
        "ha_display_name": "Power AC",
        "ha_unit_of_measurement": "W",
        "ha_device_class": "power",
        "ha_state_class": "measurement",
        "label": "AC Power",
        "description": "AC Power output",
        "vsn300_rest_name": "m103_1_W",
        "vsn700_rest_name": "Pgrid",
        "category": "Inverter",
        "sunspec_model": "M103",
    }


@pytest.fixture
def sample_device() -> MockDiscoveredDevice:
    """Return a sample discovered device."""
    return MockDiscoveredDevice(
        device_id=TEST_INVERTER_SN,
        raw_device_id=TEST_INVERTER_SN,
        device_type="inverter_3phases",
        device_model="PVI-10.0-OUTD",
        manufacturer="Power-One",
        firmware_version="C008",
        hardware_version=None,
        is_datalogger=False,
    )


@pytest.fixture
def mock_sensor_config_entry() -> MagicMock:
    """Create a mock config entry for sensor tests."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {}
    entry.options = {}
    return entry


def test_sensor_attributes(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test sensor has correct attributes."""
    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    # Test entity attributes (use _attr_ properties directly to avoid HA platform context)
    assert sensor.has_entity_name is True
    assert sensor._attr_name == "Power AC"  # Direct attribute access
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.device_class == SensorDeviceClass.POWER
    assert sensor.state_class == SensorStateClass.MEASUREMENT

    # Test unique_id format
    assert "watts" in sensor.unique_id
    assert DOMAIN in sensor.unique_id


def test_sensor_device_info(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test sensor has correct device info."""
    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    device_info = sensor.device_info
    assert device_info is not None
    assert "identifiers" in device_info


def test_sensor_native_value(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
    mock_normalized_data: dict,
) -> None:
    """Test sensor returns correct native value."""
    # Setup coordinator data
    mock_coordinator.data = mock_normalized_data

    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    # The native_value should come from coordinator data
    value = sensor.native_value
    assert value == 5000


def test_sensor_extra_state_attributes(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test sensor has extra state attributes."""
    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "device_id" in attrs
    assert "device_type" in attrs
    assert "point_name" in attrs
    assert attrs["point_name"] == "watts"
    assert attrs["device_id"] == TEST_INVERTER_SN


def test_sensor_diagnostic_entity_category(
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test diagnostic sensors have correct entity category."""
    diagnostic_point_data = {
        "value": "1.9.2",
        "ha_display_name": "Firmware Version",
        "ha_unit_of_measurement": None,
        "ha_device_class": None,
        "ha_state_class": None,
        "label": "Firmware Version",
        "description": "Datalogger firmware version",
        "entity_category": "diagnostic",
    }

    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="firmware_version",
        point_data=diagnostic_point_data,
    )

    assert sensor.entity_category == EntityCategory.DIAGNOSTIC


def test_sensor_unavailable_when_no_data(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test sensor is unavailable when no data in coordinator."""
    mock_coordinator.data = None

    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    assert sensor.native_value is None


def test_sensor_unavailable_when_device_not_in_data(
    sample_point_data: dict,
    sample_device: MockDiscoveredDevice,
    mock_coordinator: MagicMock,
    mock_sensor_config_entry: MagicMock,
) -> None:
    """Test sensor is unavailable when device not in coordinator data."""
    mock_coordinator.data = {"other_device": {}}

    sensor = VSNSensor(
        coordinator=mock_coordinator,
        config_entry=mock_sensor_config_entry,
        device_id=sample_device.device_id,
        device_type=sample_device.device_type,
        point_name="watts",
        point_data=sample_point_data,
    )

    assert sensor.native_value is None


@pytest.mark.skip(reason=SKIP_INTEGRATION_LOADING)
async def test_async_setup_entry_creates_sensors(
    hass: HomeAssistant,
    mock_config_entry,
    mock_coordinator: MagicMock,
    mock_normalized_data: dict,
    mock_add_entities: MagicMock,
) -> None:
    """Test async_setup_entry creates sensor entities."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_coordinator.data = mock_normalized_data
    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify entities were added
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]

    # Should have sensors for all points in normalized data
    assert len(entities) > 0
    assert all(isinstance(e, VSNSensor) for e in entities)
