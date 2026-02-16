"""ABB FIMER PVI VSN REST Integration.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import json
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify

from .abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from .abb_fimer_vsn_rest_client.discovery import discover_vsn_device
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_ENABLE_STARTUP_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_PREFIX_BATTERY,
    CONF_PREFIX_DATALOGGER,
    CONF_PREFIX_INVERTER,
    CONF_PREFIX_METER,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_ENABLE_STARTUP_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    STARTUP_MESSAGE,
)
from .coordinator import ABBFimerPVIVSNRestCoordinator
from .helpers import compact_serial_number, format_device_name
from .repairs import create_connection_issue, delete_connection_issue

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
STARTUP_LOGGED_KEY = f"{DOMAIN}_startup_logged"
STARTUP_FAILURES_KEY = f"{DOMAIN}_startup_failures"  # Track startup failures per entry

type ABBFimerPVIVSNRestConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Runtime data for the integration."""

    coordinator: ABBFimerPVIVSNRestCoordinator


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Set up ABB FIMER PVI VSN REST from a config entry."""
    # Log startup message only once per HA session
    if not hass.data.get(STARTUP_LOGGED_KEY):
        _LOGGER.info(STARTUP_MESSAGE)
        hass.data[STARTUP_LOGGED_KEY] = True

    # Initialize startup failures tracking dict
    if STARTUP_FAILURES_KEY not in hass.data:
        hass.data[STARTUP_FAILURES_KEY] = {}

    # Migrate options for existing entries (add defaults for new options)
    await _async_migrate_options(hass, config_entry)

    # Get configuration
    host: str = config_entry.data[CONF_HOST]
    username: str = config_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password: str = config_entry.data.get(CONF_PASSWORD, "")
    scan_interval: int = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    vsn_model: str | None = config_entry.data.get(CONF_VSN_MODEL)

    # Build base URL
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    _LOGGER.debug(
        "Setting up integration: host=%s, username=%s, scan_interval=%d, vsn_model=%s",
        host,
        username,
        scan_interval,
        vsn_model or "auto-detect",
    )

    # Get aiohttp session
    session = async_get_clientsession(hass)

    # Get startup notification settings
    enable_startup_notification = config_entry.options.get(
        CONF_ENABLE_STARTUP_NOTIFICATION, DEFAULT_ENABLE_STARTUP_NOTIFICATION
    )
    failures_threshold = config_entry.options.get(
        CONF_FAILURES_THRESHOLD, DEFAULT_FAILURES_THRESHOLD
    )

    # Perform discovery to get complete device information
    try:
        _LOGGER.debug("Performing device discovery during setup")
        discovery_result = await discover_vsn_device(
            session=session,
            base_url=base_url,
            username=username,
            password=password,
            timeout=10,
        )
        _LOGGER.info(
            "Discovery complete: %s with %d devices",
            discovery_result.vsn_model,
            len(discovery_result.devices),
        )

        # Log discovered devices
        for device in discovery_result.devices:
            _LOGGER.debug(
                "Discovered: %s (%s) - Model: %s",
                device.device_id,
                device.device_type,
                device.device_model or "Unknown",
            )

        # Clear startup failure tracking on success
        _clear_startup_failure(hass, config_entry.entry_id)

    except Exception as err:
        # Track startup failures and create notification if threshold reached
        _handle_startup_failure(
            hass,
            config_entry,
            host,
            failures_threshold,
            enable_startup_notification,
            err,
        )
        raise ConfigEntryNotReady(f"Discovery failed: {err}") from err

    # Initialize REST client with discovered VSN model and devices
    client = ABBFimerVSNRestClient(
        session=session,
        base_url=base_url,
        username=username,
        password=password,
        vsn_model=discovery_result.vsn_model,
        timeout=10,
        discovered_devices=discovery_result.devices,
        requires_auth=discovery_result.requires_auth,
    )

    # Initialize coordinator with discovery result and config entry
    coordinator = ABBFimerPVIVSNRestCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=scan_interval),
        discovery_result=discovery_result,
        entry_id=config_entry.entry_id,
        host=host,
        config_entry=config_entry,
    )

    # Perform initial data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        # HA handles logging for ConfigEntryNotReady automatically
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    # Store runtime data
    config_entry.runtime_data = RuntimeData(coordinator=coordinator)

    # Auto-migrate entity IDs affected by buggy regeneration (v1.3.4)
    _async_migrate_entity_ids(hass, config_entry)

    # Note: No manual update listener needed - OptionsFlowWithReload handles reload automatically

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Register device and store device_id in coordinator for device triggers
    async_update_device_registry(hass, config_entry)

    _LOGGER.info(
        "Successfully set up %s integration for %s",
        DOMAIN,
        coordinator.vsn_model or "VSN device",
    )

    return True


@callback
def async_update_device_registry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> None:
    """Register the main device and store device_id in coordinator for triggers."""
    coordinator = config_entry.runtime_data.coordinator
    device_registry = dr.async_get(hass)

    # The logger (datalogger) is the main device
    logger_sn = coordinator.discovery_result.logger_sn if coordinator.discovery_result else None

    if not logger_sn:
        _LOGGER.warning("No logger serial number found, skipping device registration")
        return

    # Find the datalogger DiscoveredDevice for correct manufacturer and model
    datalogger_device = None
    for device in coordinator.discovered_devices:
        if device.is_datalogger:
            datalogger_device = device
            break

    # Extract metadata from discovered device (with fallbacks)
    manufacturer = (
        datalogger_device.manufacturer
        if datalogger_device and datalogger_device.manufacturer
        else "ABB/FIMER"
    )
    device_model = (
        datalogger_device.device_model
        if datalogger_device and datalogger_device.device_model
        else coordinator.vsn_model or "VSN Datalogger"
    )

    # Get custom prefix from options (same logic as sensor.py)
    custom_prefix = config_entry.options.get(CONF_PREFIX_DATALOGGER, "").strip() or None

    # Build friendly device name using shared helper
    device_name = format_device_name(
        manufacturer=manufacturer,
        device_type_simple="datalogger",
        device_model=device_model,
        device_sn_original=logger_sn,
        custom_prefix=custom_prefix,
    )

    # Register the main device (datalogger)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, logger_sn)},
        manufacturer=manufacturer,
        model=device_model,
        name=device_name,
        serial_number=logger_sn,
        sw_version=coordinator.discovery_result.firmware_version
        if coordinator.discovery_result
        else None,
        configuration_url=f"http://{config_entry.data.get(CONF_HOST)}",
    )

    # Store device_id in coordinator for device triggers
    device = device_registry.async_get_device(identifiers={(DOMAIN, logger_sn)})
    if device:
        coordinator.device_id = device.id
        _LOGGER.debug("Device ID stored in coordinator: %s", device.id)


async def async_unload_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry")

    # Unload platforms - only cleanup if successful
    # ref.: https://developers.home-assistant.io/blog/2025/02/19/new-config-entry-states/
    if unload_ok := await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        # Shutdown coordinator and cleanup
        coordinator = config_entry.runtime_data.coordinator
        await coordinator.async_shutdown()
        _LOGGER.info("Successfully unloaded %s integration", DOMAIN)
    else:
        _LOGGER.debug("Platform unload failed, skipping cleanup")

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Prevent deletion of device via device registry.

    Users must remove the integration instead.
    """
    if any(identifier[0] == DOMAIN for identifier in device_entry.identifiers):
        _LOGGER.error("Cannot delete device using device delete. Remove the integration instead.")
        return False
    return True


async def _async_migrate_options(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> None:
    """Migrate options for existing config entries.

    Adds default values for new options that didn't exist in older versions.
    """
    options = dict(config_entry.options)
    updated = False

    # Add repair notification options if missing (added in v1.4.0)
    if CONF_ENABLE_REPAIR_NOTIFICATION not in options:
        options[CONF_ENABLE_REPAIR_NOTIFICATION] = DEFAULT_ENABLE_REPAIR_NOTIFICATION
        updated = True

    if CONF_ENABLE_STARTUP_NOTIFICATION not in options:
        options[CONF_ENABLE_STARTUP_NOTIFICATION] = DEFAULT_ENABLE_STARTUP_NOTIFICATION
        updated = True

    if CONF_FAILURES_THRESHOLD not in options:
        options[CONF_FAILURES_THRESHOLD] = DEFAULT_FAILURES_THRESHOLD
        updated = True

    if CONF_RECOVERY_SCRIPT not in options:
        options[CONF_RECOVERY_SCRIPT] = DEFAULT_RECOVERY_SCRIPT
        updated = True

    if updated:
        hass.config_entries.async_update_entry(config_entry, options=options)
        _LOGGER.debug("Migrated options with new repair notification defaults")


@callback
def _async_migrate_entity_ids(
    hass: HomeAssistant,
    config_entry: ABBFimerPVIVSNRestConfigEntry,
) -> None:
    """Auto-migrate entity IDs from point_name suffixes to translated name suffixes.

    Fixes entities affected by the buggy _regenerate_entity_ids() (pre-v1.3.5) that used
    raw point_names (e.g., 'watts') instead of translated names ('power_ac').

    This function is idempotent: after the first successful migration, no entities match
    the buggy pattern criteria, so subsequent loads do a fast no-op loop.
    """
    coordinator = config_entry.runtime_data.coordinator
    registry = er.async_get(hass)

    # Load English translations (HA always uses English for entity_ids)
    translations_path = Path(__file__).parent / "translations" / "en.json"
    translations_data = json.loads(translations_path.read_text(encoding="utf-8"))
    sensor_translations = translations_data.get("entity", {}).get("sensor", {})

    # Build device lookup by compact serial
    device_lookup: dict[str, object] = {}
    for device in coordinator.discovered_devices:
        device_lookup[compact_serial_number(device.device_id)] = device

    # Prefix map from options
    prefix_map = {
        "inverter": config_entry.options.get(CONF_PREFIX_INVERTER, ""),
        "datalogger": config_entry.options.get(CONF_PREFIX_DATALOGGER, ""),
        "meter": config_entry.options.get(CONF_PREFIX_METER, ""),
        "battery": config_entry.options.get(CONF_PREFIX_BATTERY, ""),
    }

    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)
    migrated = 0

    for entity_entry in entities:
        unique_id_parts = entity_entry.unique_id.split("_")
        if len(unique_id_parts) < 8:
            continue

        device_type = unique_id_parts[5]
        device_sn_compact = unique_id_parts[6]
        point_name = "_".join(unique_id_parts[7:])

        # Get translated name
        translation = sensor_translations.get(point_name, {})
        translated_name = translation.get("name", "")
        if not translated_name:
            continue  # No translation → can't determine if migration needed

        slugified_translation = slugify(translated_name)
        if slugified_translation == point_name:
            continue  # Translation matches point_name → no migration needed

        # Check if entity_id uses point_name suffix (buggy pattern)
        if not entity_entry.entity_id.endswith(f"_{point_name}"):
            continue  # Already uses translated name or was manually customized

        # Compute correct entity_id
        discovered = device_lookup.get(device_sn_compact)
        if not discovered:
            continue

        custom_prefix = prefix_map.get(device_type, "").strip() or None
        device_name = format_device_name(
            manufacturer=discovered.manufacturer or "ABB/FIMER",
            device_type_simple=device_type,
            device_model=discovered.device_model,
            device_sn_original=discovered.device_id,
            custom_prefix=custom_prefix,
        )

        domain = entity_entry.entity_id.split(".")[0]
        new_entity_id = f"{domain}.{slugify(device_name)}_{slugified_translation}"

        if entity_entry.entity_id != new_entity_id and not registry.async_get(new_entity_id):
            registry.async_update_entity(entity_entry.entity_id, new_entity_id=new_entity_id)
            migrated += 1
            _LOGGER.info("Migrated entity ID: %s → %s", entity_entry.entity_id, new_entity_id)

    if migrated > 0:
        _LOGGER.info("Migrated %d entity IDs from point_name to translated name format", migrated)


def _handle_startup_failure(
    hass: HomeAssistant,
    config_entry: ABBFimerPVIVSNRestConfigEntry,
    host: str,
    failures_threshold: int,
    enable_startup_notification: bool,
    error: Exception,
) -> None:
    """Handle a startup failure and create notification if threshold reached.

    Args:
        hass: HomeAssistant instance
        config_entry: Config entry
        host: Device host
        failures_threshold: Number of failures before notification
        enable_startup_notification: Whether startup notifications are enabled
        error: The exception that occurred

    """
    entry_id = config_entry.entry_id
    failures_data = hass.data[STARTUP_FAILURES_KEY]

    # Initialize or increment failure count
    if entry_id not in failures_data:
        failures_data[entry_id] = {"count": 0, "notification_created": False}

    failures_data[entry_id]["count"] += 1
    failure_count = failures_data[entry_id]["count"]

    _LOGGER.debug(
        "Startup failure %d/%d for %s: %s",
        failure_count,
        failures_threshold,
        host,
        error,
    )

    # Create notification if threshold reached and not already created
    if (
        failure_count >= failures_threshold
        and not failures_data[entry_id]["notification_created"]
        and enable_startup_notification
    ):
        device_name = config_entry.title or f"VSN Device ({host})"
        create_connection_issue(hass, entry_id, device_name, host)
        failures_data[entry_id]["notification_created"] = True
        _LOGGER.info(
            "Startup notification created after %d consecutive failures for %s",
            failure_count,
            host,
        )


def _clear_startup_failure(hass: HomeAssistant, entry_id: str) -> None:
    """Clear startup failure tracking for an entry.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    failures_data = hass.data.get(STARTUP_FAILURES_KEY, {})

    if entry_id in failures_data:
        # If notification was created, delete it
        if failures_data[entry_id].get("notification_created"):
            delete_connection_issue(hass, entry_id)
            _LOGGER.info("Startup notification cleared - device is now online")

        # Reset tracking
        del failures_data[entry_id]
