"""Helper functions."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations


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
