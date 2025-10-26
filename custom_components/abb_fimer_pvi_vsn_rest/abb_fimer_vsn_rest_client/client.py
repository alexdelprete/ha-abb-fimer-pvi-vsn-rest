"""VSN REST API client."""
import asyncio
import logging
from typing import Any
import aiohttp
from .auth import detect_vsn_model
from .exceptions import VSNConnectionError

_LOGGER = logging.getLogger(__name__)

class ABBFimerVSNRestClient:
    """VSN REST client."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str,
                 username: str, password: str, vsn_model: str | None = None):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.vsn_model = vsn_model

    async def connect(self) -> str:
        """Connect and detect VSN model."""
        if not self.vsn_model:
            self.vsn_model = await detect_vsn_model(self.session, self.base_url)
        return self.vsn_model

    async def get_all_data(self) -> dict[str, Any]:
        """Fetch all data."""
        # TODO: Implement data fetching
        return {}
