"""VSN REST API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

try:
    from .auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from .exceptions import VSNAuthenticationError, VSNConnectionError
    from .normalizer import VSNDataNormalizer
    from .utils import check_socket_connection
except ImportError:
    from auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from exceptions import VSNAuthenticationError, VSNConnectionError
    from normalizer import VSNDataNormalizer
    from utils import check_socket_connection

_LOGGER = logging.getLogger(__name__)


class ABBFimerVSNRestClient:
    """VSN REST API client with automatic VSN300/VSN700 detection."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str = "guest",
        password: str = "",
        vsn_model: str | None = None,
        timeout: int = 10,
    ):
        """Initialize the VSN client.

        Args:
            session: aiohttp client session
            base_url: Base URL of the VSN device (e.g., http://192.168.1.100)
            username: Username for authentication (default: "guest")
            password: Password for authentication (default: "")
            vsn_model: Optional VSN model ("VSN300" or "VSN700"). If None, will auto-detect.
            timeout: Request timeout in seconds

        """
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.vsn_model = vsn_model
        self.timeout = timeout
        self._normalizer: VSNDataNormalizer | None = None

    async def connect(self) -> str:
        """Connect and detect VSN model.

        Returns:
            VSN model type ("VSN300" or "VSN700")

        Raises:
            VSNDetectionError: If detection fails
            VSNConnectionError: If connection fails

        """
        if not self.vsn_model:
            self.vsn_model = await detect_vsn_model(
                self.session,
                self.base_url,
                self.username,
                self.password,
                self.timeout,
            )

        # Initialize normalizer
        self._normalizer = VSNDataNormalizer(self.vsn_model)
        await self._normalizer.async_load()

        _LOGGER.info("Connected to %s at %s", self.vsn_model, self.base_url)
        return self.vsn_model

    async def get_livedata(self) -> dict[str, Any]:
        """Fetch livedata from VSN device.

        Both VSN300 and VSN700 use /v1/livedata endpoint.

        Returns:
            Raw livedata response from VSN

        Raises:
            VSNConnectionError: If request fails

        """
        if not self.vsn_model:
            await self.connect()

        # Check socket connection before HTTP request
        await check_socket_connection(self.base_url, timeout=5)

        # Both models use the same endpoint
        url = f"{self.base_url}/v1/livedata"
        uri = "/v1/livedata"

        # Build authentication headers based on model
        if self.vsn_model == "VSN300":
            # VSN300: Digest auth with X-Digest scheme
            # Format: Authorization: X-Digest username="...", realm="...", nonce="...", ...
            digest_value = await get_vsn300_digest_header(
                self.session,
                self.base_url,
                self.username,
                self.password,
                uri,
                "GET",
                self.timeout,
            )
            headers = {"Authorization": f"X-Digest {digest_value}"}
        else:  # VSN700
            # VSN700: Preemptive HTTP Basic auth
            basic_auth = get_vsn700_basic_auth(self.username, self.password)
            headers = {"Authorization": f"Basic {basic_auth}"}

        try:
            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Count total points across all devices
                    total_points = sum(
                        len(device_data.get("points", []))
                        for device_data in data.values()
                    )
                    _LOGGER.debug(
                        "%s livedata fetched: %d devices, %d total points",
                        self.vsn_model,
                        len(data),
                        total_points,
                    )
                    # Log detailed point breakdown if debug level
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        for device_id, device_data in data.items():
                            point_count = len(device_data.get("points", []))
                            _LOGGER.debug(
                                "  Device %s: %d points",
                                device_id,
                                point_count,
                            )
                    return data
                if response.status == 401:
                    raise VSNAuthenticationError(
                        f"Authentication failed: HTTP {response.status}. "
                        "Check username and password."
                    )
                raise VSNConnectionError(
                    f"Livedata request failed: HTTP {response.status}"
                )
        except aiohttp.ClientError as err:
            raise VSNConnectionError(f"Livedata request error: {err}") from err

    async def get_normalized_data(self) -> dict[str, Any]:
        """Fetch and normalize livedata.

        Returns:
            Normalized data using the vsn-sunspec-point-mapping.xlsx

        Raises:
            VSNConnectionError: If request fails

        """
        if not self._normalizer:
            await self.connect()

        # Type narrowing: _normalizer is guaranteed to be set after connect()
        if not self._normalizer:
            raise VSNConnectionError("Normalizer not initialized after connect()")

        raw_data = await self.get_livedata()
        normalized_data = self._normalizer.normalize(raw_data)

        # Log normalization statistics
        if _LOGGER.isEnabledFor(logging.DEBUG):
            normalized_devices = normalized_data.get("devices", {})
            total_normalized = sum(
                len(device_data.get("points", {}))
                for device_data in normalized_devices.values()
            )
            _LOGGER.debug(
                "Normalization complete: %d devices, %d normalized points",
                len(normalized_devices),
                total_normalized,
            )
            for device_id, device_data in normalized_devices.items():
                point_count = len(device_data.get("points", {}))
                device_type = device_data.get("device_type", "unknown")
                _LOGGER.debug(
                    "  Device %s (%s): %d points",
                    device_id,
                    device_type,
                    point_count,
                )

        return normalized_data

    async def close(self) -> None:
        """Close the client (session management is external)."""
        _LOGGER.debug("VSN client closed")
        self._normalizer = None
