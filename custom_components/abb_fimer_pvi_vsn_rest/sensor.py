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

        # Set unique ID: domain_deviceid_pointname
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{point_name}"

        # Set entity name from HA Display Name (what users see in HA)
        # Fallback to description, then label, then point name
        self._attr_name = point_data.get(
            "ha_display_name",
            point_data.get("description", point_data.get("label", point_name))
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
                if units in ("W", "Wh", "kW", "kWh"):
                    self._attr_suggested_display_precision = 0
                elif units in ("V", "A"):
                    self._attr_suggested_display_precision = 1
                elif units in ("Hz", "°C", "°F"):
                    self._attr_suggested_display_precision = 2
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
