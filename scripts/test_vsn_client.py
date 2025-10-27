#!/usr/bin/env python3
"""Test script for VSN REST client.

Tests all endpoints and client functionality:
- Device detection
- /v1/status endpoint (system info)
- /v1/livedata endpoint (raw data)
- /v1/feeds endpoint (feed metadata)
- Data normalization

Usage:
    python test_vsn_client.py <host>

Example:
    python test_vsn_client.py 192.168.1.100
    python test_vsn_client.py abb-vsn300.axel.dom

"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import aiohttp

# Add parent directory to path for imports
sys.path.insert(
    0,
    str(Path(__file__).parent.parent / "custom_components" / "abb_fimer_pvi_vsn_rest"),
)

from abb_fimer_vsn_rest_client.auth import (
    get_vsn300_digest_header,
    get_vsn700_basic_auth,
)
from abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from abb_fimer_vsn_rest_client.exceptions import VSNClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def test_endpoint(
    session: aiohttp.ClientSession,
    base_url: str,
    endpoint: str,
    vsn_model: str,
    username: str = "guest",
    password: str = "",
    timeout: int = 10,
) -> dict:
    """Test a specific VSN endpoint.

    Args:
        session: aiohttp session
        base_url: Base URL
        endpoint: Endpoint path (e.g., /v1/status)
        vsn_model: VSN model type ("VSN300" or "VSN700")
        username: Username
        password: Password
        timeout: Timeout in seconds

    Returns:
        Response data

    """
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
        raise VSNClientError(f"Request failed: HTTP {response.status}")


async def test_client(base_url: str) -> None:
    """Test the VSN REST client.

    Args:
        base_url: Base URL of the VSN device (e.g., http://192.168.1.100)

    """
    _LOGGER.info("=" * 80)
    _LOGGER.info("VSN REST Client - Comprehensive Test")
    _LOGGER.info("Base URL: %s", base_url)
    _LOGGER.info("Username: guest (default)")
    _LOGGER.info("Password: (empty)")
    _LOGGER.info("=" * 80)

    async with aiohttp.ClientSession() as session:
        try:
            # Create client with default guest credentials
            client = ABBFimerVSNRestClient(
                session=session,
                base_url=base_url,
            )

            # Test 1: Connect and detect device
            _LOGGER.info("\n[TEST 1] Device Detection")
            _LOGGER.info("-" * 80)
            model = await client.connect()
            _LOGGER.info("✓ Device detected: %s", model)

            # Test 2: /v1/status endpoint
            _LOGGER.info("\n[TEST 2] /v1/status - System Information")
            _LOGGER.info("-" * 80)
            status_data = await test_endpoint(session, base_url, "/v1/status", model)
            _LOGGER.info("✓ Status endpoint successful")

            if isinstance(status_data, dict):
                _LOGGER.info("  - Keys: %s", list(status_data.keys()))
                if "keys" in status_data and isinstance(status_data["keys"], dict):
                    keys_data = status_data["keys"]
                    _LOGGER.info("  - System info keys: %d", len(keys_data))
                    # Show important system info
                    important_keys = [
                        "logger.sn",
                        "device.invID",
                        "device.modelDesc",
                        "fw.release_number",
                    ]
                    for key in important_keys:
                        if key in keys_data:
                            _LOGGER.info(
                                "    - %s: %s", key, keys_data[key].get("value", "N/A")
                            )

            # Save to file
            output_file = (
                Path(__file__).parent / f"test_output_{model.lower()}_status.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Test 3: /v1/livedata endpoint (raw)
            _LOGGER.info("\n[TEST 3] /v1/livedata - Raw Data")
            _LOGGER.info("-" * 80)
            raw_data = await client.get_livedata()
            _LOGGER.info("✓ Raw livedata received")
            _LOGGER.info("  - Number of devices: %d", len(raw_data))
            _LOGGER.info("  - Device IDs: %s", list(raw_data.keys()))

            # Save raw data to file
            output_file = (
                Path(__file__).parent / f"test_output_{model.lower()}_livedata.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Test 4: /v1/feeds endpoint
            _LOGGER.info("\n[TEST 4] /v1/feeds - Feed Metadata")
            _LOGGER.info("-" * 80)
            feeds_data = await test_endpoint(session, base_url, "/v1/feeds", model)
            _LOGGER.info("✓ Feeds endpoint successful")

            if isinstance(feeds_data, dict):
                _LOGGER.info("  - Keys: %s", list(feeds_data.keys()))
                if "feeds" in feeds_data:
                    _LOGGER.info("  - Number of feeds: %d", len(feeds_data["feeds"]))
            elif isinstance(feeds_data, list):
                _LOGGER.info("  - Number of feeds: %d", len(feeds_data))

            # Save to file
            output_file = (
                Path(__file__).parent / f"test_output_{model.lower()}_feeds.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(feeds_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Test 5: Data normalization
            _LOGGER.info("\n[TEST 5] Data Normalization")
            _LOGGER.info("-" * 80)
            normalized_data = await client.get_normalized_data()
            _LOGGER.info("✓ Normalized data received")
            _LOGGER.info(
                "  - Number of devices: %d", len(normalized_data.get("devices", {}))
            )

            # Save normalized data to file
            output_file = (
                Path(__file__).parent / f"test_output_{model.lower()}_normalized.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(normalized_data, f, indent=2)
            _LOGGER.info("  - Saved to: %s", output_file)

            # Show sample of normalized data
            _LOGGER.info("\n[SAMPLE] Normalized Data Structure:")
            for device_id, device_data in normalized_data.get("devices", {}).items():
                _LOGGER.info("  Device: %s", device_id)
                points = device_data.get("points", {})
                _LOGGER.info("    - Number of points: %d", len(points))
                # Show first 5 points
                for _i, (point_name, point_data) in enumerate(list(points.items())[:5]):
                    value = point_data.get("value")
                    units = point_data.get("units", "")
                    _LOGGER.info("    - %s: %s %s", point_name, value, units)
                if len(points) > 5:
                    _LOGGER.info("    - ... (%d more points)", len(points) - 5)

            # Close client
            await client.close()
            _LOGGER.info("\n✓ Client closed")

            # Summary
            _LOGGER.info("\n" + "=" * 80)
            _LOGGER.info("TEST SUMMARY")
            _LOGGER.info("=" * 80)
            _LOGGER.info("✓ Device detection: %s", model)
            _LOGGER.info("✓ /v1/status endpoint: OK")
            _LOGGER.info("✓ /v1/livedata endpoint: OK (%d devices)", len(raw_data))
            _LOGGER.info("✓ /v1/feeds endpoint: OK")
            _LOGGER.info(
                "✓ Data normalization: OK (%d points total)",
                sum(
                    len(d.get("points", {}))
                    for d in normalized_data.get("devices", {}).values()
                ),
            )
            _LOGGER.info("=" * 80)
            _LOGGER.info("All tests passed successfully!")
            _LOGGER.info("=" * 80)

        except VSNClientError as err:
            _LOGGER.error("\n✗ VSN Client Error: %s", err)
            sys.exit(1)
        except Exception as err:
            _LOGGER.error("\n✗ Unexpected Error: %s", err, exc_info=True)
            sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python test_vsn_client.py <host>")
        print("Example: python test_vsn_client.py 192.168.1.100")
        print("         python test_vsn_client.py abb-vsn300.axel.dom")
        sys.exit(1)

    host = sys.argv[1]

    # Add http:// prefix if not present
    if not host.startswith(("http://", "https://")):
        base_url = f"http://{host}"
    else:
        base_url = host

    asyncio.run(test_client(base_url))


if __name__ == "__main__":
    main()
