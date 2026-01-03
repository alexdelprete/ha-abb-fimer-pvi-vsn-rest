"""Discovery functionality for VSN devices.

This module provides device discovery for VSN300 and VSN700 dataloggers,
gathering information about the logger and all connected devices (inverters,
meters, batteries) from the status and livedata endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import aiohttp

try:
    from .auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from .constants import ENDPOINT_LIVEDATA, ENDPOINT_STATUS
    from .exceptions import VSNConnectionError
    from .utils import check_socket_connection
except ImportError:
    from auth import detect_vsn_model, get_vsn300_digest_header, get_vsn700_basic_auth
    from constants import ENDPOINT_LIVEDATA, ENDPOINT_STATUS
    from exceptions import VSNConnectionError
    from utils import check_socket_connection

_LOGGER = logging.getLogger(__name__)


@dataclass
class DiscoveredDevice:
    """Represents a discovered device (inverter, meter, battery, datalogger)."""

    device_id: str  # Clean ID (S/N or MAC without colons)
    raw_device_id: str  # Original ID from API (with colons if MAC)
    device_type: str  # inverter_3phases, meter, battery, etc.
    device_model: str | None  # PVI-10.0-OUTD, REACT2-5.0-TL, etc.
    manufacturer: str | None  # Power-One, ABB, FIMER
    firmware_version: str | None  # C008, B185, etc. (inverter firmware)
    hardware_version: str | None  # Hardware version if available
    is_datalogger: bool  # True if this is the datalogger device


@dataclass
class DiscoveryResult:
    """Complete discovery result from VSN device."""

    vsn_model: str  # VSN300 or VSN700
    requires_auth: bool  # Whether device requires authentication
    logger_sn: str  # Logger serial number
    logger_model: str | None  # WIFI LOGGER CARD, etc.
    firmware_version: str | None  # 1.9.2, etc.
    hostname: str | None  # ABB-077909-3G82-3112.local
    devices: list[DiscoveredDevice]  # All discovered devices
    status_data: dict[str, Any]  # Full status response

    def get_title(self) -> str:
        """Generate a suitable title for config entry."""
        return f"{self.vsn_model} ({self.logger_sn})"

    def get_main_inverter(self) -> DiscoveredDevice | None:
        """Get the main inverter device (first inverter found)."""
        for device in self.devices:
            if device.device_type.startswith("inverter"):
                return device
        return None


async def discover_vsn_device(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str = "guest",
    password: str = "",
    timeout: int = 10,
) -> DiscoveryResult:
    """Discover VSN device and all connected devices.

    This function:
    1. Detects VSN model (VSN300 or VSN700)
    2. Fetches status data
    3. Fetches livedata
    4. Extracts all device information
    5. Returns comprehensive discovery result

    Args:
        session: aiohttp ClientSession
        base_url: Base URL of VSN device (e.g., http://192.168.1.100)
        username: Authentication username (default: guest)
        password: Authentication password (default: empty)
        timeout: Request timeout in seconds

    Returns:
        DiscoveryResult with all discovered information

    Raises:
        VSNConnectionError: If connection fails
        VSNAuthenticationError: If authentication fails

    """
    _LOGGER.debug("Starting VSN device discovery at %s", base_url)

    # Step 1: Detect VSN model and auth requirement
    vsn_model, requires_auth = await detect_vsn_model(
        session, base_url, username, password, timeout
    )
    _LOGGER.info(
        "Detected VSN model: %s (requires_auth=%s)", vsn_model, requires_auth
    )

    # Step 2: Fetch status data
    status_data = await _fetch_status(
        session, base_url, vsn_model, username, password, timeout, requires_auth
    )

    # Step 3: Fetch livedata
    livedata = await _fetch_livedata(
        session, base_url, vsn_model, username, password, timeout, requires_auth
    )

    # Step 4: Extract logger information from status
    logger_info = _extract_logger_info(status_data, vsn_model)

    # Step 5: Extract all devices from livedata
    devices = _extract_devices(livedata, vsn_model, status_data)

    _LOGGER.info(
        "Discovery complete: %s with %d devices",
        vsn_model,
        len(devices),
    )

    return DiscoveryResult(
        vsn_model=vsn_model,
        requires_auth=requires_auth,
        logger_sn=logger_info["logger_sn"],
        logger_model=logger_info.get("logger_model"),
        firmware_version=logger_info.get("firmware_version"),
        hostname=logger_info.get("hostname"),
        devices=devices,
        status_data=status_data,
    )


async def _fetch_status(
    session: aiohttp.ClientSession,
    base_url: str,
    vsn_model: str,
    username: str,
    password: str,
    timeout: int,
    requires_auth: bool = True,
) -> dict[str, Any]:
    """Fetch status endpoint.

    Args:
        session: aiohttp ClientSession
        base_url: Base URL of VSN device
        vsn_model: VSN300 or VSN700
        username: Authentication username
        password: Authentication password
        timeout: Request timeout in seconds
        requires_auth: Whether authentication is required

    Returns:
        Status data dictionary

    Raises:
        VSNConnectionError: If fetch fails

    """
    # Check socket connection before HTTP request
    await check_socket_connection(base_url, timeout=5)

    status_url = f"{base_url}{ENDPOINT_STATUS}"
    uri = ENDPOINT_STATUS

    # Build authentication headers based on model (skip if no auth required)
    if not requires_auth:
        _LOGGER.debug("[Discovery Status] No authentication required")
        headers = {}
        auth_type = "None"
    elif vsn_model == "VSN300":
        _LOGGER.debug("[Discovery Status] Using VSN300 digest authentication")
        digest_value = await get_vsn300_digest_header(
            session, base_url, username, password, uri, "GET", timeout
        )
        headers = {"Authorization": f"X-Digest {digest_value}"}
        auth_type = "X-Digest"
    else:  # VSN700
        _LOGGER.debug("[Discovery Status] Using VSN700 basic authentication")
        basic_auth = get_vsn700_basic_auth(username, password)
        headers = {"Authorization": f"Basic {basic_auth}"}
        auth_type = "Basic"

    _LOGGER.debug(
        "[Discovery Status] Fetching status: url=%s, auth=%s, timeout=%ds",
        status_url,
        auth_type,
        timeout,
    )

    try:
        async with session.get(
            status_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            _LOGGER.debug(
                "[Discovery Status] Response: status=%d, headers=%s",
                response.status,
                dict(response.headers),
            )

            if response.status == 200:
                data = await response.json()
                _LOGGER.debug(
                    "[Discovery Status] Successfully fetched status data (%d bytes)",
                    len(str(data)),
                )
                return data

            # Log error response details
            _LOGGER.error(
                "[Discovery Status] HTTP %d error. Headers: %s",
                response.status,
                dict(response.headers),
            )
            raise VSNConnectionError(f"Failed to fetch status: HTTP {response.status}")
    except aiohttp.ClientError as err:
        _LOGGER.debug(
            "[Discovery Status] Connection error: %s (type=%s)",
            err,
            type(err).__name__,
        )
        raise VSNConnectionError(f"Failed to fetch status: {err}") from err


async def _fetch_livedata(
    session: aiohttp.ClientSession,
    base_url: str,
    vsn_model: str,
    username: str,
    password: str,
    timeout: int,
    requires_auth: bool = True,
) -> dict[str, Any]:
    """Fetch livedata endpoint.

    Args:
        session: aiohttp ClientSession
        base_url: Base URL of VSN device
        vsn_model: VSN300 or VSN700
        username: Authentication username
        password: Authentication password
        timeout: Request timeout in seconds
        requires_auth: Whether authentication is required

    Returns:
        Livedata dictionary

    Raises:
        VSNConnectionError: If fetch fails

    """
    # Check socket connection before HTTP request
    await check_socket_connection(base_url, timeout=5)

    livedata_url = f"{base_url}{ENDPOINT_LIVEDATA}"
    uri = ENDPOINT_LIVEDATA

    # Build authentication headers based on model (skip if no auth required)
    if not requires_auth:
        _LOGGER.debug("[Discovery Livedata] No authentication required")
        headers = {}
        auth_type = "None"
    elif vsn_model == "VSN300":
        _LOGGER.debug("[Discovery Livedata] Using VSN300 digest authentication")
        digest_value = await get_vsn300_digest_header(
            session, base_url, username, password, uri, "GET", timeout
        )
        headers = {"Authorization": f"X-Digest {digest_value}"}
        auth_type = "X-Digest"
    else:  # VSN700
        _LOGGER.debug("[Discovery Livedata] Using VSN700 basic authentication")
        basic_auth = get_vsn700_basic_auth(username, password)
        headers = {"Authorization": f"Basic {basic_auth}"}
        auth_type = "Basic"

    _LOGGER.debug(
        "[Discovery Livedata] Fetching livedata: url=%s, auth=%s, timeout=%ds",
        livedata_url,
        auth_type,
        timeout,
    )

    try:
        async with session.get(
            livedata_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            _LOGGER.debug(
                "[Discovery Livedata] Response: status=%d, headers=%s",
                response.status,
                dict(response.headers),
            )

            if response.status == 200:
                data = await response.json()
                _LOGGER.debug(
                    "[Discovery Livedata] Successfully fetched livedata: %d devices, %d bytes",
                    len(data),
                    len(str(data)),
                )
                return data

            # Log error response details
            _LOGGER.error(
                "[Discovery Livedata] HTTP %d error. Headers: %s",
                response.status,
                dict(response.headers),
            )
            raise VSNConnectionError(
                f"Failed to fetch livedata: HTTP {response.status}"
            )
    except aiohttp.ClientError as err:
        _LOGGER.debug(
            "[Discovery Livedata] Connection error: %s (type=%s)",
            err,
            type(err).__name__,
        )
        raise VSNConnectionError(f"Failed to fetch livedata: {err}") from err


def _extract_logger_info(status_data: dict[str, Any], vsn_model: str) -> dict[str, Any]:
    """Extract logger information from status data.

    Args:
        status_data: Status response data
        vsn_model: VSN300 or VSN700

    Returns:
        Dictionary with logger information

    """
    keys = status_data.get("keys", {})

    logger_info = {
        "logger_sn": keys.get("logger.sn", {}).get("value", "Unknown"),
        "logger_model": keys.get("logger.board_model", {}).get("value"),
        "firmware_version": keys.get("fw.release_number", {}).get("value"),
        "hostname": keys.get("logger.hostname", {}).get("value"),
    }

    # For VSN700, logger S/N might be in loggerId field (MAC address)
    if logger_info["logger_sn"] == "Unknown" and vsn_model == "VSN700":
        logger_info["logger_sn"] = keys.get("logger.loggerId", {}).get(
            "value", "Unknown"
        )

    return logger_info


def _extract_devices(
    livedata: dict[str, Any], vsn_model: str, status_data: dict[str, Any]
) -> list[DiscoveredDevice]:
    """Extract all devices from livedata.

    Args:
        livedata: Livedata response
        vsn_model: VSN300 or VSN700
        status_data: Status data for VSN300 inverter model

    Returns:
        List of discovered devices

    """
    devices = []

    # Create synthetic datalogger device from status.json
    # The datalogger doesn't appear in livedata, only in feeds.json
    keys = status_data.get("keys", {})
    logger_sn = keys.get("logger.sn", {}).get("value", "Unknown")

    # For VSN700, logger S/N might be in loggerId field (MAC address)
    if logger_sn == "Unknown" and vsn_model == "VSN700":
        logger_sn = keys.get("logger.loggerId", {}).get("value", "Unknown")

    # Clean logger ID (remove colons if MAC)
    logger_id = logger_sn.replace(":", "") if ":" in logger_sn else logger_sn

    # Create datalogger device
    datalogger_device = DiscoveredDevice(
        device_id=logger_id,
        raw_device_id=logger_sn,
        device_type="datalogger",
        device_model=vsn_model,  # "VSN300" or "VSN700"
        manufacturer="ABB" if vsn_model == "VSN300" else "FIMER",
        firmware_version=keys.get("fw.release_number", {}).get("value"),
        hardware_version=None,
        is_datalogger=True,
    )
    devices.append(datalogger_device)

    _LOGGER.debug(
        "Created synthetic datalogger device: %s (%s) - Model: %s, FW: %s",
        logger_id,
        vsn_model,
        vsn_model,
        datalogger_device.firmware_version or "Unknown",
    )

    # Process all devices from livedata (inverters, meters, batteries)
    for raw_device_id, device_data in livedata.items():
        # Determine if this is a datalogger (MAC address pattern with colons)
        is_datalogger = ":" in raw_device_id

        # Get clean device ID
        device_id = raw_device_id
        if is_datalogger:
            # Check for "sn" point (VSN300 datalogger has this)
            sn_found = False
            for point in device_data.get("points", []):
                if point.get("name") == "sn":
                    device_id = point["value"]
                    sn_found = True
                    _LOGGER.debug(
                        "Using logger S/N '%s' instead of MAC '%s'",
                        device_id,
                        raw_device_id,
                    )
                    break

            if not sn_found:
                # VSN700: Strip colons from MAC (no underscores!)
                device_id = raw_device_id.replace(":", "")
                _LOGGER.debug(
                    "Using clean MAC '%s' instead of '%s'",
                    device_id,
                    raw_device_id,
                )

        # Get device type
        device_type = device_data.get("device_type", "unknown")

        # Get device model
        device_model = None
        if is_datalogger:
            # Datalogger: Use VSN model as device model
            device_model = vsn_model  # "VSN300" or "VSN700"
            device_type = "datalogger"  # Override "unknown" from livedata
        elif vsn_model == "VSN700":
            # VSN700: Model in livedata at device level
            device_model = device_data.get("device_model")
        elif vsn_model == "VSN300":
            # VSN300: Model in status for inverter
            device_model = (
                status_data.get("keys", {}).get("device.modelDesc", {}).get("value")
            )

        # Extract useful points: manufacturer, firmware version, hardware version
        manufacturer = None
        firmware_version = None
        hardware_version = None

        for point in device_data.get("points", []):
            point_name = point.get("name")
            if point_name == "C_Mn":
                manufacturer = point.get("value")
            elif point_name == "C_Vr":
                # SunSpec firmware version (e.g., "C008")
                firmware_version = point.get("value")
            elif point_name == "fw_ver":
                # Datalogger firmware version (e.g., "1.9.2")
                firmware_version = point.get("value")

        devices.append(
            DiscoveredDevice(
                device_id=device_id,
                raw_device_id=raw_device_id,
                device_type=device_type,
                device_model=device_model,
                manufacturer=manufacturer,
                firmware_version=firmware_version,
                hardware_version=hardware_version,
                is_datalogger=is_datalogger,
            )
        )

        _LOGGER.debug(
            "Discovered device: %s (%s) - Model: %s, Manufacturer: %s, FW: %s",
            device_id,
            device_type,
            device_model or "Unknown",
            manufacturer or "Unknown",
            firmware_version or "Unknown",
        )

    return devices
