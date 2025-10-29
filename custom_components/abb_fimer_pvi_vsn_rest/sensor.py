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


def _determine_model_for_entity_id(
    point_model: str, vsn_model: str, is_datalogger: bool
) -> str:
    """Determine which model string to use in entity ID.

    Args:
        point_model: SunSpec model from mapping (e.g., "M103", "ABB Proprietary")
        vsn_model: VSN model from coordinator (e.g., "VSN300", "VSN700")
        is_datalogger: Whether this point belongs to datalogger device

    Returns:
        Lowercase model for entity ID (e.g., "m103", "vsn300", "vsn700")

    """
    # SunSpec models: use as-is in lowercase
    if point_model and point_model.startswith("M") and point_model[1:].replace("M", "").isdigit():
        return point_model.lower()

    # Datalogger system points or VSN-only points: use VSN model
    if is_datalogger or point_model in ("VSN300-only", "VSN700-only", "VSN"):
        return vsn_model.lower()

    # ABB Proprietary points: use vsn700 (they're VSN700-only)
    if point_model == "ABB Proprietary":
        return "vsn700"

    # Fallback: use VSN model
    return vsn_model.lower()


def _build_entity_id(
    device_type_simple: str,
    device_sn_compact: str,
    model: str,
    point_name: str,
) -> str:
    """Build full entity ID from components.

    Template: abb_vsn_rest_(device_type)_(device_sn)_(model)_(pointname)

    Args:
        device_type_simple: Simplified device type ("inverter", "meter", "battery", "datalogger")
        device_sn_compact: Compacted device serial number
        model: Model identifier ("m103", "m160", "vsn300", "vsn700", etc.)
        point_name: Simplified point name from mapping

    Returns:
        Full entity ID (e.g., "abb_vsn_rest_inverter_0779093g823112_m103_watts")

    """
    return f"abb_vsn_rest_{device_type_simple}_{device_sn_compact}_{model}_{point_name}"


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
        self._attr_has_entity_name = False

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

        # Get model from point_data
        point_model = point_data.get("model", "")

        # Determine which model to use in entity ID
        model_for_id = _determine_model_for_entity_id(
            point_model=point_model,
            vsn_model=coordinator.vsn_model,
            is_datalogger=is_datalogger,
        )

        # Build full entity ID using the new template
        # point_name is now the simplified name from mapping (e.g., "watts", "dc_current_1", "uptime")
        entity_id = _build_entity_id(
            device_type_simple=device_type_simple,
            device_sn_compact=device_sn_compact,
            model=model_for_id,
            point_name=point_name,
        )

        # Set unique_id to match entity_id for consistency
        self._attr_unique_id = entity_id

        # Explicitly set entity_id to use our template format
        # This overrides HA's automatic generation from _attr_name
        self.entity_id = f"sensor.{entity_id}"

        # Set entity name from HA Display Name (what users see in HA)
        # Fallback to description, then label, then point name
        self._attr_name = point_data.get(
            "ha_display_name",
            point_data.get("description", point_data.get("label", point_name))
        )

        _LOGGER.debug(
            "Built entity ID: %s (device_type=%s, sn=%s, model=%s, point=%s)",
            entity_id,
            device_type_simple,
            device_sn_compact,
            model_for_id,
            point_name,
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

        attributes = {
            "device_id": self._device_id,
            "device_type": self._device_type,
            "description": point_data.get("description"),
        }

        # Add timestamp if available
        if timestamp := device_data.get("timestamp"):
            attributes["last_updated"] = timestamp

        # Add mapping info for debugging
        if sunspec_name := point_data.get("sunspec_name"):
            attributes["sunspec_name"] = sunspec_name

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

                # Build device name according to user requirements:
                # 1. For inverters: "Model (Serial)" e.g., "PVI-10.0-OUTD (077909-3G82-3112)"
                # 2. For datalogger: "VSN300/VSN700 (Serial/CleanMAC)"
                if is_datalogger:
                    device_name = f"{self.coordinator.vsn_model} ({self._device_id})"
                    # Datalogger gets the configuration URL (VSN web interface)
                    if self.coordinator.discovery_result:
                        # Extract host from stored base_url or use hostname
                        hostname = self.coordinator.discovery_result.hostname
                        if hostname:
                            configuration_url = f"http://{hostname}"
                elif device_model:
                    device_name = f"{device_model} ({self._device_id})"
                else:
                    # Fallback: Use device type with serial
                    device_name = f"{self._device_type} ({self._device_id})"
                break

        # Fallback if not found in discovery
        if device_name is None:
            device_name = f"VSN Device {self._device_id}"

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
