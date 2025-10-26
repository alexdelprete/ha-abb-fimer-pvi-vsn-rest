"""Config flow for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .const import (
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
    """Validate the connection to VSN device.

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
            "device_info": {...}  # Info from /v1/status
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

    # First check: Socket connection on port 80
    try:
        # Extract hostname from URL
        hostname = host.replace("http://", "").replace("https://", "").split(":")[0]
        port = 80

        # Try to connect to socket with 5 second timeout
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: socket.create_connection((hostname, port), timeout=5)
            ),
            timeout=5,
        )
        _LOGGER.debug("Socket connection to %s:%d successful", hostname, port)
    except (socket.timeout, asyncio.TimeoutError) as err:
        _LOGGER.error("Socket timeout connecting to %s:%d: %s", hostname, port, err)
        raise VSNConnectionError(f"Timeout connecting to {hostname}:{port}") from err
    except (socket.error, OSError) as err:
        _LOGGER.error("Socket error connecting to %s:%d: %s", hostname, port, err)
        raise VSNConnectionError(
            f"Cannot connect to {hostname}:{port} - {err}"
        ) from err

    # Second check: REST API connection with client
    session = async_get_clientsession(hass)
    client = ABBFimerVSNRestClient(
        session=session,
        base_url=base_url,
        username=username or DEFAULT_USERNAME,
        password=password or "",
        timeout=10,
    )

    try:
        # Connect and detect model
        vsn_model = await client.connect()
        _LOGGER.info("Successfully detected VSN model: %s", vsn_model)

        # Fetch status to get device info
        # We'll make a direct status call here since it's validation
        status_url = f"{base_url}/v1/status"
        uri = "/v1/status"

        # Build auth headers based on detected model
        if vsn_model == "VSN300":
            from .abb_fimer_vsn_rest_client.auth import get_vsn300_digest_header

            digest_value = await get_vsn300_digest_header(
                session, base_url, uri, username or DEFAULT_USERNAME, password or ""
            )
            headers = {"Authorization": f"X-Digest {digest_value}"}
        else:  # VSN700
            from .abb_fimer_vsn_rest_client.auth import get_vsn700_basic_auth

            basic_auth = get_vsn700_basic_auth(
                username or DEFAULT_USERNAME, password or ""
            )
            headers = {"Authorization": f"Basic {basic_auth}"}

        async with session.get(
            status_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                status_data = await response.json()
                _LOGGER.debug("Status data retrieved: %s", status_data)

                # Extract useful info for title
                logger_sn = status_data.get("logger", {}).get("sn", "Unknown")
                device_model = (
                    status_data.get("device", {}).get("modelDesc", "Unknown")
                )

                return {
                    "vsn_model": vsn_model,
                    "title": f"{vsn_model} - {logger_sn}",
                    "device_info": status_data,
                }
            else:
                raise VSNConnectionError(
                    f"Failed to fetch status: HTTP {response.status}"
                )

    except VSNAuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise
    except VSNConnectionError as err:
        _LOGGER.error("Connection error: %s", err)
        raise
    except VSNClientError as err:
        _LOGGER.error("Client error: %s", err)
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation: %s", err)
        raise VSNClientError(f"Unexpected error: {err}") from err
    finally:
        await client.close()


class ABBFimerPVIVSNRestConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
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

                # Check if already configured (by host)
                await self.async_set_unique_id(host.lower())
                self._abort_if_unique_id_configured()

                # Create config entry
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_HOST: host,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_VSN_MODEL: info["vsn_model"],
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
        return ABBFimerPVIVSNRestOptionsFlowHandler(config_entry)


class ABBFimerPVIVSNRestOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for ABB FIMER PVI VSN REST."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

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
