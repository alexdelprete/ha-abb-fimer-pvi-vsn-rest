"""Tests for data models."""

from __future__ import annotations

from typing import Any

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.models import VSNDevice


class TestVSNDevice:
    """Tests for VSNDevice dataclass."""

    def test_create_device_with_all_fields(self) -> None:
        """Test creating a VSNDevice with all fields."""
        points: dict[str, Any] = {
            "watts": {"value": 5000, "unit": "W"},
            "wh": {"value": 123456, "unit": "Wh"},
        }
        device = VSNDevice(
            device_id="077909-3G82-3112",
            device_type="inverter_3phases",
            serial_number="077909-3G82-3112",
            manufacturer="Power-One",
            model="PVI-10.0-OUTD",
            points=points,
        )

        assert device.device_id == "077909-3G82-3112"
        assert device.device_type == "inverter_3phases"
        assert device.serial_number == "077909-3G82-3112"
        assert device.manufacturer == "Power-One"
        assert device.model == "PVI-10.0-OUTD"
        assert device.points == points

    def test_create_device_with_empty_points(self) -> None:
        """Test creating a VSNDevice with empty points."""
        device = VSNDevice(
            device_id="test-device",
            device_type="datalogger",
            serial_number="123456",
            manufacturer="ABB",
            model="VSN300",
            points={},
        )

        assert device.device_id == "test-device"
        assert device.points == {}

    def test_device_equality(self) -> None:
        """Test VSNDevice equality."""
        points: dict[str, Any] = {"watts": {"value": 5000}}
        device1 = VSNDevice(
            device_id="test",
            device_type="inverter",
            serial_number="123",
            manufacturer="ABB",
            model="Test",
            points=points,
        )
        device2 = VSNDevice(
            device_id="test",
            device_type="inverter",
            serial_number="123",
            manufacturer="ABB",
            model="Test",
            points=points,
        )

        assert device1 == device2

    def test_device_inequality(self) -> None:
        """Test VSNDevice inequality."""
        device1 = VSNDevice(
            device_id="test1",
            device_type="inverter",
            serial_number="123",
            manufacturer="ABB",
            model="Test",
            points={},
        )
        device2 = VSNDevice(
            device_id="test2",
            device_type="inverter",
            serial_number="123",
            manufacturer="ABB",
            model="Test",
            points={},
        )

        assert device1 != device2
