"""ABB FIMER PVI VSN REST Integration.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, STARTUP_MESSAGE

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type ABBFimerPVIVSNRestConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Runtime data for the integration."""

    coordinator: object  # TODO: Add actual type when coordinator is implemented


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Set up ABB FIMER PVI VSN REST from a config entry."""
    _LOGGER.info(STARTUP_MESSAGE)

    # TODO: Initialize abb-fimer-vsn-rest-client and coordinator
    # client = ABBFimerVSNRestClient(...)
    # await client.connect()
    # coordinator = ABBFimerPVIVSNRestCoordinator(hass, config_entry, client)
    # await coordinator.async_config_entry_first_refresh()

    # config_entry.runtime_data = RuntimeData(coordinator=coordinator)
    # await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    raise ConfigEntryNotReady("TODO: Implement async_setup_entry")


async def async_unload_entry(
    hass: HomeAssistant, config_entry: ABBFimerPVIVSNRestConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
