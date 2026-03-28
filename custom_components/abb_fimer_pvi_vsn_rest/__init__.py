"""ABB FIMER PVI VSN REST Integration.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

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
    CONF_KNOWN_DEVICES,
    CONF_PREFIX_DATALOGGER,
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
from .helpers import async_get_entity_translations, format_device_name
from .repairs import (
    create_connection_issue,
    create_partial_discovery_issue,
    delete_connection_issue,
    delete_partial_discovery_issue,
)

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

    # --- Known devices management ---
    # Merge discovered devices into the persisted known_devices list (union — only adds)
    known_devices = list(config_entry.data.get(CONF_KNOWN_DEVICES, []))
    known_device_ids = {d["device_id"] for d in known_devices}
    discovered_device_ids = {d.device_id for d in discovery_result.devices}

    known_devices.extend(
        {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "is_datalogger": device.is_datalogger,
        }
        for device in discovery_result.devices
        if device.device_id not in known_device_ids
    )

    # Update config_entry.data if new devices were found
    if len(known_devices) != len(config_entry.data.get(CONF_KNOWN_DEVICES, [])):
        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data, CONF_KNOWN_DEVICES: known_devices}
        )
        _LOGGER.info(
            "Updated known_devices list: %d devices",
            len(known_devices),
        )

    known_device_ids = {d["device_id"] for d in known_devices}

    # Detect missing devices (exclude datalogger — if it's down, discovery fails entirely)
    known_non_datalogger_ids = {d["device_id"] for d in known_devices if not d.get("is_datalogger")}
    missing_device_ids = known_non_datalogger_ids - discovered_device_ids

    # Create or clear partial discovery repair notification
    if missing_device_ids:
        _LOGGER.warning(
            "Partial discovery: %d of %d known devices missing: %s",
            len(missing_device_ids),
            len(known_device_ids),
            ", ".join(sorted(missing_device_ids)),
        )
        device_name = discovery_result.get_title()
        create_partial_discovery_issue(
            hass, config_entry.entry_id, device_name, sorted(missing_device_ids)
        )
    else:
        delete_partial_discovery_issue(hass, config_entry.entry_id)

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

    # Initialize coordinator with discovery result, config entry, and missing devices
    coordinator = ABBFimerPVIVSNRestCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=scan_interval),
        discovery_result=discovery_result,
        entry_id=config_entry.entry_id,
        host=host,
        config_entry=config_entry,
        missing_devices=missing_device_ids,
    )

    # Perform initial data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        # HA handles logging for ConfigEntryNotReady automatically
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    # Store runtime data
    config_entry.runtime_data = RuntimeData(coordinator=coordinator)

    # Note: No manual update listener needed - OptionsFlowWithReload handles reload automatically

    # Register datalogger device FIRST so child devices can reference it via via_device
    async_update_device_registry(hass, config_entry)

    # Forward setup to platforms (datalogger device already exists for via_device references)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

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

    # Find the datalogger DiscoveredDevice for correct identifiers and metadata
    datalogger_device = None
    for device in coordinator.discovered_devices:
        if device.is_datalogger:
            datalogger_device = device
            break

    if not datalogger_device:
        _LOGGER.warning("No datalogger device found, skipping device registration")
        return

    # Use the cleaned device_id from discovery as the device identifier.
    # This MUST match what sensor.py uses for via_device references.
    # For VSN300: serial number (e.g., "111033-3N16-1421") — no change needed.
    # For VSN700: MAC without colons (e.g., "0c1c57fdc62c") — colons stripped in discovery.
    # Previously used discovery_result.logger_sn which kept colons for VSN700 MACs,
    # causing a mismatch with sensor.py's via_device reference.
    device_identifier = datalogger_device.device_id

    # Extract metadata from discovered device (with fallbacks)
    manufacturer = datalogger_device.manufacturer or "ABB/FIMER"
    device_model = datalogger_device.device_model or coordinator.vsn_model or "VSN Datalogger"

    # Get custom prefix from options (same logic as sensor.py)
    custom_prefix = config_entry.options.get(CONF_PREFIX_DATALOGGER, "").strip() or None

    # Build friendly device name using shared helper
    device_name = format_device_name(
        manufacturer=manufacturer,
        device_type_simple="datalogger",
        device_model=device_model,
        device_sn_original=datalogger_device.raw_device_id,
        custom_prefix=custom_prefix,
    )

    # Register the main device (datalogger)
    # Use cleaned device_id as identifier for consistency with sensor.py via_device
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, device_identifier)},
        manufacturer=manufacturer,
        model=device_model,
        name=device_name,
        serial_number=datalogger_device.raw_device_id,
        sw_version=coordinator.discovery_result.firmware_version
        if coordinator.discovery_result
        else None,
        configuration_url=f"http://{config_entry.data.get(CONF_HOST)}",
    )

    # Store device_id in coordinator for device triggers
    device = device_registry.async_get_device(identifiers={(DOMAIN, device_identifier)})
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
    """Allow device deletion and sync known_devices list.

    Always allows deletion. Removes the device from the persisted known_devices
    list so it won't trigger a "missing device" repair notification. If the device
    still physically exists, next discovery will find it and re-add it naturally.
    """
    device_id = next(
        (ident[1] for ident in device_entry.identifiers if ident[0] == DOMAIN),
        None,
    )

    if device_id:
        # Remove from known_devices so we don't flag it as "missing"
        known_devices = list(config_entry.data.get(CONF_KNOWN_DEVICES, []))
        updated = [d for d in known_devices if d["device_id"] != device_id]
        if len(updated) != len(known_devices):
            hass.config_entries.async_update_entry(
                config_entry, data={**config_entry.data, CONF_KNOWN_DEVICES: updated}
            )
            _LOGGER.info(
                "Removed device '%s' from known_devices list",
                device_id,
            )

    # Always allow deletion — if device still physically exists,
    # next discovery will find it and re-add it naturally
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


async def async_migrate_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Migrate config entry to a new version.

    Version 1 → 2: Migrate entity IDs to remove category prefixes from display names.
    Version 2 → 3: Re-run migration to fix entities missed by buggy endswith check.
    Version 3 → 4: Fix stale original_name in entity registry after prefix removal.
    Version 4 → 5: Clear stale suggested_object_id so HA rename preview uses correct names.
    Version 5 → 6: Clear stale object_id_base so HA rename preview uses original_name.
    Version 6 → 7: Fix object_id_base — set to original_name (None loses entity name).
    Version 7 → 8: Populate known_devices list from device registry.
    """
    if config_entry.version > 8:
        _LOGGER.error(
            "Cannot downgrade config entry from version %s to 8",
            config_entry.version,
        )
        return False

    if config_entry.version < 3:
        _LOGGER.info(
            "Migrating config entry from version %s to 3",
            config_entry.version,
        )
        await _async_migrate_entity_ids_v2(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=3)
        _LOGGER.info("Config entry migration to version 3 complete")

    if config_entry.version < 4:
        _LOGGER.info(
            "Migrating config entry from version %s to 4",
            config_entry.version,
        )
        await _async_fix_original_names_v4(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=4)
        _LOGGER.info("Config entry migration to version 4 complete")

    if config_entry.version < 5:
        _LOGGER.info(
            "Migrating config entry from version %s to 5",
            config_entry.version,
        )
        _async_clear_stale_suggested_object_ids_v5(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=5)
        _LOGGER.info("Config entry migration to version 5 complete")

    if config_entry.version < 6:
        _LOGGER.info(
            "Migrating config entry from version %s to 6",
            config_entry.version,
        )
        _async_clear_stale_object_id_base_v6(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=6)
        _LOGGER.info("Config entry migration to version 6 complete")

    if config_entry.version < 7:
        _LOGGER.info(
            "Migrating config entry from version %s to 7",
            config_entry.version,
        )
        _async_fix_object_id_base_v7(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=7)
        _LOGGER.info("Config entry migration to version 7 complete")

    if config_entry.version < 8:
        _LOGGER.info(
            "Migrating config entry from version %s to 8",
            config_entry.version,
        )
        _async_populate_known_devices_v8(hass, config_entry)
        hass.config_entries.async_update_entry(config_entry, version=8)
        _LOGGER.info("Config entry migration to version 8 complete")

    return True


async def _async_migrate_entity_ids_v2(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Migrate entity IDs from old display names (with category prefixes) to new ones.

    Runs once during config entry version 1 → 2 migration.
    Renames entity IDs to match the cleaned display names (e.g., removes
    "Inverter - ", "Device - ", "System - " prefixes).

    This runs before async_setup_entry, so runtime_data is NOT available.
    We use the entity registry and translations only.
    """
    registry = er.async_get(hass)

    # Load NEW English translations (with cleaned display names)
    sensor_translations = await async_get_entity_translations(hass, DOMAIN)

    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    migrated = 0

    for entity_entry in entities:
        # Parse unique_id: {domain}_{...}_{device_type}_{serial_compact}_{point_name}
        unique_id_parts = entity_entry.unique_id.split("_")
        if len(unique_id_parts) < 8:
            continue

        point_name = "_".join(unique_id_parts[7:])

        # Get NEW translated name (after prefix cleanup)
        translated_name = sensor_translations.get(point_name, "")
        if not translated_name:
            continue

        new_suffix = slugify(translated_name)

        # Build new entity_id from device name + new translated suffix
        domain = entity_entry.entity_id.split(".")[0]
        device_entry = (
            dr.async_get(hass).async_get(entity_entry.device_id) if entity_entry.device_id else None
        )
        if not device_entry or not device_entry.name:
            continue

        new_entity_id = f"{domain}.{slugify(device_entry.name)}_{new_suffix}"

        if entity_entry.entity_id == new_entity_id:
            continue  # Already correct

        # Check target is available
        if registry.async_get(new_entity_id):
            _LOGGER.debug(
                "Migration skip: target %s already exists for %s",
                new_entity_id,
                entity_entry.entity_id,
            )
            continue

        try:
            registry.async_update_entity(entity_entry.entity_id, new_entity_id=new_entity_id)
            migrated += 1
            _LOGGER.info("Migrated entity ID: %s → %s", entity_entry.entity_id, new_entity_id)
        except ValueError:
            _LOGGER.debug(
                "Migration skip: cannot rename %s → %s",
                entity_entry.entity_id,
                new_entity_id,
            )

    if migrated > 0:
        _LOGGER.info(
            "Migrated %d entity IDs to remove category prefixes from display names",
            migrated,
        )
    else:
        _LOGGER.info("Entity ID migration v2: no changes needed")


async def _async_fix_original_names_v4(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Fix stale original_name in entity registry after category prefix removal.

    The v2/v3 migration renamed entity_ids but did not update original_name.
    This caused HA's "rename device entity IDs" feature to propose wrong IDs
    based on the old cached names (e.g., "Device - Product Number" instead of
    "Product Number").
    """
    registry = er.async_get(hass)

    # Load current English translations (with cleaned display names)
    sensor_translations = await async_get_entity_translations(hass, DOMAIN)

    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    fixed = 0

    for entity_entry in entities:
        # Parse unique_id: {domain}_{...}_{device_type}_{serial_compact}_{point_name}
        unique_id_parts = entity_entry.unique_id.split("_")
        if len(unique_id_parts) < 8:
            continue

        point_name = "_".join(unique_id_parts[7:])

        # Get current translated name (after prefix cleanup)
        translated_name = sensor_translations.get(point_name, "")
        if not translated_name:
            continue

        # Check if original_name is stale (differs from current translation)
        if entity_entry.original_name == translated_name:
            continue

        if entity_entry.original_name is None:
            continue

        try:
            registry.async_update_entity(
                entity_entry.entity_id,
                original_name=translated_name,
            )
            fixed += 1
            _LOGGER.info(
                "Fixed original_name: %s → %s (entity: %s)",
                entity_entry.original_name,
                translated_name,
                entity_entry.entity_id,
            )
        except ValueError:
            _LOGGER.debug(
                "Cannot fix original_name for %s",
                entity_entry.entity_id,
            )

    if fixed > 0:
        _LOGGER.info(
            "Fixed %d entity original_name values to match current translations",
            fixed,
        )
    else:
        _LOGGER.info("Entity original_name migration v4: no changes needed")


@callback
def _async_clear_stale_suggested_object_ids_v5(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Clear stale suggested_object_id in entity registry.

    HA's "rename device entity IDs" preview uses suggested_object_id (persisted in the
    entity registry) to compute proposed entity IDs. This field is only updated when the
    entity platform loads. If entities are in "restored" state (device offline), the field
    retains old values from before the v1.4.1 display name cleanup (with category prefixes).

    Clearing suggested_object_id forces HA to fall through to original_name (fixed in v4)
    for the rename preview computation. The field will be repopulated with correct values
    when the entity platform next loads.
    """
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    cleared = 0

    for entity_entry in entities:
        # Only clear if suggested_object_id is set (non-None)
        if entity_entry.suggested_object_id is None:
            continue

        try:
            # Use private API to clear suggested_object_id — the public
            # async_update_entity() does not expose this field.
            # Safe: field is repopulated by entity platform on next load.
            registry._async_update_entity(  # noqa: SLF001
                entity_entry.entity_id,
                suggested_object_id=None,
            )
            cleared += 1
        except (ValueError, AttributeError):
            _LOGGER.debug(
                "Cannot clear suggested_object_id for %s",
                entity_entry.entity_id,
            )

    if cleared > 0:
        _LOGGER.info(
            "Cleared stale suggested_object_id for %d entities (will refresh on next load)",
            cleared,
        )
    else:
        _LOGGER.info("Entity suggested_object_id migration v5: no changes needed")


@callback
def _async_clear_stale_object_id_base_v6(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Clear stale object_id_base in entity registry.

    HA's "rename device entity IDs" preview computes proposed entity IDs from
    object_id_base (passed as original_name to _async_get_full_entity_name).
    This field is only updated when the entity platform loads. For entities in
    "restored" state (device offline), it retains old values with category prefixes
    (e.g., "Device - Product Number" instead of "Product Number").

    Verified via .storage/core.entity_registry: object_id_base holds old prefixed
    names while original_name is already correct (fixed in v4). Clearing object_id_base
    forces HA to fall through to original_name for rename preview computation.
    The field will be repopulated by the entity platform on next load.
    """
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    cleared = 0

    for entity_entry in entities:
        if entity_entry.object_id_base is None:
            continue

        # Only clear if object_id_base differs from original_name (i.e., stale)
        if entity_entry.object_id_base == entity_entry.original_name:
            continue

        try:
            # Use private API — public async_update_entity() does not expose
            # object_id_base. Safe: repopulated by entity platform on next load.
            registry._async_update_entity(  # noqa: SLF001
                entity_entry.entity_id,
                object_id_base=None,
            )
            cleared += 1
            _LOGGER.info(
                "Cleared stale object_id_base '%s' for %s (original_name='%s')",
                entity_entry.object_id_base,
                entity_entry.entity_id,
                entity_entry.original_name,
            )
        except (ValueError, AttributeError):
            _LOGGER.debug(
                "Cannot clear object_id_base for %s",
                entity_entry.entity_id,
            )

    if cleared > 0:
        _LOGGER.info(
            "Cleared stale object_id_base for %d entities (will refresh on next load)",
            cleared,
        )
    else:
        _LOGGER.info("Entity object_id_base migration v6: no changes needed")


@callback
def _async_fix_object_id_base_v7(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Set object_id_base to original_name for entities where it is None.

    v6 migration incorrectly set object_id_base to None. When object_id_base is None,
    HA's _async_get_full_entity_name falls through to just the device name (losing the
    entity name portion), producing entity IDs like sensor.abb_fimer_datalogger instead
    of sensor.abb_fimer_datalogger_product_number.

    Fix: set object_id_base = original_name (already correct from v4 migration).
    """
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    fixed = 0

    for entity_entry in entities:
        if entity_entry.object_id_base is not None:
            continue

        if not entity_entry.original_name:
            continue

        try:
            registry._async_update_entity(  # noqa: SLF001
                entity_entry.entity_id,
                object_id_base=entity_entry.original_name,
            )
            fixed += 1
            _LOGGER.info(
                "Set object_id_base='%s' for %s",
                entity_entry.original_name,
                entity_entry.entity_id,
            )
        except (ValueError, AttributeError):
            _LOGGER.debug(
                "Cannot fix object_id_base for %s",
                entity_entry.entity_id,
            )

    if fixed > 0:
        _LOGGER.info(
            "Fixed object_id_base for %d entities",
            fixed,
        )
    else:
        _LOGGER.info("Entity object_id_base migration v7: no changes needed")


@callback
def _async_populate_known_devices_v8(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Populate known_devices from existing device registry entries.

    Reads the device registry for this config entry and builds the initial
    known_devices list. Infers is_datalogger from the model field.
    """
    device_registry = dr.async_get(hass)
    known_devices: list[dict] = []

    for device_entry in dr.async_entries_for_config_entry(device_registry, config_entry.entry_id):
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                model = device_entry.model or ""
                is_datalogger = "VSN300" in model or "VSN700" in model
                known_devices.append(
                    {
                        "device_id": identifier[1],
                        "device_type": "datalogger" if is_datalogger else "unknown",
                        "is_datalogger": is_datalogger,
                    }
                )
                break

    new_data = {**config_entry.data, CONF_KNOWN_DEVICES: known_devices}
    hass.config_entries.async_update_entry(config_entry, data=new_data)
    _LOGGER.info(
        "Populated known_devices with %d devices from registry",
        len(known_devices),
    )


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
