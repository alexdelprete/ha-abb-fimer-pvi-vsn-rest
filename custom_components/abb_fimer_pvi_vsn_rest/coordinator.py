"""Data update coordinator for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from .abb_fimer_vsn_rest_client.discovery import DiscoveredDevice, DiscoveryResult
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ABBFimerPVIVSNRestCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data updates from VSN device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ABBFimerVSNRestClient,
        update_interval: timedelta,
        discovery_result: DiscoveryResult | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: VSN REST API client
            update_interval: How often to fetch data
            discovery_result: Optional discovery result from initial setup
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.vsn_model: str | None = discovery_result.vsn_model if discovery_result else None
        self.discovery_result: DiscoveryResult | None = discovery_result
        self.discovered_devices: list[DiscoveredDevice] = (
            discovery_result.devices if discovery_result else []
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from VSN device.

        Returns:
            Normalized data structure from the client

        Raises:
            UpdateFailed: If data fetch fails
        """
        try:
            # Ensure client is connected and model is detected
            if not self.vsn_model:
                self.vsn_model = await self.client.connect()
                _LOGGER.info("Connected to %s", self.vsn_model)

            # Fetch normalized data (includes mapping to HA entities)
            data = await self.client.get_normalized_data()

            _LOGGER.debug(
                "Successfully fetched data: %d devices",
                len(data.get("devices", {})),
            )

            return data

        except VSNAuthenticationError as err:
            # Authentication errors are likely configuration issues
            _LOGGER.error("Authentication failed: %s", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err

        except VSNConnectionError as err:
            # Connection errors might be temporary (device offline, network issues)
            _LOGGER.warning("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err

        except VSNClientError as err:
            # Generic client errors
            _LOGGER.error("Client error: %s", err)
            raise UpdateFailed(f"Client error: {err}") from err

        except Exception as err:
            # Catch-all for unexpected errors
            _LOGGER.exception("Unexpected error during data update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        _LOGGER.debug("Shutting down coordinator")
        await self.client.close()
