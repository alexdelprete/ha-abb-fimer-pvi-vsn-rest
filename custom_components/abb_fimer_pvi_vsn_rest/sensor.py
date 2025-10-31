"""Sensor platform for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ABBFimerPVIVSNRestCoordinator

_LOGGER = logging.getLogger(__name__)


def _compact_serial_number(serial: str) -> str:
    """Compact serial number by removing separators and converting to lowercase.

    Args:
        serial: Serial number with possible separators (e.g., "077909-3G82-3112")

    Returns:
        Compacted lowercase serial (e.g., "0779093g823112")

    """
    return serial.replace("-", "").replace(":", "").replace("_", "").lower()


def _simplify_device_type(device_type: str) -> str:
    """Simplify device type to basic category.

    Args:
        device_type: Device type from API (e.g., "inverter_3phases", "meter")

    Returns:
        Simplified type (e.g., "inverter", "meter", "battery", "datalogger")

    """
    if device_type.startswith("inverter"):
        return "inverter"
    if device_type == "meter":
        return "meter"
    if device_type == "battery":
        return "battery"
    # Datalogger types vary, but we'll handle this specially
    return device_type.lower()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VSN REST sensor platform."""
    coordinator: ABBFimerPVIVSNRestCoordinator = config_entry.runtime_data.coordinator

    # Wait for first successful data fetch
    if not coordinator.data:
        _LOGGER.warning("No data available from coordinator, skipping sensor setup")
        return

    # Create sensors from normalized data
    # IMPORTANT: Create datalogger sensors first, then inverter sensors
    # This ensures datalogger device exists before inverter devices reference it via via_device
    datalogger_sensors: list[VSNSensor] = []
    other_sensors: list[VSNSensor] = []

    devices = coordinator.data.get("devices", {})
    _LOGGER.debug("Creating sensors for %d devices", len(devices))

    # First pass: identify datalogger device ID
    datalogger_device_id = None
    for discovered_device in coordinator.discovered_devices:
        if discovered_device.is_datalogger:
            datalogger_device_id = discovered_device.device_id
            break

    # Second pass: create sensors, separating datalogger from others
    for device_id, device_data in devices.items():
        device_type = device_data.get("device_type", "unknown")
        points = device_data.get("points", {})

        _LOGGER.debug("Device %s (%s): %d points", device_id, device_type, len(points))

        is_datalogger = device_id == datalogger_device_id

        for point_name, point_data in points.items():
            sensor = VSNSensor(
                coordinator=coordinator,
                device_id=device_id,
                device_type=device_type,
                point_name=point_name,
                point_data=point_data,
            )

            if is_datalogger:
                datalogger_sensors.append(sensor)
            else:
                other_sensors.append(sensor)

    # Add datalogger sensors first, then other sensors
    # This ensures proper device hierarchy registration
    total_sensors = len(datalogger_sensors) + len(other_sensors)
    _LOGGER.info(
        "Adding %d sensors (%d datalogger, %d inverters)",
        total_sensors,
        len(datalogger_sensors),
        len(other_sensors),
    )
    async_add_entities(datalogger_sensors + other_sensors)


class VSNSensor(CoordinatorEntity[ABBFimerPVIVSNRestCoordinator], SensorEntity):
    """Representation of a VSN sensor."""

    def __init__(
        self,
        coordinator: ABBFimerPVIVSNRestCoordinator,
        device_id: str,
        device_type: str,
        point_name: str,
        point_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data coordinator
            device_id: Device serial number
            device_type: Device type (e.g., "inverter_3phases")
            point_name: HA entity name (e.g., "abb_m103_w")
            point_data: Point metadata and initial value

        """
        super().__init__(coordinator)

        self._device_id = device_id
        self._device_type = device_type
        self._point_name = point_name
        self._point_data = point_data  # Store for attributes

        # Enable modern entity naming pattern
        self._attr_has_entity_name = True

        # Determine if this sensor belongs to datalogger device
        is_datalogger = False
        for discovered_device in coordinator.discovered_devices:
            if discovered_device.device_id == device_id and discovered_device.is_datalogger:
                is_datalogger = True
                break

        # Simplify device type for entity ID
        if is_datalogger:
            device_type_simple = "datalogger"
        else:
            device_type_simple = _simplify_device_type(device_type)

        # Compact device serial number (remove dashes/colons/underscores, lowercase)
        device_sn_compact = _compact_serial_number(device_id)

        # Build device identifier (no model - simplified template)
        # This will be used as device name in device_info
        device_identifier = f"abb_vsn_rest_{device_type_simple}_{device_sn_compact}"

        # Build unique_id: device_identifier + point_name (no model)
        unique_id = f"{device_identifier}_{point_name}"
        self._attr_unique_id = unique_id

        # Set entity name to friendly display name (what users see in device cards)
        # With has_entity_name=True, HA will auto-construct:
        #   entity_id = slugify(device_name) + "_" + slugify(entity_name)
        #   friendly_name = device_name + " " + entity_name
        self._attr_name = point_data.get(
            "ha_display_name",
            point_data.get("label", point_name)
        )

        # Store device identifier for device_info
        self._device_identifier = device_identifier

        _LOGGER.debug(
            "Created sensor: %s (device=%s, unique_id=%s)",
            self._attr_name,
            device_identifier,
            unique_id,
        )

        # Check if initial value is numeric - determines sensor type
        # HA strictly requires numeric classification (state_class, units, precision) only for numeric sensors
        initial_value = point_data.get("value")
        is_numeric = isinstance(initial_value, (int, float))

        if is_numeric:
            # Numeric sensor: set device_class, state_class, units, precision as available
            device_class_str = point_data.get("device_class")
            if device_class_str:
                try:
                    self._attr_device_class = SensorDeviceClass(device_class_str)
                except ValueError:
                    _LOGGER.debug(
                        "Unknown device_class '%s' for %s", device_class_str, point_name
                    )

            state_class_str = point_data.get("state_class")
            if state_class_str:
                try:
                    self._attr_state_class = SensorStateClass(state_class_str)
                except ValueError:
                    _LOGGER.debug(
                        "Unknown state_class '%s' for %s", state_class_str, point_name
                    )

            units = point_data.get("units")
            if units:
                self._attr_native_unit_of_measurement = units

                # Set suggested display precision based on units
                if units in ("W", "Wh", "kW", "kWh", "var", "VAR", "VAh", "s", "B"):
                    # Power, energy, reactive power, apparent energy, duration, bytes: no decimals
                    self._attr_suggested_display_precision = 0
                elif units in ("V", "A", "mA", "%", "Ah"):
                    # Voltage, current, percentage, capacity: 1 decimal
                    self._attr_suggested_display_precision = 1
                elif units in ("Hz", "°C", "°F", "MOhm", "MΩ", "kΩ"):
                    # Frequency, temperature, large resistance values: 2 decimals
                    self._attr_suggested_display_precision = 2
                elif units in ("Ω", "Ohm"):
                    # Small resistance values in ohms: no decimals
                    self._attr_suggested_display_precision = 0
        else:
            # String sensor: explicitly set ALL numeric attributes to None
            # This prevents HA from inferring numeric type from any attribute
            self._attr_device_class = None
            self._attr_state_class = None
            self._attr_native_unit_of_measurement = None
            _LOGGER.debug(
                "String sensor %s: device_class=None, state_class=None, unit=None (value: %s)",
                point_name,
                initial_value,
            )

        # Set entity_category if specified (e.g., "diagnostic" for M1/system monitoring)
        entity_category_str = point_data.get("entity_category")
        if entity_category_str == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            _LOGGER.debug("Sensor %s set as diagnostic entity", point_name)

        _LOGGER.debug(
            "Created sensor: %s (device_class=%s, state_class=%s, unit=%s, entity_category=%s)",
            self._attr_name,
            getattr(self, "_attr_device_class", None),
            getattr(self, "_attr_state_class", None),
            getattr(self, "_attr_native_unit_of_measurement", None),
            getattr(self, "_attr_entity_category", None),
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        devices = self.coordinator.data.get("devices", {})
        device_data = devices.get(self._device_id)

        if not device_data:
            _LOGGER.debug("Device %s not found in coordinator data", self._device_id)
            return None

        points = device_data.get("points", {})
        point_data = points.get(self._point_name)

        if not point_data:
            _LOGGER.debug(
                "Point %s not found for device %s", self._point_name, self._device_id
            )
            return None

        return point_data.get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        devices = self.coordinator.data.get("devices", {})
        device_data = devices.get(self._device_id)

        if not device_data:
            return {}

        points = device_data.get("points", {})
        point_data = points.get(self._point_name)

        if not point_data:
            return {}

        # Comprehensive attributes including mapping information
        attributes = {
            # Identity
            "device_id": self._device_id,
            "device_type": self._device_type,
            "point_name": self._point_name,

            # Display Names
            "friendly_name": point_data.get("ha_display_name", ""),
            "label": point_data.get("label", ""),

            # VSN REST API Names
            "vsn300_rest_name": point_data.get("vsn300_name", ""),
            "vsn700_rest_name": point_data.get("vsn700_name", ""),

            # SunSpec Information
            "sunspec_model": point_data.get("model", ""),  # Now contains comma-separated models
            "sunspec_name": point_data.get("sunspec_name", ""),
            "description": point_data.get("description", ""),

            # Compatibility Flags (derived from model string)
            "vsn300_compatible": "VSN300-only" in point_data.get("model", "") or
                               ("VSN700-only" not in point_data.get("model", "") and
                                "ABB Proprietary" not in point_data.get("model", "")),
            "vsn700_compatible": "VSN700-only" in point_data.get("model", "") or
                               ("VSN300-only" not in point_data.get("model", "") and
                                point_data.get("model", "") != ""),

            # Category
            "category": point_data.get("category", ""),
        }

        # Add timestamp if available
        if timestamp := device_data.get("timestamp"):
            attributes["last_updated"] = timestamp

        # Clean up empty strings to None for cleaner display
        attributes = {k: (v if v != "" else None) for k, v in attributes.items()}

        return attributes

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        # Find the discovered device info for this device_id
        device_name = None
        device_model = None
        manufacturer = "ABB/FIMER"  # Default
        firmware_version = None
        hardware_version = None
        is_datalogger = False
        configuration_url = None

        for discovered_device in self.coordinator.discovered_devices:
            if discovered_device.device_id == self._device_id:
                is_datalogger = discovered_device.is_datalogger
                device_model = discovered_device.device_model
                manufacturer = discovered_device.manufacturer or "ABB/FIMER"
                firmware_version = discovered_device.firmware_version
                hardware_version = discovered_device.hardware_version

                # Get configuration URL for datalogger
                if is_datalogger and self.coordinator.discovery_result:
                    # Datalogger gets the configuration URL (VSN web interface)
                    hostname = self.coordinator.discovery_result.hostname
                    if hostname:
                        configuration_url = f"http://{hostname}"
                break

        # Use device identifier as device name for entity_id generation
        # This creates consistent entity IDs following the template:
        #   sensor.abb_vsn_rest_{device_type}_{serial}_{entity_name}
        device_name = self._device_identifier

        # Build device info dictionary with all available fields
        device_info_dict = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_name,
            "manufacturer": manufacturer,
            "model": device_model or self._device_type,
            "serial_number": self._device_id,  # Use device_id (serial number)
        }

        # Add optional fields if available
        if firmware_version:
            device_info_dict["sw_version"] = firmware_version
        if hardware_version:
            device_info_dict["hw_version"] = hardware_version
        if configuration_url:
            device_info_dict["configuration_url"] = configuration_url

        # For non-datalogger devices, set via_device to the datalogger
        if not is_datalogger and self.coordinator.discovery_result:
            # Find the datalogger device ID
            for discovered_device in self.coordinator.discovered_devices:
                if discovered_device.is_datalogger:
                    device_info_dict["via_device"] = (
                        DOMAIN,
                        discovered_device.device_id,
                    )
                    break

        return device_info_dict

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._device_id in self.coordinator.data.get("devices", {})
        )
