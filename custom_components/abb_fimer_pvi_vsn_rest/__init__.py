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
from homeassistant.helpers import device_registry as dr
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
STARTUP_LOGGED_KEY = f"{DOMAIN}_startup_logged"

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
        # HA handles logging for ConfigEntryNotReady automatically
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
        # HA handles logging for ConfigEntryNotReady automatically
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    # Store runtime data
    config_entry.runtime_data = RuntimeData(coordinator=coordinator)

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

    # Register the main device (datalogger)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, logger_sn)},
        manufacturer=coordinator.discovery_result.logger_model or "ABB/FIMER",
        model=coordinator.vsn_model or "VSN Datalogger",
        name=f"{DOMAIN}_datalogger_{logger_sn.lower().replace('-', '').replace(':', '')}",
        serial_number=logger_sn,
        sw_version=coordinator.discovery_result.firmware_version,
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
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
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
        _LOGGER.error(
            "Cannot delete device using device delete. Remove the integration instead."
        )
        return False
    return True
