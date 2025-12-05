"""Config flow for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .abb_fimer_vsn_rest_client.discovery import discover_vsn_device
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .abb_fimer_vsn_rest_client.utils import check_socket_connection
from .const import (
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


class ABBFimerPVIVSNRestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore  # noqa: PGH003
    """Handle a config flow for ABB FIMER PVI VSN REST."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

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

                # Update config entry
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VSN_MODEL: info["vsn_model"],
                        CONF_REQUIRES_AUTH: info["requires_auth"],
                    },
                )

                # Reload the integration
                await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reconfigure_successful")

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
                    vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST)): str,
                    vol.Optional(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                    ): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "current_host": entry.data.get(CONF_HOST),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ABBFimerPVIVSNRestOptionsFlowHandler:
        """Get the options flow for this handler."""
        return ABBFimerPVIVSNRestOptionsFlowHandler()


class ABBFimerPVIVSNRestOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for ABB FIMER PVI VSN REST."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
