"""Config flow for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
from homeassistant.util import slugify

from .abb_fimer_vsn_rest_client.discovery import discover_vsn_device
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .abb_fimer_vsn_rest_client.utils import check_socket_connection
from .const import (
    CONF_PREFIX_BATTERY,
    CONF_PREFIX_DATALOGGER,
    CONF_PREFIX_INVERTER,
    CONF_PREFIX_METER,
    CONF_REGENERATE_ENTITY_IDS,
    CONF_REQUIRES_AUTH,
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Error messages for user feedback
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_UNKNOWN = "unknown"
ERROR_TIMEOUT = "timeout"


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


class ABBFimerPVIVSNRestConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
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

            except VSNAuthenticationError:
                errors["base"] = ERROR_INVALID_AUTH
            except VSNConnectionError as err:
                if "timeout" in str(err).lower():
                    errors["base"] = ERROR_TIMEOUT
                else:
                    errors["base"] = ERROR_CANNOT_CONNECT
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

            except VSNAuthenticationError:
                errors["base"] = ERROR_INVALID_AUTH
            except VSNConnectionError as err:
                if "timeout" in str(err).lower():
                    errors["base"] = ERROR_TIMEOUT
                else:
                    errors["base"] = ERROR_CANNOT_CONNECT
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

        # Determine which device types exist from discovered devices
        has_inverters = False
        has_datalogger = False
        has_meters = False
        has_batteries = False

        # Access discovered devices from coordinator (if available)
        if hasattr(self.config_entry, "runtime_data") and self.config_entry.runtime_data:
            coordinator = self.config_entry.runtime_data.coordinator
            discovered_devices = getattr(coordinator, "discovered_devices", None) or []

            for device in discovered_devices:
                if device.is_datalogger:
                    has_datalogger = True
                elif device.device_type.startswith("inverter"):
                    has_inverters = True
                elif device.device_type == "meter":
                    has_meters = True
                elif device.device_type == "battery":
                    has_batteries = True
        else:
            # Fallback: show all fields if no runtime data (shouldn't happen normally)
            _LOGGER.debug("No runtime_data available, showing all prefix fields")
            has_inverters = has_datalogger = has_meters = has_batteries = True

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

        # Only add prefix fields for device types that exist
        if has_inverters:
            schema_dict[
                vol.Optional(
                    CONF_PREFIX_INVERTER,
                    default=current_options.get(CONF_PREFIX_INVERTER, ""),
                )
            ] = str

        if has_datalogger:
            schema_dict[
                vol.Optional(
                    CONF_PREFIX_DATALOGGER,
                    default=current_options.get(CONF_PREFIX_DATALOGGER, ""),
                )
            ] = str

        if has_meters:
            schema_dict[
                vol.Optional(
                    CONF_PREFIX_METER,
                    default=current_options.get(CONF_PREFIX_METER, ""),
                )
            ] = str

        if has_batteries:
            schema_dict[
                vol.Optional(
                    CONF_PREFIX_BATTERY,
                    default=current_options.get(CONF_PREFIX_BATTERY, ""),
                )
            ] = str

        # Always show regenerate checkbox if any device type has prefix support
        if has_inverters or has_datalogger or has_meters or has_batteries:
            schema_dict[
                vol.Optional(
                    CONF_REGENERATE_ENTITY_IDS,
                    default=False,
                )
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )

    async def _regenerate_entity_ids(self, new_options: dict[str, Any]) -> None:
        """Regenerate entity IDs based on new prefix settings.

        This updates entity_id in the entity registry to match the new device names.
        Warning: This breaks existing automations and dashboards!
        """
        registry = er.async_get(self.hass)

        # Map device types to their prefix options
        prefix_map = {
            "inverter": new_options.get(CONF_PREFIX_INVERTER, ""),
            "datalogger": new_options.get(CONF_PREFIX_DATALOGGER, ""),
            "meter": new_options.get(CONF_PREFIX_METER, ""),
            "battery": new_options.get(CONF_PREFIX_BATTERY, ""),
        }

        # Get all entities for this config entry
        entities = er.async_entries_for_config_entry(registry, self.config_entry.entry_id)

        regenerated_count = 0
        for entity_entry in entities:
            # Extract device type from unique_id
            # Format: abb_fimer_pvi_vsn_rest_{device_type}_{serial}_{point_name}
            unique_id_parts = entity_entry.unique_id.split("_")
            if len(unique_id_parts) >= 8:
                # Find device type (after domain prefix: abb_fimer_pvi_vsn_rest)
                device_type = unique_id_parts[5]  # inverter, datalogger, meter, battery
                # Point name is everything after the serial (index 6 is serial)
                point_name = "_".join(unique_id_parts[7:])

                custom_prefix = prefix_map.get(device_type, "").strip()

                if not custom_prefix:
                    # Keep current entity_id if no prefix set
                    continue

                # Generate new entity_id from custom prefix
                new_entity_id = f"sensor.{slugify(custom_prefix)}_{point_name}"

                # Update if different and new ID doesn't exist
                if entity_entry.entity_id != new_entity_id:
                    if not registry.async_get(new_entity_id):
                        registry.async_update_entity(
                            entity_entry.entity_id, new_entity_id=new_entity_id
                        )
                        regenerated_count += 1
                        _LOGGER.info(
                            "Regenerated entity ID: %s → %s",
                            entity_entry.entity_id,
                            new_entity_id,
                        )
                    else:
                        _LOGGER.warning(
                            "Cannot regenerate %s → %s: target already exists",
                            entity_entry.entity_id,
                            new_entity_id,
                        )

        if regenerated_count > 0:
            _LOGGER.info("Regenerated %d entity IDs", regenerated_count)
