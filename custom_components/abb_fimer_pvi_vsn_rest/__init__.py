"""ABB FIMER PVI VSN REST Integration.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from .abb_fimer_vsn_rest_client.discovery import discover_vsn_device
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    STARTUP_MESSAGE,
)
from .coordinator import ABBFimerPVIVSNRestCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type ABBFimerPVIVSNRestConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Runtime data for the integration."""

    coordinator: ABBFimerPVIVSNRestCoordinator


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Set up ABB FIMER PVI VSN REST from a config entry."""
    _LOGGER.info(STARTUP_MESSAGE)

    # Get configuration
    host: str = config_entry.data[CONF_HOST]
    username: str = config_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password: str = config_entry.data.get(CONF_PASSWORD, "")
    scan_interval: int = config_entry.options.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
    )
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
    except Exception as err:
        _LOGGER.error("Discovery failed during setup: %s", err)
        raise ConfigEntryNotReady(f"Discovery failed: {err}") from err

    # Initialize REST client with discovered VSN model
    client = ABBFimerVSNRestClient(
        session=session,
        base_url=base_url,
        username=username,
        password=password,
        vsn_model=discovery_result.vsn_model,
        timeout=10,
    )

    # Initialize coordinator with discovery result
    coordinator = ABBFimerPVIVSNRestCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=scan_interval),
        discovery_result=discovery_result,
    )

    # Perform initial data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to fetch initial data: %s", err)
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    # Store runtime data
    config_entry.runtime_data = RuntimeData(coordinator=coordinator)

    # Register an update listener for config flow options changes
    # Listener is attached when entry loads and automatically detached at unload
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _LOGGER.info(
        "Successfully set up %s integration for %s",
        DOMAIN,
        coordinator.vsn_model or "VSN device",
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Shutdown coordinator and cleanup
    if unload_ok:
        coordinator = config_entry.runtime_data.coordinator
        await coordinator.async_shutdown()
        _LOGGER.info("Successfully unloaded %s integration", DOMAIN)

    return unload_ok


@callback
def async_reload_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> None:
    """Reload the config entry when options change."""
    _LOGGER.debug("Scheduling reload of config entry")
    hass.config_entries.async_schedule_reload(config_entry.entry_id)
