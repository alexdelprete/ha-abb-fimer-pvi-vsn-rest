#!/usr/bin/env python3
"""Self-contained VSN REST client for testing VSN300/VSN700 devices.

This script has no dependencies except Python standard library and aiohttp.
It can be sent to users for testing their VSN devices without installing
the full Home Assistant integration.

Features:
- Auto-detects VSN300 vs VSN700
- Tests all 3 endpoints (/v1/status, /v1/livedata, /v1/feeds)
- Normalizes data using online mapping (no local files needed)
- Creates both raw and normalized JSON outputs

Usage:
    python vsn_rest_client.py <host> [--username USER] [--password PASS] [--timeout SEC]

Example:
    python vsn_rest_client.py 192.168.1.100
    python vsn_rest_client.py 192.168.1.100 --username admin --password mypassword
    python vsn_rest_client.py abb-vsn300.local -u guest -p "" -t 15

Requirements:
    - Python 3.9+
    - aiohttp (install with: pip install aiohttp)

"""

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp is required. Install it with: pip install aiohttp")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)

# URL to the mapping JSON on GitHub (integration runtime location)
MAPPING_URL = "https://raw.githubusercontent.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/master/custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/data/vsn-sunspec-point-mapping.json"


# ============================================================================
# VSN Authentication Module
# ============================================================================


def calculate_digest_response(
    username: str,
    password: str,
    realm: str,
    nonce: str,
    method: str,
    uri: str,
    qop: str | None = None,
    nc: str | None = None,
    cnonce: str | None = None,
) -> str:
    """Calculate HTTP Digest authentication response."""
    # Calculate HA1 = MD5(username:realm:password)
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()

    # Calculate HA2 = MD5(method:uri)
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

    # Calculate response
    if qop and nc and cnonce:
        response_str = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        response_str = f"{ha1}:{nonce}:{ha2}"

    return hashlib.md5(response_str.encode()).hexdigest()


def parse_digest_challenge(www_authenticate: str) -> dict[str, str]:
    """Parse WWW-Authenticate digest challenge header."""
    challenge = re.sub(
        r"^(Digest|X-Digest)\s+", "", www_authenticate, flags=re.IGNORECASE
    )

    params = {}
    for match in re.finditer(r'(\w+)=(?:"([^"]+)"|([^,\s]+))', challenge):
        key = match.group(1)
        value = match.group(2) or match.group(3)
        params[key] = value

    return params


def build_digest_header(
    username: str,
    password: str,
    challenge_params: dict[str, str],
    method: str,
    uri: str,
) -> str:
    """Build X-Digest authentication header value."""
    realm = challenge_params.get("realm", "")
    nonce = challenge_params.get("nonce", "")
    qop = challenge_params.get("qop")
    opaque = challenge_params.get("opaque")

    if qop:
        nc = "00000001"
        # Generate cnonce like stdlib: H(nonce:time:random)
        cnonce_input = f"{nonce}:{time.time()}:{os.urandom(8).hex()}"
        cnonce = hashlib.md5(cnonce_input.encode()).hexdigest()[:16]
        response = calculate_digest_response(
            username, password, realm, nonce, method, uri, qop, nc, cnonce
        )

        # Match stdlib format: response before algorithm/qop/nc/cnonce, qop without quotes
        auth_parts = [
            f'username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
            'algorithm="MD5"',
            f"qop={qop}",
            f"nc={nc}",
            f'cnonce="{cnonce}"',
        ]
    else:
        response = calculate_digest_response(
            username, password, realm, nonce, method, uri
        )

        auth_parts = [
            f'username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
        ]

    if opaque:
        auth_parts.append(f'opaque="{opaque}"')

    return ", ".join(auth_parts)


async def get_vsn300_digest_header(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    password: str,
    uri: str = "/v1/livedata",
    method: str = "GET",
    timeout: int = 10,
) -> str:
    """Get VSN300 X-Digest authentication header."""
    url = f"{base_url.rstrip('/')}{uri}"

    try:
        async with session.request(
            method,
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "")

                if not www_authenticate or "digest" not in www_authenticate.lower():
                    raise Exception("VSN300 challenge missing or not digest-based")

                challenge_params = parse_digest_challenge(www_authenticate)
                return build_digest_header(
                    username, password, challenge_params, method, uri
                )

            raise Exception(f"Expected 401 challenge, got {response.status}")
    except aiohttp.ClientError as err:
        raise Exception(f"VSN300 challenge request failed: {err}") from err


def get_vsn700_basic_auth(username: str, password: str) -> str:
    """Get VSN700 HTTP Basic authentication header value."""
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode("utf-8")).decode("utf-8")


def _detect_model_from_status(status_data: dict) -> str:
    """Detect VSN model from status data structure.

    VSN300 status has:
    - keys.logger.sn (serial number like "111033-3N16-1421")
    - keys.logger.board_model = "WIFI LOGGER CARD"
    - Many keys including device info, firmware, etc.

    VSN700 status has:
    - keys.logger.loggerId (MAC address like "ac:1f:0f:b0:50:b5")
    - Minimal keys (usually just loggerId)

    Args:
        status_data: Parsed status JSON response

    Returns:
        "VSN300" or "VSN700"

    Raises:
        Exception: If model cannot be determined

    """
    keys = status_data.get("keys", {})

    # Check for VSN300 indicators
    logger_sn = keys.get("logger.sn", {}).get("value", "")
    board_model = keys.get("logger.board_model", {}).get("value", "")

    if board_model == "WIFI LOGGER CARD":
        _LOGGER.info(
            "[VSN Detection] Detected VSN300 (board_model='WIFI LOGGER CARD')"
        )
        return "VSN300"

    # VSN300 serial number format: XXXXXX-XXXX-XXXX (digits and dashes)
    if logger_sn and re.match(r"^\d{6}-\w{4}-\d{4}$", logger_sn):
        _LOGGER.info(
            "[VSN Detection] Detected VSN300 (serial number format: %s)",
            logger_sn,
        )
        return "VSN300"

    # Check for VSN700 indicators
    logger_id = keys.get("logger.loggerId", {}).get("value", "")

    # VSN700 loggerId is a MAC address format: xx:xx:xx:xx:xx:xx
    if logger_id and re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", logger_id):
        _LOGGER.info(
            "[VSN Detection] Detected VSN700 (MAC address format: %s)",
            logger_id,
        )
        return "VSN700"

    # Fallback: VSN300 typically has many more keys than VSN700
    if len(keys) > 10:
        _LOGGER.info(
            "[VSN Detection] Detected VSN300 (rich status data with %d keys)",
            len(keys),
        )
        return "VSN300"

    if len(keys) <= 3:
        _LOGGER.info(
            "[VSN Detection] Detected VSN700 (minimal status data with %d keys)",
            len(keys),
        )
        return "VSN700"

    # Cannot determine model
    _LOGGER.error(
        "[VSN Detection] Could not determine VSN model from status data. "
        "Keys found: %s",
        list(keys.keys()),
    )
    raise Exception(
        "Could not determine VSN model from status data. "
        "Enable debug logging for details."
    )


async def detect_vsn_model(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    password: str,
    timeout: int = 10,
) -> tuple[str, bool]:
    """Detect VSN model by examining response and data structure.

    Detection methods (in order of preference):
    1. If 401: Examine WWW-Authenticate header (digest = VSN300, basic = VSN700)
    2. If 200: Analyze status data structure to determine model (no auth required)

    This approach supports:
    - VSN300 (digest authentication with WWW-Authenticate header)
    - VSN700 (preemptive Basic auth, may or may not send WWW-Authenticate header)
    - Devices without authentication (HTTP 200 response)

    Args:
        session: aiohttp client session
        base_url: Base URL of VSN device
        username: Username for authentication
        password: Password for authentication
        timeout: Request timeout in seconds

    Returns:
        Tuple of (vsn_model, requires_auth):
        - vsn_model: "VSN300" or "VSN700"
        - requires_auth: True if authentication is required, False if device is open

    Raises:
        Exception: If detection fails or device is not compatible

    """
    base_url = base_url.rstrip("/")
    detection_url = f"{base_url}/v1/status"

    _LOGGER.debug(
        "[VSN Detection] Making unauthenticated request to %s (timeout=%ds)",
        detection_url,
        timeout,
    )

    try:
        # Make unauthenticated request to /v1/status to trigger 401
        async with session.get(
            detection_url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            _LOGGER.debug(
                "[VSN Detection] Response: status=%d, headers=%s",
                response.status,
                dict(response.headers),
            )

            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "").lower()
                www_authenticate_raw = response.headers.get("WWW-Authenticate", "")

                _LOGGER.debug(
                    "[VSN Detection] WWW-Authenticate: %s",
                    repr(www_authenticate_raw)
                    if www_authenticate_raw
                    else "NOT PRESENT",
                )

                # Check for digest authentication (VSN300) - unique identifier
                if www_authenticate and (
                    "x-digest" in www_authenticate or "digest" in www_authenticate
                ):
                    _LOGGER.info(
                        "Detected VSN300 (digest auth in WWW-Authenticate: %s)",
                        www_authenticate_raw,
                    )
                    return ("VSN300", True)  # Auth required

                # Not VSN300 - try preemptive Basic authentication
                # VSN700 uses preemptive Basic auth (may or may not send WWW-Authenticate header)
                _LOGGER.debug(
                    "[VSN Detection] Not VSN300. Attempting preemptive Basic authentication for VSN700."
                )

                try:
                    basic_auth = get_vsn700_basic_auth(username, password)
                    auth_headers = {"Authorization": f"Basic {basic_auth}"}

                    _LOGGER.debug(
                        "[VSN Detection] Sending preemptive Basic auth to %s",
                        detection_url,
                    )

                    async with session.get(
                        detection_url,
                        headers=auth_headers,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as auth_response:
                        _LOGGER.debug(
                            "[VSN Detection] Preemptive auth response: status=%d",
                            auth_response.status,
                        )

                        # Check if preemptive Basic auth succeeded
                        if auth_response.status in (200, 204):
                            _LOGGER.info(
                                "Detected VSN700 (preemptive Basic authentication)"
                            )
                            return ("VSN700", True)  # Auth required

                        # Preemptive auth failed
                        _LOGGER.error(
                            "[VSN Detection] Preemptive Basic auth failed with status %d. "
                            "Device is not compatible.",
                            auth_response.status,
                        )
                        raise Exception(
                            f"Device authentication failed. Not VSN300/VSN700 compatible. "
                            f"Preemptive Basic auth returned {auth_response.status}."
                        )

                except aiohttp.ClientError as auth_err:
                    _LOGGER.error(
                        "[VSN Detection] Preemptive Basic auth connection error: %s",
                        auth_err,
                    )
                    raise Exception(
                        f"Device authentication connection failed: {auth_err}"
                    ) from auth_err

            elif response.status == 200:
                # No authentication required - detect model from status data structure
                _LOGGER.info(
                    "[VSN Detection] No authentication required (HTTP 200). "
                    "Detecting model from status data structure."
                )

                try:
                    status_data = await response.json()
                    model = _detect_model_from_status(status_data)
                except Exception as parse_err:
                    _LOGGER.error(
                        "[VSN Detection] Failed to parse status response: %s",
                        parse_err,
                    )
                    raise Exception(
                        f"Failed to parse status response: {parse_err}"
                    ) from parse_err
                else:
                    return (model, False)  # No auth required

            # Got unexpected response status
            _LOGGER.error(
                "[VSN Detection] Unexpected response status %d. Headers: %s",
                response.status,
                dict(response.headers),
            )
            raise Exception(
                f"Unexpected response status {response.status} during detection"
            )
    except aiohttp.ClientError as err:
        raise Exception(f"Device detection connection error: {err}") from err


# ============================================================================
# VSN REST Client
# ============================================================================


async def fetch_endpoint(
    session: aiohttp.ClientSession,
    base_url: str,
    endpoint: str,
    vsn_model: str,
    username: str = "guest",
    password: str = "",
    timeout: int = 10,
    requires_auth: bool = True,
) -> dict:
    """Fetch data from a VSN endpoint.

    Args:
        session: aiohttp client session
        base_url: Base URL of VSN device
        endpoint: API endpoint (e.g., /v1/status)
        vsn_model: "VSN300" or "VSN700"
        username: Authentication username
        password: Authentication password
        timeout: Request timeout in seconds
        requires_auth: Whether authentication is required

    Returns:
        JSON response data

    """
    url = f"{base_url.rstrip('/')}{endpoint}"

    # Build auth header based on model (skip if no auth required)
    if not requires_auth:
        _LOGGER.debug("[Fetch %s] No authentication required", endpoint)
        headers = {}
    elif vsn_model == "VSN300":
        digest_value = await get_vsn300_digest_header(
            session, base_url, username, password, endpoint, "GET", timeout
        )
        headers = {"Authorization": f"X-Digest {digest_value}"}
    else:  # VSN700
        basic_auth = get_vsn700_basic_auth(username, password)
        headers = {"Authorization": f"Basic {basic_auth}"}

    # Make authenticated request
    async with session.get(
        url,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=timeout),
    ) as response:
        if response.status == 200:
            return await response.json()
        raise Exception(f"Request failed: HTTP {response.status}")


# ============================================================================
# Mapping and Normalization Module
# ============================================================================


async def load_mapping_from_url(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Load VSN-SunSpec mapping from GitHub URL.

    Returns:
        Dictionary with vsn300_index, vsn700_index, and mappings

    """
    _LOGGER.info("Loading VSN-SunSpec mapping from GitHub...")

    try:
        async with session.get(
            MAPPING_URL, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                # GitHub serves raw files as text/plain, so we need to use content_type=None
                # to allow aiohttp to parse JSON regardless of Content-Type header
                mappings_data = await response.json(content_type=None)

                # Build indexes for fast lookup
                vsn300_index = {}
                vsn700_index = {}

                for mapping in mappings_data:
                    vsn300_name = mapping.get("REST Name (VSN300)")
                    vsn700_name = mapping.get("REST Name (VSN700)")
                    mapping.get("HA Entity Name")

                    if vsn300_name and vsn300_name != "N/A":
                        vsn300_index[vsn300_name] = mapping
                    if vsn700_name and vsn700_name != "N/A":
                        vsn700_index[vsn700_name] = mapping

                _LOGGER.info(
                    "✓ Loaded %d mappings (%d VSN300, %d VSN700)",
                    len(mappings_data),
                    len(vsn300_index),
                    len(vsn700_index),
                )

                return {
                    "vsn300_index": vsn300_index,
                    "vsn700_index": vsn700_index,
                    "mappings": mappings_data,
                }
            raise Exception(f"Failed to load mapping: HTTP {response.status}")
    except Exception as err:
        _LOGGER.warning("Could not load mapping from URL: %s", err)
        _LOGGER.warning("Normalization will be skipped")
        _LOGGER.info(
            "  Note: Mapping file may not be available yet in the GitHub repository"
        )
        _LOGGER.info(
            "  The normalization feature will be available once the file is committed"
        )
        return None


def normalize_livedata(
    raw_data: dict[str, Any], vsn_model: str, mapping_data: dict
) -> dict[str, Any]:
    """Normalize VSN livedata to Home Assistant format.

    Args:
        raw_data: Raw livedata from VSN
        vsn_model: "VSN300" or "VSN700"
        mapping_data: Mapping data with indexes

    Returns:
        Normalized data structure

    """
    if not mapping_data:
        return None

    index = (
        mapping_data["vsn300_index"]
        if vsn_model == "VSN300"
        else mapping_data["vsn700_index"]
    )

    normalized = {"devices": {}}

    for device_id, device_data in raw_data.items():
        if not isinstance(device_data, dict):
            continue

        device_points = {}
        points = device_data.get("points", [])

        for point in points:
            if not isinstance(point, dict):
                continue

            point_name = point.get("name")
            if not point_name or point_name not in index:
                continue

            mapping = index[point_name]
            ha_entity = mapping.get("HA Entity Name")
            point_value = point.get("value")

            # Get metadata from mapping
            device_class = mapping.get("HA Device Class", "")
            unit = mapping.get("HA Unit of Measurement", "")

            # Convert energy sensors from Wh to kWh (matching normalizer.py logic)
            if device_class == "energy" and point_value is not None:
                if isinstance(point_value, (int, float)) and point_value != 0:
                    point_value = point_value / 1000  # Wh → kWh
                    unit = "kWh"

            if ha_entity:
                device_points[ha_entity] = {
                    "value": point_value,
                    "units": unit,
                    "label": mapping.get("Label", ""),
                    "description": mapping.get("Description", ""),
                    "device_class": device_class,
                    "state_class": mapping.get("HA State Class", ""),
                }

        if device_points:
            normalized["devices"][device_id] = {
                "device_type": device_data.get("device_type", "unknown"),
                "timestamp": device_data.get("timestamp", ""),
                "points": device_points,
            }

    return normalized


async def test_vsn_device(
    host: str,
    username: str = "guest",
    password: str = "",
    timeout: int = 10,
) -> None:
    """Test VSN device and display results.

    Args:
        host: Hostname or IP address of the VSN device
        username: Authentication username
        password: Authentication password
        timeout: Request timeout in seconds

    """
    # Add http:// prefix if not present
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    _LOGGER.info("=" * 80)
    _LOGGER.info("VSN REST Client - Device Test")
    _LOGGER.info("Host: %s", host)
    _LOGGER.info("Base URL: %s", base_url)
    _LOGGER.info("Username: %s", username)
    _LOGGER.info("Password: %s", "(set)" if password else "(empty)")
    _LOGGER.info("Timeout: %d seconds", timeout)
    _LOGGER.info("=" * 80)

    async with aiohttp.ClientSession() as session:
        try:
            # Test 1: Device Detection
            _LOGGER.info("\n[TEST 1] Device Detection")
            _LOGGER.info("-" * 80)
            model, requires_auth = await detect_vsn_model(
                session, base_url, username, password, timeout
            )
            _LOGGER.info("✓ Device detected: %s", model)
            _LOGGER.info("  - Requires authentication: %s", requires_auth)

            # Test 2: /v1/status
            _LOGGER.info("\n[TEST 2] /v1/status - System Information")
            _LOGGER.info("-" * 80)
            status_data = await fetch_endpoint(
                session, base_url, "/v1/status", model, username, password, timeout,
                requires_auth=requires_auth,
            )
            _LOGGER.info("✓ Status endpoint successful")

            if isinstance(status_data, dict) and "keys" in status_data:
                keys_data = status_data["keys"]
                important_keys = [
                    "logger.sn",
                    "device.invID",
                    "device.modelDesc",
                    "fw.release_number",
                ]
                for key in important_keys:
                    if key in keys_data:
                        _LOGGER.info(
                            "  - %s: %s", key, keys_data[key].get("value", "N/A")
                        )

            # Save status to file
            output_file = Path.cwd() / f"{model.lower()}_status.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Test 3: /v1/livedata
            _LOGGER.info("\n[TEST 3] /v1/livedata - Live Data")
            _LOGGER.info("-" * 80)
            livedata = await fetch_endpoint(
                session, base_url, "/v1/livedata", model, username, password, timeout,
                requires_auth=requires_auth,
            )
            _LOGGER.info("✓ Livedata endpoint successful")
            _LOGGER.info("  - Number of devices: %d", len(livedata))
            _LOGGER.info("  - Device IDs: %s", list(livedata.keys()))

            # Show sample data from first device
            if livedata:
                first_device_id = list(livedata.keys())[0]
                first_device = livedata[first_device_id]
                _LOGGER.info("\n  Sample data from device: %s", first_device_id)
                if "points" in first_device:
                    points = first_device["points"]
                    _LOGGER.info("  - Total points: %d", len(points))
                    # Show first 5 points
                    for _i, point in enumerate(points[:5]):
                        name = point.get("name", "N/A")
                        value = point.get("value", "N/A")
                        _LOGGER.info("    - %s: %s", name, value)
                    if len(points) > 5:
                        _LOGGER.info("    - ... (%d more points)", len(points) - 5)

            # Save livedata to file
            output_file = Path.cwd() / f"{model.lower()}_livedata.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(livedata, f, indent=2)
            _LOGGER.info("\n  - Saved to: %s", output_file)

            # Load mapping and normalize data
            _LOGGER.info("\n[TEST 3b] Data Normalization")
            _LOGGER.info("-" * 80)
            mapping_data = await load_mapping_from_url(session)

            if mapping_data:
                normalized = normalize_livedata(livedata, model, mapping_data)
                if normalized:
                    total_points = sum(
                        len(d.get("points", {}))
                        for d in normalized.get("devices", {}).values()
                    )
                    _LOGGER.info("✓ Data normalized successfully")
                    _LOGGER.info("  - Normalized points: %d", total_points)

                    # Show sample normalized data
                    if normalized.get("devices"):
                        first_device_id = list(normalized["devices"].keys())[0]
                        first_device = normalized["devices"][first_device_id]
                        _LOGGER.info(
                            "\n  Sample normalized data from: %s", first_device_id
                        )
                        points = first_device.get("points", {})
                        for _i, (ha_entity, point_data) in enumerate(
                            list(points.items())[:5]
                        ):
                            value = point_data.get("value")
                            units = point_data.get("units", "")
                            label = point_data.get("label", "")
                            _LOGGER.info(
                                "    - %s (%s): %s %s", ha_entity, label, value, units
                            )
                        if len(points) > 5:
                            _LOGGER.info("    - ... (%d more points)", len(points) - 5)

                    # Save normalized data
                    output_file = Path.cwd() / f"{model.lower()}_normalized.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(normalized, f, indent=2)
                    _LOGGER.info("\n  - Saved to: %s", output_file)
                else:
                    _LOGGER.warning("✗ Normalization failed")
            else:
                _LOGGER.warning("✗ Mapping not available, skipping normalization")

            # Test 4: /v1/feeds
            _LOGGER.info("\n[TEST 4] /v1/feeds - Feed Metadata")
            _LOGGER.info("-" * 80)
            feeds_data = await fetch_endpoint(
                session, base_url, "/v1/feeds", model, username, password, timeout,
                requires_auth=requires_auth,
            )
            _LOGGER.info("✓ Feeds endpoint successful")

            if isinstance(feeds_data, dict) and "feeds" in feeds_data:
                _LOGGER.info("  - Number of feeds: %d", len(feeds_data["feeds"]))

            # Save feeds to file
            output_file = Path.cwd() / f"{model.lower()}_feeds.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(feeds_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Summary
            _LOGGER.info("\n" + "=" * 80)
            _LOGGER.info("TEST SUMMARY")
            _LOGGER.info("=" * 80)
            _LOGGER.info("✓ Device model: %s", model)
            _LOGGER.info("✓ Requires authentication: %s", requires_auth)
            _LOGGER.info("✓ All 3 endpoints tested successfully!")
            _LOGGER.info("✓ /v1/status: OK")
            _LOGGER.info("✓ /v1/livedata: OK (%d devices)", len(livedata))
            if mapping_data and normalized:
                total_points = sum(
                    len(d.get("points", {}))
                    for d in normalized.get("devices", {}).values()
                )
                _LOGGER.info("✓ /v1/livedata normalized: OK (%d points)", total_points)
            _LOGGER.info("✓ /v1/feeds: OK")
            _LOGGER.info("\nOutput files created:")
            _LOGGER.info("  - %s_status.json", model.lower())
            _LOGGER.info("  - %s_livedata.json", model.lower())
            if mapping_data and normalized:
                _LOGGER.info("  - %s_normalized.json", model.lower())
            _LOGGER.info("  - %s_feeds.json", model.lower())
            _LOGGER.info("=" * 80)

        except Exception as err:
            _LOGGER.error("\n✗ Error: %s", err)
            import traceback

            _LOGGER.debug(traceback.format_exc())
            sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VSN REST Client - Self-contained testing script for VSN300/VSN700 devices"
    )
    parser.add_argument(
        "host",
        help="Host or IP address of the VSN device (e.g., 192.168.1.100 or abb-vsn300.local)",
    )
    parser.add_argument(
        "--username", "-u",
        default="guest",
        help="Authentication username (check your datalogger's web interface)",
    )
    parser.add_argument(
        "--password", "-p",
        default="",
        help="Authentication password (check your datalogger's web interface)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    args = parser.parse_args()

    asyncio.run(test_vsn_device(
        host=args.host,
        username=args.username,
        password=args.password,
        timeout=args.timeout,
    ))


if __name__ == "__main__":
    main()
