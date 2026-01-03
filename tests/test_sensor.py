"""Tests for ABB FIMER PVI VSN REST sensor platform."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN, GLOBAL_STATE_MAP
from custom_components.abb_fimer_pvi_vsn_rest.sensor import (
    DEVICE_CLASS_EXCEPTIONS,
    DEVICE_CLASS_VALID_UNITS,
    VSNSensor,
    _compact_serial_number,
    _format_device_name,
    _get_precision_from_units,
    _simplify_device_type,
    async_setup_entry,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .conftest import TEST_INVERTER_SN, TEST_LOGGER_SN, MockDiscoveredDevice

# Skip reason for tests requiring full integration loading
SKIP_INTEGRATION_LOADING = (
    "Skipped: HA integration loading fails in CI due to editable install path issues"
)


class TestCompactSerialNumber:
    """Tests for _compact_serial_number function."""

    def test_compact_with_dashes(self) -> None:
        """Test compacting serial with dashes."""
        result = _compact_serial_number("077909-3G82-3112")
        assert result == "0779093g823112"

    def test_compact_with_colons(self) -> None:
        """Test compacting MAC address with colons."""
        result = _compact_serial_number("ac:1f:0f:b0:50:b5")
        assert result == "ac1f0fb050b5"

    def test_compact_with_underscores(self) -> None:
        """Test compacting serial with underscores."""
        result = _compact_serial_number("abc_123_def")
        assert result == "abc123def"

    def test_compact_mixed_separators(self) -> None:
        """Test compacting with mixed separators."""
        result = _compact_serial_number("a-b:c_d")
        assert result == "abcd"

    def test_compact_lowercase(self) -> None:
        """Test result is lowercase."""
        result = _compact_serial_number("ABC-DEF")
        assert result == "abcdef"


class TestSimplifyDeviceType:
    """Tests for _simplify_device_type function."""

    def test_inverter_3phases(self) -> None:
        """Test inverter_3phases simplifies to inverter."""
        result = _simplify_device_type("inverter_3phases")
        assert result == "inverter"

    def test_inverter_1phase(self) -> None:
        """Test inverter_1phase simplifies to inverter."""
        result = _simplify_device_type("inverter_1phase")
        assert result == "inverter"

    def test_meter(self) -> None:
        """Test meter stays as meter."""
        result = _simplify_device_type("meter")
        assert result == "meter"

    def test_battery(self) -> None:
        """Test battery stays as battery."""
        result = _simplify_device_type("battery")
        assert result == "battery"

    def test_other_types_lowercase(self) -> None:
        """Test other types are lowercased."""
        result = _simplify_device_type("DATALOGGER")
        assert result == "datalogger"


class TestGetPrecisionFromUnits:
    """Tests for _get_precision_from_units function."""

    def test_power_units_precision_0(self) -> None:
        """Test power units have precision 0."""
        for unit in ("W", "Wh", "kW", "kWh"):
            result = _get_precision_from_units(unit)
            assert result == 0, f"Expected 0 for {unit}"

    def test_voltage_current_precision_1(self) -> None:
        """Test voltage/current units have precision 1."""
        for unit in ("V", "A", "mA", "%"):
            result = _get_precision_from_units(unit)
            assert result == 1, f"Expected 1 for {unit}"

    def test_frequency_precision_2(self) -> None:
        """Test frequency units have precision 2."""
        result = _get_precision_from_units("Hz")
        assert result == 2

    def test_none_input(self) -> None:
        """Test None input returns None."""
        result = _get_precision_from_units(None)
        assert result is None

    def test_unknown_unit(self) -> None:
        """Test unknown unit returns None."""
        result = _get_precision_from_units("unknown")
        assert result is None


class TestFormatDeviceName:
    """Tests for _format_device_name function."""

    def test_with_model(self) -> None:
        """Test formatting with model."""
        result = _format_device_name(
            manufacturer="Power-One",
            device_type_simple="inverter",
            device_model="PVI-10.0-OUTD",
            device_sn_original="077909-3G82-3112",
        )
        assert result == "Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112)"

    def test_without_model(self) -> None:
        """Test formatting without model."""
        result = _format_device_name(
            manufacturer="ABB",
            device_type_simple="datalogger",
            device_model=None,
            device_sn_original="111033-3N16-1421",
        )
        assert result == "ABB Datalogger 111033-3N16-1421"

    def test_with_custom_prefix(self) -> None:
        """Test custom prefix overrides default name."""
        result = _format_device_name(
            manufacturer="Power-One",
            device_type_simple="inverter",
            device_model="PVI-10.0-OUTD",
            device_sn_original="077909-3G82-3112",
            custom_prefix="My Solar Inverter",
        )
        assert result == "My Solar Inverter"

    def test_device_type_title_case(self) -> None:
        """Test device type is title cased."""
        result = _format_device_name(
            manufacturer="ABB",
            device_type_simple="battery",
            device_model="REACT2",
            device_sn_original="123456",
        )
        assert "Battery" in result


class TestDeviceClassValidUnits:
    """Tests for DEVICE_CLASS_VALID_UNITS constant."""

    def test_power_units(self) -> None:
        """Test power device class has valid units."""
        assert "W" in DEVICE_CLASS_VALID_UNITS["power"]
        assert "kW" in DEVICE_CLASS_VALID_UNITS["power"]

    def test_energy_units(self) -> None:
        """Test energy device class has valid units."""
        assert "Wh" in DEVICE_CLASS_VALID_UNITS["energy"]
        assert "kWh" in DEVICE_CLASS_VALID_UNITS["energy"]

    def test_temperature_units(self) -> None:
        """Test temperature device class has valid units."""
        assert "°C" in DEVICE_CLASS_VALID_UNITS["temperature"]
        assert "°F" in DEVICE_CLASS_VALID_UNITS["temperature"]


class TestDeviceClassExceptions:
    """Tests for DEVICE_CLASS_EXCEPTIONS constant."""

    def test_mohm_exception(self) -> None:
        """Test MOhm is an exception."""
        assert "MOhm" in DEVICE_CLASS_EXCEPTIONS
        assert "MΩ" in DEVICE_CLASS_EXCEPTIONS

    def test_kvah_exception(self) -> None:
        """Test kVAh is an exception."""
        assert "kVAh" in DEVICE_CLASS_EXCEPTIONS


@pytest.fixture
def mock_add_entities() -> MagicMock:
    """Mock async_add_entities callback."""
    return MagicMock()


@pytest.fixture
def sample_point_data() -> dict:
    """Return sample point data for a sensor.

    Keys must match what sensor.py expects:
    - device_class (not ha_device_class)
    - state_class (not ha_state_class)
    - units (not ha_unit_of_measurement)
    """
    return {
        "value": 5000,
        "ha_display_name": "Power AC",
        "units": "W",
        "device_class": "power",
        "state_class": "measurement",
        "label": "AC Power",
        "description": "AC Power output",
        "vsn300_name": "m103_1_W",
        "vsn700_name": "Pgrid",
        "category": "Inverter",
        "model": "M103",
        "sunspec_name": "W",
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


class TestVSNSensorInit:
    """Tests for VSNSensor initialization."""

    def test_sensor_attributes(
        self,
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

        assert sensor.has_entity_name is True
        assert sensor._attr_translation_key == "watts"
        assert sensor.native_unit_of_measurement == "W"
        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert "watts" in sensor.unique_id
        assert DOMAIN in sensor.unique_id

    def test_sensor_string_value_no_device_class(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test string sensors have no device class."""
        point_data = {
            "value": "1.9.2",
            "ha_display_name": "Firmware Version",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="firmware_version",
            point_data=point_data,
        )

        assert sensor._attr_device_class is None
        assert sensor._attr_state_class is None
        assert sensor._attr_native_unit_of_measurement is None

    def test_sensor_diagnostic_category(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test diagnostic sensors have correct entity category."""
        point_data = {
            "value": "1.9.2",
            "ha_display_name": "Firmware Version",
            "entity_category": "diagnostic",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="firmware_version",
            point_data=point_data,
        )

        assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    def test_sensor_custom_icon(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test sensors can have custom icons."""
        point_data = {
            "value": 100,
            "ha_display_name": "Resistance",
            "icon": "mdi:omega",
            "units": "MOhm",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="resistance",
            point_data=point_data,
        )

        assert sensor._attr_icon == "mdi:omega"

    def test_sensor_precision_from_mapping(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test precision from mapping is applied."""
        point_data = {
            "value": 45.123,
            "ha_display_name": "Temperature",
            "units": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "suggested_display_precision": 1,
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="temperature",
            point_data=point_data,
        )

        assert sensor._attr_suggested_display_precision == 1


class TestVSNSensorDeviceInfo:
    """Tests for VSNSensor device_info property."""

    def test_device_info_inverter(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test device info for inverter."""
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
        assert "name" in device_info
        assert "manufacturer" in device_info

    def test_device_info_has_via_device_for_inverter(
        self,
        sample_point_data: dict,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test inverter has via_device linking to datalogger."""
        # Add a datalogger device to discovered_devices
        datalogger = MockDiscoveredDevice(
            device_id=TEST_LOGGER_SN,
            raw_device_id=TEST_LOGGER_SN,
            device_type="datalogger",
            device_model="VSN300",
            manufacturer="ABB",
            firmware_version="1.9.2",
            hardware_version=None,
            is_datalogger=True,
        )
        inverter = MockDiscoveredDevice(
            device_id=TEST_INVERTER_SN,
            raw_device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            device_model="PVI-10.0-OUTD",
            manufacturer="Power-One",
            firmware_version="C008",
            hardware_version=None,
            is_datalogger=False,
        )
        mock_coordinator.discovered_devices = [datalogger, inverter]

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="watts",
            point_data=sample_point_data,
        )

        device_info = sensor.device_info
        assert "via_device" in device_info
        assert device_info["via_device"] == (DOMAIN, TEST_LOGGER_SN)


class TestVSNSensorNativeValue:
    """Tests for VSNSensor native_value property."""

    def test_native_value_from_coordinator(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test native value comes from coordinator data."""
        mock_coordinator.data = mock_normalized_data

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.native_value == 5000

    def test_native_value_none_when_no_data(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test native value is None when no coordinator data."""
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

    def test_native_value_none_when_device_not_found(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test native value is None when device not in data."""
        mock_coordinator.data = {"devices": {"other_device": {}}}

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.native_value is None

    def test_native_value_state_translation(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test state codes are translated to text."""
        # Use "GlobalSt" which matches STATE_ENTITY_MAPPINGS key in const.py
        point_data = {
            "value": 6,  # "Run" in GLOBAL_STATE_MAP
            "ha_display_name": "Global State",
            "sunspec_name": "GlobalSt",  # Must match STATE_ENTITY_MAPPINGS key
        }

        mock_coordinator.data = {
            "devices": {
                TEST_INVERTER_SN: {
                    "points": {
                        "global_st": {
                            "value": 6,
                            "sunspec_name": "GlobalSt",
                        }
                    }
                }
            }
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="global_st",
            point_data=point_data,
        )

        # Value should be translated to text
        assert sensor.native_value == GLOBAL_STATE_MAP.get(6, "Unknown (6)")

    def test_native_value_unknown_state_code(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test unknown state codes show with code."""
        # Use "GlobalSt" which matches STATE_ENTITY_MAPPINGS key in const.py
        point_data = {
            "value": 999,  # Unknown code
            "ha_display_name": "Global State",
            "sunspec_name": "GlobalSt",  # Must match STATE_ENTITY_MAPPINGS key
        }

        mock_coordinator.data = {
            "devices": {
                TEST_INVERTER_SN: {
                    "points": {
                        "global_st": {
                            "value": 999,
                            "sunspec_name": "GlobalSt",
                        }
                    }
                }
            }
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="global_st",
            point_data=point_data,
        )

        assert sensor.native_value == "Unknown (999)"

    def test_native_value_system_load_rounded(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test system_load is rounded to 2 decimals."""
        point_data = {
            "value": 0.12345,
            "ha_display_name": "System Load",
        }

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"system_load": {"value": 0.12345}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="system_load",
            point_data=point_data,
        )

        assert sensor.native_value == 0.12

    def test_native_value_cycle_counters_integer(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test cycle counters are integers."""
        for point_name in ("chc", "dhc", "cycle_num"):
            point_data = {"value": 123.7, "ha_display_name": "Cycles"}

            mock_coordinator.data = {
                "devices": {TEST_INVERTER_SN: {"points": {point_name: {"value": 123.7}}}}
            }

            sensor = VSNSensor(
                coordinator=mock_coordinator,
                config_entry=mock_sensor_config_entry,
                device_id=sample_device.device_id,
                device_type=sample_device.device_type,
                point_name=point_name,
                point_data=point_data,
            )

            assert sensor.native_value == 123


class TestVSNSensorExtraStateAttributes:
    """Tests for VSNSensor extra_state_attributes property."""

    def test_extra_state_attributes(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test extra state attributes are populated."""
        mock_coordinator.data = mock_normalized_data

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        attrs = sensor.extra_state_attributes
        assert attrs["device_id"] == TEST_INVERTER_SN
        assert attrs["device_type"] == "inverter_3phases"
        assert attrs["point_name"] == "watts"

    def test_extra_state_attributes_empty_when_no_data(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test empty attributes when no coordinator data."""
        mock_coordinator.data = None

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.extra_state_attributes == {}


class TestVSNSensorAvailable:
    """Tests for VSNSensor available property."""

    def test_available_when_data_present(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test sensor is available when data present."""
        mock_coordinator.data = mock_normalized_data
        mock_coordinator.last_update_success = True

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.available is True

    def test_unavailable_when_update_failed(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
        mock_normalized_data: dict,
    ) -> None:
        """Test sensor is unavailable when last update failed."""
        mock_coordinator.data = mock_normalized_data
        mock_coordinator.last_update_success = False

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.available is False

    def test_unavailable_when_device_not_in_data(
        self,
        sample_point_data: dict,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test sensor is unavailable when device not in data."""
        mock_coordinator.data = {"devices": {}}
        mock_coordinator.last_update_success = True

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="watts",
            point_data=sample_point_data,
        )

        assert sensor.available is False


class TestVSNSensorUptimeFormatting:
    """Tests for uptime formatting."""

    def test_format_uptime_minutes(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test uptime formatting for minutes."""
        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="system_uptime",
            point_data={"value": 300},
        )

        result = sensor._format_uptime_seconds(300)
        assert "5 minutes" in result

    def test_format_uptime_hours(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test uptime formatting for hours."""
        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="system_uptime",
            point_data={"value": 7200},
        )

        result = sensor._format_uptime_seconds(7200)
        assert "2 hours" in result

    def test_format_uptime_days(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test uptime formatting for days."""
        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="system_uptime",
            point_data={"value": 86400},
        )

        result = sensor._format_uptime_seconds(86400)
        assert "1 day" in result

    def test_format_uptime_invalid(
        self,
        sample_device: MockDiscoveredDevice,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test uptime formatting for invalid input."""
        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=sample_device.device_id,
            device_type=sample_device.device_type,
            point_name="system_uptime",
            point_data={"value": 0},
        )

        result = sensor._format_uptime_seconds(-100)
        assert result == "-100"


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

    @dataclass
    class RuntimeData:
        coordinator: object

    mock_coordinator.data = mock_normalized_data
    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) > 0
    assert all(isinstance(e, VSNSensor) for e in entities)


class TestVSNSensorSysTime:
    """Tests for sys_time sensor timestamp conversion."""

    def test_sys_time_conversion(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test sys_time value is converted from Aurora epoch."""
        # Aurora timestamp: 788918400 (Jan 1, 2025 00:00:00 in Aurora epoch)
        aurora_timestamp = 788918400
        # Expected Unix timestamp would be: aurora_timestamp + AURORA_EPOCH_OFFSET

        point_data = {
            "value": aurora_timestamp,
            "ha_display_name": "System Time",
        }

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"sys_time": {"value": aurora_timestamp}}}}
        }

        # Create mock hass with config.time_zone
        mock_hass = MagicMock()
        mock_hass.config.time_zone = "UTC"

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="sys_time",
            point_data=point_data,
        )

        # Patch the hass property on the sensor instance
        with patch.object(type(sensor), "hass", new_callable=PropertyMock, return_value=mock_hass):
            # The result should be a formatted datetime string
            result = sensor.native_value
            assert result is not None
            assert isinstance(result, str)
            # Should contain date format
            assert "-" in result

    def test_sys_time_invalid_value(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test sys_time handles invalid timestamp gracefully."""
        point_data = {
            "value": -1,  # Invalid timestamp
            "ha_display_name": "System Time",
        }

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"sys_time": {"value": -1}}}}
        }

        mock_coordinator.hass.config.time_zone = "UTC"

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="sys_time",
            point_data=point_data,
        )

        # Should return the raw value for invalid timestamps
        result = sensor.native_value
        # Negative values should just pass through as-is
        assert result == -1


class TestVSNSensorStateFlags:
    """Tests for state flag sensors that should be integers."""

    def test_battery_mode_integer(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test battery_mode is converted to integer."""
        point_data = {"value": 2.5, "ha_display_name": "Battery Mode"}

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"battery_mode": {"value": 2.5}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="battery_mode",
            point_data=point_data,
        )

        assert sensor.native_value == 2

    def test_batt_num_integer(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test batt_num is converted to integer."""
        point_data = {"value": 4.0, "ha_display_name": "Battery Count"}

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"batt_num": {"value": 4.0}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="batt_num",
            point_data=point_data,
        )

        assert sensor.native_value == 4

    def test_num_of_mppt_integer(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test num_of_mppt is converted to integer."""
        point_data = {"value": 2.0, "ha_display_name": "MPPT Count"}

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"num_of_mppt": {"value": 2.0}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="num_of_mppt",
            point_data=point_data,
        )

        assert sensor.native_value == 2

    def test_country_std_integer(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test country_std is converted to integer."""
        point_data = {"value": 50.0, "ha_display_name": "Country Standard"}

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"country_std": {"value": 50.0}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="country_std",
            point_data=point_data,
        )

        assert sensor.native_value == 50


class TestVSNSensorExtraAttributes:
    """Additional tests for extra_state_attributes."""

    def test_extra_attributes_uptime_formatted(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test system_uptime has formatted attribute."""
        point_data = {"value": 86400, "ha_display_name": "System Uptime"}

        mock_coordinator.data = {
            "devices": {TEST_INVERTER_SN: {"points": {"system_uptime": {"value": 86400}}}}
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="system_uptime",
            point_data=point_data,
        )

        attrs = sensor.extra_state_attributes
        assert "formatted" in attrs
        assert "1 day" in attrs["formatted"]

    def test_extra_attributes_state_mapping_raw_code(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test state mapping sensors have raw_state_code attribute."""
        point_data = {
            "value": 6,
            "ha_display_name": "Global State",
            "sunspec_name": "GlobalSt",
        }

        mock_coordinator.data = {
            "devices": {
                TEST_INVERTER_SN: {
                    "points": {"global_st": {"value": 6, "sunspec_name": "GlobalSt"}}
                }
            }
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="global_st",
            point_data=point_data,
        )

        attrs = sensor.extra_state_attributes
        assert "raw_state_code" in attrs
        assert attrs["raw_state_code"] == 6


class TestVSNSensorDeviceInfoConfiguration:
    """Tests for device_info configuration URL."""

    def test_datalogger_has_configuration_url(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test datalogger device has configuration URL."""
        # Setup datalogger device in discovered_devices
        datalogger = MockDiscoveredDevice(
            device_id=TEST_LOGGER_SN,
            raw_device_id=TEST_LOGGER_SN,
            device_type="datalogger",
            device_model="VSN300",
            manufacturer="ABB",
            firmware_version="1.9.2",
            hardware_version=None,
            is_datalogger=True,
        )
        mock_coordinator.discovered_devices = [datalogger]
        mock_coordinator.discovery_result.hostname = "abb-vsn300.local"

        point_data = {"value": "1.9.2", "ha_display_name": "Firmware"}

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_LOGGER_SN,
            device_type="datalogger",
            point_name="firmware",
            point_data=point_data,
        )

        device_info = sensor.device_info
        assert "configuration_url" in device_info
        assert device_info["configuration_url"] == "http://abb-vsn300.local"


class TestVSNSensorPrecision:
    """Tests for sensor display precision."""

    def test_precision_invalid_value_fallback(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test invalid precision value falls back to unit-based default."""
        point_data = {
            "value": 45.123,
            "ha_display_name": "Voltage",
            "units": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "suggested_display_precision": "invalid",  # Invalid
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="voltage",
            point_data=point_data,
        )

        # Should fall back to unit-based precision (1 for V)
        assert sensor._attr_suggested_display_precision == 1

    def test_precision_negative_value_fallback(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test negative precision value falls back to unit-based default."""
        point_data = {
            "value": 45.123,
            "ha_display_name": "Voltage",
            "units": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "suggested_display_precision": -1,  # Negative
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="voltage",
            point_data=point_data,
        )

        # Should fall back to unit-based precision (1 for V)
        assert sensor._attr_suggested_display_precision == 1


class TestVSNSensorUnitValidation:
    """Tests for unit validation against device class."""

    def test_invalid_unit_for_device_class(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test invalid unit is corrected for device class."""
        point_data = {
            "value": 1000,
            "ha_display_name": "Power",
            "units": "invalid_unit",  # Invalid unit for power
            "device_class": "power",
            "state_class": "measurement",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="power_test",
            point_data=point_data,
        )

        # Should be corrected to first valid unit (mW)
        assert sensor.native_unit_of_measurement == "mW"

    def test_exception_unit_removes_device_class(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test exception units remove device class."""
        point_data = {
            "value": 100,
            "ha_display_name": "Insulation Resistance",
            "units": "MOhm",
            "device_class": "current",  # Wrong, should be removed
            "state_class": "measurement",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="resistance",
            point_data=point_data,
        )

        # Device class should be None because MOhm is an exception
        # Use getattr since _attr_device_class may not be set when no valid device class
        assert getattr(sensor, "_attr_device_class", None) is None


class TestVSNSensorCustomPrefix:
    """Tests for custom device name prefix functionality."""

    def test_sensor_with_custom_prefix(
        self,
        mock_coordinator: MagicMock,
        mock_sensor_config_entry: MagicMock,
    ) -> None:
        """Test sensor with custom prefix option."""
        # Set custom prefix in options
        mock_sensor_config_entry.options = {"prefix_inverter": "My Solar Inverter"}

        point_data = {
            "value": 5000,
            "ha_display_name": "Power AC",
            "units": "W",
            "device_class": "power",
            "state_class": "measurement",
        }

        sensor = VSNSensor(
            coordinator=mock_coordinator,
            config_entry=mock_sensor_config_entry,
            device_id=TEST_INVERTER_SN,
            device_type="inverter_3phases",
            point_name="watts",
            point_data=point_data,
        )

        device_info = sensor.device_info
        assert device_info["name"] == "My Solar Inverter"


class TestGetPrecisionFromUnitsAdditional:
    """Additional tests for _get_precision_from_units function."""

    def test_kvah_precision_0(self) -> None:
        """Test kVAh has precision 0."""
        result = _get_precision_from_units("kVAh")
        assert result == 0

    def test_var_precision_0(self) -> None:
        """Test var has precision 0."""
        result = _get_precision_from_units("var")
        assert result == 0

    def test_vah_precision_0(self) -> None:
        """Test VAh has precision 0."""
        result = _get_precision_from_units("VAh")
        assert result == 0

    def test_ah_precision_1(self) -> None:
        """Test Ah has precision 1."""
        result = _get_precision_from_units("Ah")
        assert result == 1

    def test_mohm_precision_2(self) -> None:
        """Test MOhm has precision 2."""
        result = _get_precision_from_units("MOhm")
        assert result == 2

    def test_mohm_unicode_precision_2(self) -> None:
        """Test MΩ (unicode) has precision 2."""
        result = _get_precision_from_units("MΩ")
        assert result == 2

    def test_kohm_precision_2(self) -> None:
        """Test kΩ has precision 2."""
        result = _get_precision_from_units("kΩ")
        assert result == 2

    def test_ohm_precision_0(self) -> None:
        """Test Ohm has precision 0."""
        result = _get_precision_from_units("Ohm")
        assert result == 0

    def test_ohm_symbol_precision_0(self) -> None:
        """Test Ω has precision 0."""
        result = _get_precision_from_units("Ω")
        assert result == 0

    def test_mb_precision_1(self) -> None:
        """Test MB has precision 1."""
        result = _get_precision_from_units("MB")
        assert result == 1

    def test_gb_precision_1(self) -> None:
        """Test GB has precision 1."""
        result = _get_precision_from_units("GB")
        assert result == 1

    def test_cycles_precision_0(self) -> None:
        """Test cycles has precision 0."""
        result = _get_precision_from_units("cycles")
        assert result == 0

    def test_channels_precision_0(self) -> None:
        """Test channels has precision 0."""
        result = _get_precision_from_units("channels")
        assert result == 0

    def test_b_precision_0(self) -> None:
        """Test B (bytes) has precision 0."""
        result = _get_precision_from_units("B")
        assert result == 0

    def test_s_precision_0(self) -> None:
        """Test s (seconds) has precision 0."""
        result = _get_precision_from_units("s")
        assert result == 0

    def test_fahrenheit_precision_1(self) -> None:
        """Test °F has precision 1."""
        result = _get_precision_from_units("°F")
        assert result == 1
