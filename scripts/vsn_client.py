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
    python vsn_client.py <host>

Example:
    python vsn_client.py 192.168.1.100
    python vsn_client.py abb-vsn300.axel.dom

Requirements:
    - Python 3.9+
    - aiohttp (install with: pip install aiohttp)

"""

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

# URL to the mapping JSON on GitHub
MAPPING_URL = "https://raw.githubusercontent.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/master/docs/vsn-sunspec-point-mapping.json"


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


async def detect_vsn_model(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    password: str,
    timeout: int = 10,
) -> str:
    """Detect VSN model by examining WWW-Authenticate header."""
    base_url = base_url.rstrip("/")

    try:
        async with session.get(
            f"{base_url}/v1/status",
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "").lower()

                if not www_authenticate:
                    raise Exception(
                        "Device returned 401 but no WWW-Authenticate header found"
                    )

                if "x-digest" in www_authenticate or "digest" in www_authenticate:
                    _LOGGER.info("Detected VSN300 (digest auth)")
                    return "VSN300"

                if "basic" in www_authenticate:
                    _LOGGER.info("Detected VSN700 (basic auth)")
                    return "VSN700"

                raise Exception(f"Unknown authentication scheme: {www_authenticate}")
            raise Exception(
                f"Expected 401 response for detection, got {response.status}"
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
) -> dict:
    """Fetch data from a VSN endpoint."""
    url = f"{base_url.rstrip('/')}{endpoint}"

    # Build auth header based on model
    if vsn_model == "VSN300":
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

            if ha_entity:
                device_points[ha_entity] = {
                    "value": point.get("value"),
                    "units": mapping.get("Units", ""),
                    "label": mapping.get("Label", ""),
                    "description": mapping.get("Description", ""),
                    "device_class": mapping.get("Device Class", ""),
                    "state_class": mapping.get("State Class", ""),
                }

        if device_points:
            normalized["devices"][device_id] = {
                "device_type": device_data.get("device_type", "unknown"),
                "timestamp": device_data.get("timestamp", ""),
                "points": device_points,
            }

    return normalized


async def test_vsn_device(host: str) -> None:
    """Test VSN device and display results."""
    # Add http:// prefix if not present
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    _LOGGER.info("=" * 80)
    _LOGGER.info("VSN REST Client - Device Test")
    _LOGGER.info("Host: %s", host)
    _LOGGER.info("Base URL: %s", base_url)
    _LOGGER.info("Username: guest (default)")
    _LOGGER.info("Password: (empty)")
    _LOGGER.info("=" * 80)

    async with aiohttp.ClientSession() as session:
        try:
            # Test 1: Device Detection
            _LOGGER.info("\n[TEST 1] Device Detection")
            _LOGGER.info("-" * 80)
            model = await detect_vsn_model(session, base_url, "guest", "", 10)
            _LOGGER.info("✓ Device detected: %s", model)

            # Test 2: /v1/status
            _LOGGER.info("\n[TEST 2] /v1/status - System Information")
            _LOGGER.info("-" * 80)
            status_data = await fetch_endpoint(session, base_url, "/v1/status", model)
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
            livedata = await fetch_endpoint(session, base_url, "/v1/livedata", model)
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
            feeds_data = await fetch_endpoint(session, base_url, "/v1/feeds", model)
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
    if len(sys.argv) != 2:
        print("VSN REST Client - Self-contained testing script")
        print()
        print("Usage: python vsn_client.py <host>")
        print()
        print("Example:")
        print("  python vsn_client.py 192.168.1.100")
        print("  python vsn_client.py abb-vsn300.axel.dom")
        print()
        print("Requirements:")
        print("  - Python 3.9+")
        print("  - aiohttp (install with: pip install aiohttp)")
        sys.exit(1)

    host = sys.argv[1]
    asyncio.run(test_vsn_device(host))


if __name__ == "__main__":
    main()
