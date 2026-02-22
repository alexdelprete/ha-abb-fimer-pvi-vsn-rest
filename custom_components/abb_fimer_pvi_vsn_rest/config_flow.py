"""Config flow for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import slugify

from .abb_fimer_vsn_rest_client.discovery import discover_vsn_device
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
    VSNUnsupportedDeviceError,
)
from .abb_fimer_vsn_rest_client.utils import check_socket_connection
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_ENABLE_STARTUP_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_RECOVERY_SCRIPT,
    CONF_REGENERATE_ENTITY_IDS,
    CONF_REQUIRES_AUTH,
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_ENABLE_STARTUP_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_FAILURES_THRESHOLD,
    MAX_SCAN_INTERVAL,
    MIN_FAILURES_THRESHOLD,
    MIN_SCAN_INTERVAL,
    TYPE_TO_CONF_PREFIX,
)
from .helpers import (
    async_get_entity_translations,
    build_prefix_by_device,
    compact_serial_number,
    format_device_name,
    get_device_type_simple,
)

_LOGGER = logging.getLogger(__name__)

# Error messages for user feedback
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_UNKNOWN = "unknown"
ERROR_TIMEOUT = "timeout"
ERROR_UNSUPPORTED_DEVICE = "unsupported_device"


async def validate_connection(
    hass: HomeAssistant, host: str, username: str, password: str
) -> dict[str, Any]:
    """Validate the connection to VSN device using discovery.

    Args:
        hass: Home Assistant instance
        host: Device hostname or IP
        username: Authentication username
        password: Authentication password

    Returns:
        Dictionary with validation results:
        {
            "vsn_model": "VSN300" or "VSN700",
            "title": "Device title for config entry",
            "logger_sn": "Logger serial number",
            "devices": list[DiscoveredDevice]  # All discovered devices
        }

    Raises:
        VSNConnectionError: If connection fails
        VSNAuthenticationError: If authentication fails
        VSNClientError: For other client errors

    """
    # Build base URL
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    _LOGGER.debug("Validating connection to %s", base_url)

    # First check: Socket connection before HTTP request
    await check_socket_connection(base_url, timeout=5)

    # Second check: Perform device discovery
    session = async_get_clientsession(hass)

    try:
        # Perform discovery (this validates connection, auth, and gathers device info)
        discovery = await discover_vsn_device(
            session=session,
            base_url=base_url,
            username=username or DEFAULT_USERNAME,
            password=password or "",
            timeout=10,
        )

        _LOGGER.info("Successfully detected VSN model: %s", discovery.vsn_model)

        # Log discovered devices for debugging
        for device in discovery.devices:
            _LOGGER.debug(
                "Found device: %s (%s) - Model: %s, Manufacturer: %s",
                device.device_id,
                device.device_type,
                device.device_model or "Unknown",
                device.manufacturer or "Unknown",
            )

        return {
            "vsn_model": discovery.vsn_model,
            "requires_auth": discovery.requires_auth,
            "title": discovery.get_title(),
            "logger_sn": discovery.logger_sn,
            "devices": discovery.devices,  # Include discovered devices
        }

    except VSNAuthenticationError as err:
        err_str = str(err)
        _LOGGER.error("Authentication failed: %s", err)
        # Check if error suggests enabling debug logging
        if "Enable debug logging" not in err_str:
            _LOGGER.info(
                "Enable debug logging (logger: custom_components.abb_fimer_pvi_vsn_rest) "
                "for detailed authentication flow information"
            )
        raise
    except VSNConnectionError as err:
        err_str = str(err)
        _LOGGER.error("Connection error: %s", err)

        # Check for SSL/TLS certificate errors
        if any(
            keyword in err_str
            for keyword in [
                "SSL",
                "CERTIFICATE",
                "certificate",
                "self-signed",
                "verify failed",
            ]
        ):
            _LOGGER.error(
                "SSL/TLS certificate error detected. This device may be using a self-signed certificate. "
                "Enable debug logging for detailed SSL error information. "
                "Logger: custom_components.abb_fimer_pvi_vsn_rest"
            )
        else:
            _LOGGER.info(
                "Enable debug logging (logger: custom_components.abb_fimer_pvi_vsn_rest) "
                "for detailed connection diagnostics"
            )
        raise
    except VSNUnsupportedDeviceError as err:
        _LOGGER.error(
            "Unsupported device: %s - Device does not have VSN REST API endpoints",
            err,
        )
        raise
    except VSNClientError as err:
        err_str = str(err)
        _LOGGER.error("Client error: %s", err)
        # Check if error suggests enabling debug logging
        if "Enable debug logging" not in err_str:
            _LOGGER.info(
                "Enable debug logging (logger: custom_components.abb_fimer_pvi_vsn_rest) "
                "for detailed error information"
            )
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        _LOGGER.info(
            "Enable debug logging (logger: custom_components.abb_fimer_pvi_vsn_rest) "
            "for detailed diagnostics"
        )
        raise VSNClientError(f"Unexpected error: {err}") from err


class ABBFimerPVIVSNRestConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABB FIMER PVI VSN REST."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ABBFimerPVIVSNRestOptionsFlow:
        """Get the options flow for this handler."""
        return ABBFimerPVIVSNRestOptionsFlow()

    def __init__(self) -> None:
        """Initialize config flow."""
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Get form values
            host = user_input[CONF_HOST].strip()
            username = user_input.get(CONF_USERNAME, "").strip() or DEFAULT_USERNAME
            password = user_input.get(CONF_PASSWORD, "")

            _LOGGER.debug("User input: host=%s, username=%s", host, username)

            try:
                # Validate connection
                info = await validate_connection(self.hass, host, username, password)

                # Check if already configured (by logger serial number)
                await self.async_set_unique_id(info["logger_sn"].lower())
                self._abort_if_unique_id_configured()

                # Create config entry
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VSN_MODEL: info["vsn_model"],
                        CONF_REQUIRES_AUTH: info["requires_auth"],
                    },
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

            except AbortFlow:
                # Re-raise AbortFlow exceptions (e.g., already_configured)
                raise
            except VSNAuthenticationError:
                errors["base"] = ERROR_INVALID_AUTH
            except VSNConnectionError as err:
                if "timeout" in str(err).lower():
                    errors["base"] = ERROR_TIMEOUT
                else:
                    errors["base"] = ERROR_CANNOT_CONNECT
            except VSNUnsupportedDeviceError:
                errors["base"] = ERROR_UNSUPPORTED_DEVICE
            except VSNClientError:
                errors["base"] = ERROR_UNKNOWN
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in config flow")
                errors["base"] = ERROR_UNKNOWN

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "default_username": DEFAULT_USERNAME,
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Get form values
            host = user_input[CONF_HOST].strip()
            username = user_input.get(CONF_USERNAME, "").strip() or DEFAULT_USERNAME
            password = user_input.get(CONF_PASSWORD, "")

            _LOGGER.debug("Reconfigure: host=%s, username=%s", host, username)

            try:
                # Validate connection
                info = await validate_connection(self.hass, host, username, password)

                # Use async_update_reload_and_abort for modern reconfigure pattern
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VSN_MODEL: info["vsn_model"],
                        CONF_REQUIRES_AUTH: info["requires_auth"],
                    },
                )

            except AbortFlow:
                # Re-raise AbortFlow exceptions
                raise
            except VSNAuthenticationError:
                errors["base"] = ERROR_INVALID_AUTH
            except VSNConnectionError as err:
                if "timeout" in str(err).lower():
                    errors["base"] = ERROR_TIMEOUT
                else:
                    errors["base"] = ERROR_CANNOT_CONNECT
            except VSNUnsupportedDeviceError:
                errors["base"] = ERROR_UNSUPPORTED_DEVICE
            except VSNClientError:
                errors["base"] = ERROR_UNKNOWN
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in reconfigure flow")
                errors["base"] = ERROR_UNKNOWN

        # Show form with current values
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=reconfigure_entry.data.get(CONF_HOST)): str,
                    vol.Optional(
                        CONF_USERNAME,
                        default=reconfigure_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                    ): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "current_host": str(reconfigure_entry.data.get(CONF_HOST, "")),
            },
        )


class ABBFimerPVIVSNRestOptionsFlow(OptionsFlowWithReload):
    """Handle options flow for ABB FIMER PVI VSN REST with auto-reload."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Check if entity ID regeneration was requested (one-time action)
            regenerate = user_input.pop(CONF_REGENERATE_ENTITY_IDS, False)

            if regenerate:
                await self._regenerate_entity_ids(user_input)

            _LOGGER.debug(
                "Options updated: scan_interval=%s",
                user_input.get(CONF_SCAN_INTERVAL),
            )
            return self.async_create_entry(data=user_input)

        # Access discovered devices from coordinator (if available)
        discovered_devices = []
        if hasattr(self.config_entry, "runtime_data") and self.config_entry.runtime_data:
            coordinator = self.config_entry.runtime_data.coordinator
            discovered_devices = getattr(coordinator, "discovered_devices", None) or []

        # Group discovered devices by simplified type, sorted for stable ordering
        devices_by_type: dict[str, list] = {}
        for device in discovered_devices:
            dtype = get_device_type_simple(device)
            devices_by_type.setdefault(dtype, []).append(device)
        for device_list in devices_by_type.values():
            device_list.sort(key=lambda d: d.device_id)

        # Get current options with defaults
        current_options = self.config_entry.options

        # Build schema dynamically based on discovered device types
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=current_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="seconds",
                )
            ),
        }

        # Repair notification options
        schema_dict[
            vol.Optional(
                CONF_ENABLE_REPAIR_NOTIFICATION,
                default=current_options.get(
                    CONF_ENABLE_REPAIR_NOTIFICATION, DEFAULT_ENABLE_REPAIR_NOTIFICATION
                ),
            )
        ] = bool

        schema_dict[
            vol.Optional(
                CONF_ENABLE_STARTUP_NOTIFICATION,
                default=current_options.get(
                    CONF_ENABLE_STARTUP_NOTIFICATION, DEFAULT_ENABLE_STARTUP_NOTIFICATION
                ),
            )
        ] = bool

        schema_dict[
            vol.Required(
                CONF_FAILURES_THRESHOLD,
                default=current_options.get(CONF_FAILURES_THRESHOLD, DEFAULT_FAILURES_THRESHOLD),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=MIN_FAILURES_THRESHOLD,
                max=MAX_FAILURES_THRESHOLD,
                mode=NumberSelectorMode.BOX,
                step=1,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_RECOVERY_SCRIPT,
                default=current_options.get(CONF_RECOVERY_SCRIPT, DEFAULT_RECOVERY_SCRIPT),
            )
        ] = TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.TEXT,
                multiline=False,
            )
        )

        # Add per-device prefix fields
        # Single device of a type → base key (e.g., "prefix_battery") for backward compat
        # Multiple devices of same type → indexed keys (e.g., "prefix_battery_1", "prefix_battery_2")
        # Build description_placeholders to show serial numbers in field descriptions
        has_any_device = False
        description_placeholders: dict[str, str] = {}
        for dtype, devices in devices_by_type.items():
            base_key = TYPE_TO_CONF_PREFIX.get(dtype)
            if not base_key:
                continue
            has_any_device = True

            if len(devices) == 1:
                # Single device: use base key (backward compatible)
                schema_dict[vol.Optional(base_key, default=current_options.get(base_key, ""))] = str
            else:
                # Multiple devices: use indexed keys with serial numbers in descriptions
                for i, device in enumerate(devices, start=1):
                    key = f"{base_key}_{i}"
                    schema_dict[vol.Optional(key, default=current_options.get(key, ""))] = str
                    # Add serial number placeholder for this field's description
                    # e.g., "battery_1_sn" → "113049-3P72-0221"
                    placeholder_key = f"{dtype}_{i}_sn"
                    description_placeholders[placeholder_key] = device.device_id

        # Show regenerate checkbox if any devices exist
        if has_any_device:
            schema_dict[
                vol.Optional(
                    CONF_REGENERATE_ENTITY_IDS,
                    default=False,
                )
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders=description_placeholders if description_placeholders else None,
        )

    async def _regenerate_entity_ids(self, new_options: dict[str, Any]) -> None:
        """Regenerate entity IDs based on new prefix settings.

        Uses translated entity names (from en.json) as suffixes to match HA's native
        entity_id generation convention: {domain}.{slugify(device_name)}_{slugify(translated_name)}.
        Also clears any user-set custom entity names so that HA uses the translation-based
        names, ensuring consistency between entity_id and friendly_name.
        Warning: This breaks existing automations and dashboards!
        """
        # Need runtime_data with coordinator for device discovery info
        if not hasattr(self.config_entry, "runtime_data") or not self.config_entry.runtime_data:
            _LOGGER.warning("Cannot regenerate entity IDs: runtime_data not available")
            return

        coordinator = self.config_entry.runtime_data.coordinator

        # Load English entity translations via HA's built-in translation API
        # Returns {point_name: translated_name}, e.g. {"watts": "Power AC"}
        sensor_translations = await async_get_entity_translations(self.hass, DOMAIN)

        # Build device lookup by compact serial
        device_lookup: dict[str, Any] = {}
        for device in coordinator.discovered_devices:
            key = compact_serial_number(device.device_id)
            device_lookup[key] = device

        registry = er.async_get(self.hass)

        # Build device_id_compact → custom_prefix mapping using shared helper
        prefix_by_device = build_prefix_by_device(coordinator.discovered_devices, new_options)

        # Get all entities for this config entry
        entities = er.async_entries_for_config_entry(registry, self.config_entry.entry_id)

        # Phase 1: Build complete rename plan
        rename_plan: list[tuple[er.RegistryEntry, str, bool]] = []
        target_sources: dict[str, list[str]] = defaultdict(list)

        for entity_entry in entities:
            # Extract device_id_compact and point_name from unique_id
            # Format: abb_fimer_pvi_vsn_rest_{device_type}_{serial_compact}_{point_name}
            # Indices: 0   1     2   3    4    5             6                7+
            unique_id_parts = entity_entry.unique_id.split("_")
            if len(unique_id_parts) < 8:
                continue

            # Find device type (after domain prefix: abb_fimer_pvi_vsn_rest)
            device_type = unique_id_parts[5]  # inverter, datalogger, meter, battery
            device_sn_compact = unique_id_parts[6]
            # Point name is everything after the serial (index 6 is serial)
            point_name = "_".join(unique_id_parts[7:])

            # Find matching discovered device for device name computation
            discovered = device_lookup.get(device_sn_compact)
            if not discovered:
                _LOGGER.debug(
                    "Skipping entity %s: no discovered device for serial %s",
                    entity_entry.entity_id,
                    device_sn_compact,
                )
                continue

            # Compute device name (custom prefix or default friendly name)
            custom_prefix = prefix_by_device.get(device_sn_compact, "").strip() or None
            device_name = format_device_name(
                manufacturer=discovered.manufacturer or "ABB/FIMER",
                device_type_simple=device_type,
                device_model=discovered.device_model,
                device_sn_original=discovered.device_id,
                custom_prefix=custom_prefix,
            )

            # Get translated entity name (matches HA's entity_id generation)
            entity_name = sensor_translations.get(point_name, point_name)

            # Generate entity_id matching HA's convention
            domain = entity_entry.entity_id.split(".")[0]  # sensor, binary_sensor, etc.
            new_entity_id = f"{domain}.{slugify(device_name)}_{slugify(entity_name)}"

            # Determine what needs updating
            needs_id_update = entity_entry.entity_id != new_entity_id
            needs_name_clear = entity_entry.name is not None

            if not needs_id_update and not needs_name_clear:
                continue

            rename_plan.append((entity_entry, new_entity_id, needs_name_clear))

            # Track targets for collision detection (only actual renames)
            if needs_id_update:
                target_sources[new_entity_id].append(entity_entry.entity_id)

        # Phase 1b: Detect collisions (multiple entities targeting same entity_id)
        collision_targets: set[str] = set()
        for target, sources in target_sources.items():
            if len(sources) > 1:
                collision_targets.add(target)
                _LOGGER.warning(
                    "Collision detected: %d entities target '%s': %s (keeping first, skipping rest)",
                    len(sources),
                    target,
                    sorted(sources),
                )

        # Phase 2: Execute renames
        regenerated_count = 0
        names_cleared = 0

        for entity_entry, new_entity_id, needs_name_clear in rename_plan:
            needs_id_update = entity_entry.entity_id != new_entity_id

            # Skip collision losers (keep first entity alphabetically)
            if needs_id_update and new_entity_id in collision_targets:
                winner = sorted(target_sources[new_entity_id])[0]
                if entity_entry.entity_id != winner:
                    _LOGGER.info(
                        "Skipping collision loser: %s → %s (winner: %s)",
                        entity_entry.entity_id,
                        new_entity_id,
                        winner,
                    )
                    if needs_name_clear:
                        registry.async_update_entity(entity_entry.entity_id, name=None)
                        names_cleared += 1
                    continue

            # Build update kwargs for a single registry call
            update_kwargs: dict[str, Any] = {}

            if needs_id_update:
                if registry.async_get(new_entity_id):
                    _LOGGER.warning(
                        "Cannot regenerate %s → %s: target already exists",
                        entity_entry.entity_id,
                        new_entity_id,
                    )
                    if needs_name_clear:
                        registry.async_update_entity(entity_entry.entity_id, name=None)
                        names_cleared += 1
                    continue
                update_kwargs["new_entity_id"] = new_entity_id

            if needs_name_clear:
                update_kwargs["name"] = None

            # Apply all updates in a single call
            registry.async_update_entity(entity_entry.entity_id, **update_kwargs)

            if needs_id_update:
                regenerated_count += 1
                _LOGGER.info(
                    "Regenerated entity ID: %s → %s",
                    entity_entry.entity_id,
                    new_entity_id,
                )
            if needs_name_clear:
                names_cleared += 1
                _LOGGER.info(
                    "Cleared custom name '%s' for %s",
                    entity_entry.name,
                    new_entity_id if needs_id_update else entity_entry.entity_id,
                )

        if regenerated_count > 0:
            _LOGGER.info("Regenerated %d entity IDs", regenerated_count)
        if names_cleared > 0:
            _LOGGER.info("Cleared %d custom entity names", names_cleared)
