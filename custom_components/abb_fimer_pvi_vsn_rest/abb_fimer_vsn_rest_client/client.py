"""VSN REST API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
from .constants import ENDPOINT_LIVEDATA
from .exceptions import VSNAuthenticationError, VSNConnectionError
from .normalizer import VSNDataNormalizer
from .utils import check_socket_connection

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
        # Maps livedata device keys to device_type for injection before normalization.
        # Built lazily on first poll from _discovered_devices, invalidated on update.
        self._device_type_map: dict[str, str] | None = None

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

    def update_discovered_devices(self, devices: list[Any]) -> None:
        """Update the discovered devices list and invalidate cached mappings.

        Called by the coordinator after re-discovery to keep client in sync.
        """
        self._discovered_devices = devices
        self._device_type_map = None  # Force rebuild on next data fetch
        _LOGGER.debug(
            "Updated discovered devices: %d devices",
            len(devices),
        )

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

        # Inject device_type into raw livedata before normalization.
        # The API may not include device_type for all devices (e.g., datalogger).
        # The map is built lazily from discovered devices and invalidated on re-discovery.
        self._ensure_device_type_map()
        self._inject_device_types(raw_data)

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

    def _ensure_device_type_map(self) -> None:
        """Build the device_type injection map if not already cached.

        Maps all possible livedata keys (device_id, raw_device_id, livedata_device_id)
        to the corresponding device_type from discovery. This allows fast O(1) lookup
        during injection instead of iterating discovered devices on every poll.
        """
        if self._device_type_map is not None or not self._discovered_devices:
            return

        self._device_type_map = {}
        for device in self._discovered_devices:
            if not device.device_type:
                continue
            for key in (device.device_id, device.raw_device_id, device.livedata_device_id):
                if key:
                    self._device_type_map[key] = device.device_type

        _LOGGER.debug("Built device_type injection map: %s", self._device_type_map)

    def _inject_device_types(self, raw_data: dict[str, Any]) -> None:
        """Inject device_type from discovery into raw livedata entries.

        Some devices (e.g., datalogger) don't include device_type in the API response.
        This ensures all devices have consistent device_type before normalization.
        """
        if not self._device_type_map:
            return
        for device_id, device_data in raw_data.items():
            device_type = self._device_type_map.get(device_id)
            if device_type:
                device_data["device_type"] = device_type

    async def close(self) -> None:
        """Close the client (session management is external)."""
        _LOGGER.debug("VSN client closed")
        self._normalizer = None
