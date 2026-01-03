"""VSN REST API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

try:
    from .auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from .constants import ENDPOINT_LIVEDATA
    from .exceptions import VSNAuthenticationError, VSNConnectionError
    from .normalizer import VSNDataNormalizer
    from .utils import check_socket_connection
except ImportError:
    from auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from constants import ENDPOINT_LIVEDATA
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
        discovered_devices: list[Any] | None = None,
        requires_auth: bool = True,
    ):
        """Initialize the VSN client.

        Args:
            session: aiohttp client session
            base_url: Base URL of the VSN device (e.g., http://192.168.1.100)
            username: Username for authentication (default: "guest")
            password: Password for authentication (default: "")
            vsn_model: Optional VSN model ("VSN300" or "VSN700"). If None, will auto-detect.
            timeout: Request timeout in seconds
            discovered_devices: Optional list of discovered devices from discovery phase
            requires_auth: Whether device requires authentication (default: True)

        """
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.vsn_model = vsn_model
        self.timeout = timeout
        self._normalizer: VSNDataNormalizer | None = None
        self._discovered_devices = discovered_devices or []
        self.requires_auth = requires_auth

    async def connect(self) -> str:
        """Connect and detect VSN model.

        Returns:
            VSN model type ("VSN300" or "VSN700")

        Raises:
            VSNDetectionError: If detection fails
            VSNConnectionError: If connection fails

        """
        if not self.vsn_model:
            self.vsn_model, self.requires_auth = await detect_vsn_model(
                self.session,
                self.base_url,
                self.username,
                self.password,
                self.timeout,
            )

        # Initialize normalizer
        self._normalizer = VSNDataNormalizer(self.vsn_model)
        await self._normalizer.async_load()

        _LOGGER.info(
            "Connected to %s at %s (requires_auth=%s)",
            self.vsn_model,
            self.base_url,
            self.requires_auth,
        )
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
        url = f"{self.base_url}{ENDPOINT_LIVEDATA}"
        uri = ENDPOINT_LIVEDATA

        # Build authentication headers based on model (skip if no auth required)
        if not self.requires_auth:
            _LOGGER.debug("[Client] No authentication required")
            headers = {}
            auth_type = "None"
        elif self.vsn_model == "VSN300":
            # VSN300: Digest auth with X-Digest scheme
            # Format: Authorization: X-Digest username="...", realm="...", nonce="...", ...
            _LOGGER.debug("[Client] Using VSN300 digest authentication")
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
            auth_type = "X-Digest"
        else:  # VSN700
            # VSN700: Preemptive HTTP Basic auth
            _LOGGER.debug("[Client] Using VSN700 basic authentication")
            basic_auth = get_vsn700_basic_auth(self.username, self.password)
            headers = {"Authorization": f"Basic {basic_auth}"}
            auth_type = "Basic"

        _LOGGER.debug(
            "[Client] Fetching livedata: url=%s, auth=%s, timeout=%ds",
            url,
            auth_type,
            self.timeout,
        )

        try:
            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                _LOGGER.debug(
                    "[Client] Response: status=%d, headers=%s",
                    response.status,
                    dict(response.headers),
                )

                if response.status == 200:
                    data = await response.json()
                    # Count total points across all devices
                    total_points = sum(
                        len(device_data.get("points", [])) for device_data in data.values()
                    )
                    _LOGGER.debug(
                        "[Client] %s livedata fetched successfully: %d devices, %d total points",
                        self.vsn_model,
                        len(data),
                        total_points,
                    )
                    # Log detailed point breakdown if debug level
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        for device_id, device_data in data.items():
                            point_count = len(device_data.get("points", []))
                            _LOGGER.debug(
                                "[Client]   Device %s: %d points",
                                device_id,
                                point_count,
                            )
                    return data

                if response.status == 401:
                    _LOGGER.error(
                        "[Client] Authentication failed (HTTP 401). "
                        "Headers: %s. Check username/password for %s authentication.",
                        dict(response.headers),
                        self.vsn_model,
                    )
                    raise VSNAuthenticationError(
                        f"Authentication failed: HTTP {response.status}. "
                        "Check username and password. Enable debug logging for details."
                    )

                # Log error response details
                _LOGGER.error(
                    "[Client] Livedata request failed: HTTP %d. Headers: %s",
                    response.status,
                    dict(response.headers),
                )
                raise VSNConnectionError(f"Livedata request failed: HTTP {response.status}")
        except aiohttp.ClientError as err:
            _LOGGER.debug(
                "[Client] Connection error: %s (type=%s)",
                err,
                type(err).__name__,
            )
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

        # Inject device_type from discovered devices into raw_data before normalization
        # This is needed because the datalogger doesn't appear in livedata with device_type
        if self._discovered_devices:
            for discovered_device in self._discovered_devices:
                # Match by device_id (with or without formatting)
                for device_id, device_data in raw_data.items():
                    # Check both raw and cleaned versions of device IDs
                    if device_id in (
                        discovered_device.device_id,
                        discovered_device.raw_device_id,
                    ):
                        # Inject device_type from discovery
                        if discovered_device.device_type:
                            device_data["device_type"] = discovered_device.device_type
                            _LOGGER.debug(
                                "Injected device_type '%s' for device %s from discovery",
                                discovered_device.device_type,
                                device_id,
                            )

        normalized_data = self._normalizer.normalize(raw_data)

        # Log normalization statistics
        if _LOGGER.isEnabledFor(logging.DEBUG):
            normalized_devices = normalized_data.get("devices", {})
            total_normalized = sum(
                len(device_data.get("points", {})) for device_data in normalized_devices.values()
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
