"""Coordinator."""
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN

class ABBFimerPVIVSNRestCoordinator(DataUpdateCoordinator):
    """Coordinator."""

    def __init__(self, hass, config_entry, client):
        super().__init__(hass, None, name=DOMAIN,
                         update_interval=timedelta(seconds=60))
        self.client = client

    async def _async_update_data(self):
        return await self.client.get_all_data()
