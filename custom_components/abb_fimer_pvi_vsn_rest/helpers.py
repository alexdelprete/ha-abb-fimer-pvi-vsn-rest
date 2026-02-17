"""Helper functions."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import TYPE_TO_CONF_PREFIX


def simplify_device_type(device_type: str) -> str:
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


def get_device_type_simple(device: object) -> str:
    """Get simplified device type from a DiscoveredDevice.

    Args:
        device: DiscoveredDevice with is_datalogger and device_type attributes

    Returns:
        Simplified type (e.g., "inverter", "meter", "battery", "datalogger")

    """
    if device.is_datalogger:  # type: ignore[attr-defined]
        return "datalogger"
    return simplify_device_type(device.device_type)  # type: ignore[attr-defined]


def build_prefix_by_device(
    discovered_devices: list,
    options: dict[str, Any],
) -> dict[str, str]:
    """Build mapping of compact_serial → custom_prefix from options.

    Handles both single-device (base key like "prefix_battery") and multi-device
    (indexed keys like "prefix_battery_1", "prefix_battery_2") scenarios.

    Args:
        discovered_devices: List of DiscoveredDevice objects from coordinator
        options: Config entry options dict

    Returns:
        Dict mapping compact serial number to custom prefix string.
        Only includes entries with non-empty prefixes.

    """
    # Group devices by simplified type, sorted by device_id for stable ordering
    devices_by_type: dict[str, list] = {}
    for device in discovered_devices:
        dtype = get_device_type_simple(device)
        devices_by_type.setdefault(dtype, []).append(device)
    for device_list in devices_by_type.values():
        device_list.sort(key=lambda d: d.device_id)

    prefix_by_device: dict[str, str] = {}
    for dtype, devices in devices_by_type.items():
        base_key = TYPE_TO_CONF_PREFIX.get(dtype, "")
        if not base_key:
            continue
        if len(devices) == 1:
            prefix = options.get(base_key, "").strip()
            if prefix:
                prefix_by_device[compact_serial_number(devices[0].device_id)] = prefix
        else:
            for i, device in enumerate(devices, start=1):
                prefix = options.get(f"{base_key}_{i}", "").strip()
                if prefix:
                    prefix_by_device[compact_serial_number(device.device_id)] = prefix

    return prefix_by_device


def compact_serial_number(serial: str) -> str:
    """Compact serial number by removing separators and converting to lowercase.

    Args:
        serial: Serial number with possible separators (e.g., "077909-3G82-3112")

    Returns:
        Compacted lowercase serial (e.g., "0779093g823112")

    """
    return serial.replace("-", "").replace(":", "").replace("_", "").lower()


def format_device_name(
    manufacturer: str,
    device_type_simple: str,
    device_model: str | None,
    device_sn_original: str,
    custom_prefix: str | None = None,
) -> str:
    """Format user-friendly device name, or use custom prefix if provided.

    Args:
        manufacturer: Device manufacturer (e.g., "Power-One", "ABB", "FIMER")
        device_type_simple: Simplified device type (e.g., "inverter", "datalogger")
        device_model: Device model (e.g., "PVI-3.0-TL-OUTD", "VSN300")
        device_sn_original: Original serial number with dashes (e.g., "077909-3G82-3112")
        custom_prefix: Optional custom device name that completely replaces default

    Returns:
        Custom prefix if provided, otherwise formatted device name
        (e.g., "Power-One Inverter PVI-3.0-TL-OUTD (077909-3G82-3112)")

    Examples:
        >>> format_device_name("Power-One", "inverter", "PVI-3.0-TL-OUTD", "077909-3G82-3112")
        'Power-One Inverter PVI-3.0-TL-OUTD (077909-3G82-3112)'
        >>> format_device_name("ABB", "datalogger", "VSN300", "111033-3N16-1421")
        'ABB Datalogger VSN300 (111033-3N16-1421)'
        >>> format_device_name("FIMER", "inverter", None, "077909-3G82-3112")
        'FIMER Inverter 077909-3G82-3112'
        >>> format_device_name("ABB", "inverter", "PVI-10.0", "123", "My Solar Inverter")
        'My Solar Inverter'

    """
    # If custom prefix is set, use it as the complete device name
    if custom_prefix:
        return custom_prefix

    # Use full serial number in uppercase (preserves original dash formatting)
    sn_display = device_sn_original.upper()

    # Capitalize device type for display
    device_type_display = device_type_simple.title()

    # Format: "Manufacturer Type Model (Serial)"
    if device_model:
        return f"{manufacturer} {device_type_display} {device_model} ({sn_display})"

    # Fallback without model: "Manufacturer Type Serial"
    return f"{manufacturer} {device_type_display} {sn_display}"


async def async_get_entity_translations(
    hass: HomeAssistant,
    domain: str,
) -> dict[str, str]:
    """Load entity name translations using HA's built-in translation API.

    Returns a dict mapping translation_key → translated name.
    Example: {"watts": "Power AC", "alarm_st": "Alarm Status"}

    Args:
        hass: Home Assistant instance
        domain: Integration domain (e.g., "abb_fimer_pvi_vsn_rest")

    """
    translations = await async_get_translations(hass, "en", "entity", integrations=[domain])

    # HA returns flat keys like:
    # "component.abb_fimer_pvi_vsn_rest.entity.sensor.watts.name" → "Power AC"
    # Extract into {point_name: translated_name} lookup
    prefix = f"component.{domain}.entity.sensor."
    suffix = ".name"
    result: dict[str, str] = {}
    for key, value in translations.items():
        if key.startswith(prefix) and key.endswith(suffix):
            translation_key = key[len(prefix) : -len(suffix)]
            result[translation_key] = value

    return result


def log_debug(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log debug."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug("%s: %s %s", context, message, extra)


def log_info(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log info."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info("%s: %s %s", context, message, extra)


def log_warning(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log warning."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.warning("%s: %s %s", context, message, extra)


def log_error(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log error."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error("%s: %s %s", context, message, extra)
