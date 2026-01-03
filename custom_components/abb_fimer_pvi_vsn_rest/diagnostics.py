"""Diagnostics support for ABB/FIMER PVI VSN REST.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ABBFimerPVIVSNRestConfigEntry
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VSN_MODEL,
    DOMAIN,
    VERSION,
)

# Keys to redact from diagnostics output
TO_REDACT = {
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    "sn",
    "serial_number",
    "ip",
    "mac",
    "hostname",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator

    # Gather configuration data
    config_data = {
        "entry_id": config_entry.entry_id,
        "version": config_entry.version,
        "domain": DOMAIN,
        "integration_version": VERSION,
        "data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "options": async_redact_data(dict(config_entry.options), TO_REDACT),
    }

    # Gather discovery result info
    discovery_data = {}
    if coordinator.discovery_result:
        discovery = coordinator.discovery_result
        discovery_data = {
            "vsn_model": discovery.vsn_model,
            "logger_sn": "**REDACTED**",
            "logger_model": discovery.logger_model,
            "firmware_version": discovery.firmware_version,
            "hostname": "**REDACTED**",
            "device_count": len(discovery.devices),
            "devices": [
                {
                    "device_id": "**REDACTED**",
                    "device_type": device.device_type,
                    "device_model": device.device_model,
                    "manufacturer": device.manufacturer,
                    "firmware_version": device.firmware_version,
                    "is_datalogger": device.is_datalogger,
                }
                for device in discovery.devices
            ],
        }

    # Gather coordinator state
    coordinator_data = {
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "vsn_model": config_entry.data.get(CONF_VSN_MODEL),
        "scan_interval": config_entry.options.get(
            CONF_SCAN_INTERVAL, config_entry.data.get(CONF_SCAN_INTERVAL)
        ),
    }

    # Gather sensor data summary (counts by device type, no actual values)
    sensor_summary = {}
    if coordinator.data:
        for device_id, device_data in coordinator.data.items():
            if isinstance(device_data, dict):
                sensor_summary[f"device_{device_id[:8]}..."] = {
                    "point_count": len(device_data),
                }

    return {
        "config": config_data,
        "discovery": discovery_data,
        "coordinator": coordinator_data,
        "sensor_summary": sensor_summary,
    }
