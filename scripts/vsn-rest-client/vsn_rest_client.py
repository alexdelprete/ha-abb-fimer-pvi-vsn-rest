#!/usr/bin/env python3
"""ABB/FIMER/Power-One VSN REST Client - Standalone Test Script.

Self-contained REST client for testing VSN300/VSN700 dataloggers.
This script mirrors the integration's client library features but
can be run independently of Home Assistant.

Usage:
    python vsn_rest_client.py --host <IP> [--username guest] [--password ""]

Features:
    - Automatic VSN300/VSN700 detection (auth header + status structure analysis)
    - X-Digest authentication (VSN300) / Basic authentication (VSN700)
    - Socket connectivity check (fast-fail when device is offline)
    - Full device discovery (logger metadata, inverters, meters, batteries)
    - Data normalization with SunSpec mapping (fetched from GitHub)
    - All value transformations (uA->mA, A->mA, temp correction, Wh->kWh, bytes->MB)
    - VSN300/VSN700 point name normalization (M101/M102->M103, TSoc->Soc)
    - Aurora protocol state translation (human-readable status codes)
    - Comprehensive sensor attributes in normalized output
    - Pretty-printed JSON output with optional file save

Requirements:
    - Python 3.11+
    - aiohttp

Author: Alex Del Prete
License: Apache-2.0
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import socket
import sys
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────


class VSNClientError(Exception):
    """Base exception for VSN client."""


class VSNConnectionError(VSNClientError):
    """Connection error."""


class VSNAuthenticationError(VSNClientError):
    """Authentication error."""


class VSNDetectionError(VSNClientError):
    """VSN model detection error."""


class VSNUnsupportedDeviceError(VSNDetectionError):
    """Device doesn't support VSN REST API (404 response)."""


# ── Constants ────────────────────────────────────────────────────────

DEFAULT_USERNAME = "guest"
DEFAULT_PASSWORD = ""
DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 10

ENDPOINT_STATUS = "/v1/status"
ENDPOINT_LIVEDATA = "/v1/livedata"
ENDPOINT_FEEDS = "/v1/feeds"

MAPPING_URL = (
    "https://raw.githubusercontent.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest"
    "/master/docs/vsn-sunspec-point-mapping.json"
)

# Aurora protocol epoch offset (Jan 1, 2000 00:00:00 UTC)
AURORA_EPOCH_OFFSET = 946684800

# Aurora Protocol State Mappings
# Reference: https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library
GLOBAL_STATE_MAP = {
    0: "Sending Parameters",
    1: "Wait Sun / Grid",
    2: "Checking Grid",
    3: "Measuring Riso",
    4: "DcDc Start",
    5: "Inverter Start",
    6: "Run",
    7: "Recovery",
    8: "Pausev",
    9: "Ground Fault",
    10: "OTH Fault",
    11: "Address Setting",
    12: "Self Test",
    13: "Self Test Fail",
    14: "Sensor Test + Meas.Riso",
    15: "Leak Fault",
    16: "Waiting for manual reset",
    17: "Internal Error E026",
    18: "Internal Error E027",
    19: "Internal Error E028",
    20: "Internal Error E029",
    21: "Internal Error E030",
    22: "Sending Wind Table",
    23: "Failed Sending table",
    24: "UTH Fault",
    25: "Remote OFF",
    26: "Interlock Fail",
    27: "Executing Autotest",
    30: "Waiting Sun",
    31: "Temperature Fault",
    32: "Fan Staucked",
    33: "Int.Com.Fault",
    34: "Slave Insertion",
    35: "DC Switch Open",
    36: "TRAS Switch Open",
    37: "MASTER Exclusion",
    38: "Auto Exclusion",
    98: "Erasing Internal EEprom",
    99: "Erasing External EEprom",
    100: "Counting EEprom",
    101: "Freeze",
}

DCDC_STATE_MAP = {
    0: "DcDc OFF",
    1: "Ramp Start",
    2: "MPPT",
    3: "Not Used",
    4: "Input OC",
    5: "Input UV",
    6: "Input OV",
    7: "Input Low",
    8: "No Parameters",
    9: "Bulk OV",
    10: "Communication Error",
    11: "Ramp Fail",
    12: "Internal Error",
    13: "Input mode Error",
    14: "Ground Fault",
    15: "Inverter Fail",
    16: "DcDc IGBT Sat",
    17: "DcDc ILEAK Fail",
    18: "DcDc Grid Fail",
    19: "DcDc Comm. Error",
}

INVERTER_STATE_MAP = {
    0: "Stand By",
    1: "Checking Grid",
    2: "Run",
    3: "Bulk OV",
    4: "Out OC",
    5: "IGBT Sat",
    6: "Bulk UV",
    7: "Degauss Error",
    8: "No Parameters",
    9: "Bulk Low",
    10: "Grid OV",
    11: "Communication Error",
    12: "Degaussing",
    13: "Starting",
    14: "Bulk Cap Fail",
    15: "Leak Fail",
    16: "DcDc Fail",
    17: "Ileak Sensor Fail",
    18: "SelfTest: relay inverter",
    19: "SelfTest: wait for sensor test",
    20: "SelfTest: test relay DcDc + sensor",
    21: "SelfTest: relay inverter fail",
    22: "SelfTest: timeout fail",
    23: "SelfTest: relay DcDc fail",
    24: "Self Test 1",
    25: "Waiting self test start",
    26: "Dc Injection",
    27: "Self Test 2",
    28: "Self Test 3",
    29: "Self Test 4",
    30: "Internal Error",
    31: "Internal Error",
    40: "Forbidden State",
    41: "Input UC",
    42: "Zero Power",
    43: "Grid Not Present",
    44: "Waiting Start",
    45: "MPPT",
    46: "Grid Fail",
    47: "Input OC",
}

ALARM_STATE_MAP = {
    0: "No Alarm",
    1: "Sun Low",
    2: "Input OC",
    3: "Input UV",
    4: "Input OV",
    5: "Sun Low",
    6: "No Parameters",
    7: "Bulk OV",
    8: "Comm.Error",
    9: "Output OC",
    10: "IGBT Sat",
    11: "Bulk UV",
    12: "Internal error",
    13: "Grid Fail",
    14: "Bulk Low",
    15: "Ramp Fail",
    16: "Dc/Dc Fail",
    17: "Wrong Mode",
    18: "Ground Fault",
    19: "Over Temp.",
    20: "Bulk Cap Fail",
    21: "Inverter Fail",
    22: "Start Timeout",
    23: "Ground Fault",
    24: "Degauss error",
    25: "Ileak sens.fail",
    26: "DcDc Fail",
    27: "Self Test Error 1",
    28: "Self Test Error 2",
    29: "Self Test Error 3",
    30: "Self Test Error 4",
    31: "DC inj error",
    32: "Grid OV",
    33: "Grid UV",
    34: "Grid OF",
    35: "Grid UF",
    36: "Z grid Hi",
    37: "Internal error",
    38: "Riso Low",
    39: "Vref Error",
    40: "Error Meas V",
    41: "Error Meas F",
    42: "Error Meas Z",
    43: "Error Meas Ileak",
    44: "Error Read V",
    45: "Error Read I",
    46: "Table fail",
    47: "Fan Fail",
    48: "UTH",
    49: "Interlock fail",
    50: "Remote Off",
    51: "Vout Avg errror",
    52: "Battery low",
    53: "Clk fail",
    54: "Input UC",
    55: "Zero Power",
    56: "Fan Stucked",
    57: "DC Switch Open",
    58: "Tras Switch Open",
    59: "AC Switch Open",
    60: "Bulk UV",
    61: "Autoexclusion",
    62: "Grid df / dt",
    63: "Den switch Open",
    64: "Jbox fail",
}

# State entity name -> state map
STATE_ENTITY_MAPPINGS: dict[str, dict[int, str]] = {
    "GlobState": GLOBAL_STATE_MAP,
    "m64061_1_GlobState": GLOBAL_STATE_MAP,
    "DC1State": DCDC_STATE_MAP,
    "m64061_1_DC1State": DCDC_STATE_MAP,
    "DC2State": DCDC_STATE_MAP,
    "m64061_1_DC2State": DCDC_STATE_MAP,
    "InvState": INVERTER_STATE_MAP,
    "m64061_1_InvState": INVERTER_STATE_MAP,
    "AlarmState": ALARM_STATE_MAP,
    "AlarmSt": ALARM_STATE_MAP,
    "m64061_1_AlarmState": ALARM_STATE_MAP,
}

# ── Normalization Registries ─────────────────────────────────────────

# uA to mA conversion (divide by 1000)
UA_TO_MA_POINTS = {
    "m64061_1_ILeakDcAc",
    "m64061_1_ILeakDcDc",
    "Ileak 1",
    "Ileak 2",
}

# A to mA conversion for VSN700 leakage current (multiply by 1000)
A_TO_MA_POINTS = {"IleakInv", "IleakDC"}

# Temperature scale factor correction (divide by 10 when > 70)
TEMP_CORRECTION_POINTS = {"m103_1_TmpCab", "m101_1_TmpCab", "Temp1"}
TEMP_THRESHOLD_CELSIUS = 70

# String cleanup - strip leading/trailing dashes
STRING_STRIP_POINTS = {"pn", "C_Md"}

# Title case normalization
TITLE_CASE_POINTS = {"type"}

# Bytes to MB conversion (divide by 1048576)
B_TO_MB_POINTS = {"flash_free", "free_ram", "store_size"}

# VSN700 alternate name normalization
VSN700_NAME_NORMALIZATION = {"TSoc": "Soc"}


# ── Data Models ──────────────────────────────────────────────────────


@dataclass
class DiscoveredDevice:
    """Represents a discovered device."""

    device_id: str
    raw_device_id: str
    device_type: str
    device_model: str | None = None
    manufacturer: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    is_datalogger: bool = False


@dataclass
class DiscoveryResult:
    """Complete discovery result from VSN device."""

    vsn_model: str
    requires_auth: bool
    logger_sn: str
    logger_model: str | None = None
    firmware_version: str | None = None
    hostname: str | None = None
    devices: list[DiscoveredDevice] = field(default_factory=list)
    status_data: dict[str, Any] = field(default_factory=dict)

    def get_title(self) -> str:
        """Generate a suitable title."""
        return f"{self.vsn_model} ({self.logger_sn})"


@dataclass
class PointMapping:
    """Mapping information for a single point."""

    vsn700_name: str | None
    vsn300_name: str | None
    sunspec_name: str | None
    ha_entity_name: str
    in_livedata: bool
    in_feeds: bool
    label: str
    description: str
    ha_display_name: str
    models: list[str]
    category: str
    units: str
    state_class: str
    device_class: str
    entity_category: str | None
    available_in_modbus: str
    icon: str = ""
    suggested_display_precision: int | None = None


# ── Socket Check ─────────────────────────────────────────────────────


def check_socket_connection(base_url: str, timeout: int = 5) -> None:
    """Check TCP socket connection (fast-fail when device is offline).

    Args:
        base_url: Base URL of device (e.g., "http://192.168.1.100")
        timeout: Socket connection timeout in seconds

    Raises:
        VSNConnectionError: If socket connection fails

    """
    parsed = urlparse(base_url)
    hostname = parsed.hostname or parsed.netloc.split(":")[0]
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    _LOGGER.debug("Testing socket connection to %s:%d...", hostname, port)

    try:
        sock = socket.create_connection((hostname, port), timeout=timeout)
        sock.close()
        _LOGGER.debug("Socket connection to %s:%d successful", hostname, port)
    except (TimeoutError, ConnectionRefusedError, OSError) as err:
        msg = f"Cannot connect to {hostname}:{port}: {err}"
        raise VSNConnectionError(msg) from err


# ── Authentication ───────────────────────────────────────────────────


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
    """Calculate HTTP Digest authentication response (MD5)."""
    ha1 = hashlib.md5(  # noqa: S324
        f"{username}:{realm}:{password}".encode()
    ).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()  # noqa: S324

    if qop and nc and cnonce:
        response_str = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        response_str = f"{ha1}:{nonce}:{ha2}"

    return hashlib.md5(response_str.encode()).hexdigest()  # noqa: S324


def parse_digest_challenge(www_authenticate: str) -> dict[str, str]:
    """Parse WWW-Authenticate digest challenge header."""
    challenge = re.sub(r"^(Digest|X-Digest)\s+", "", www_authenticate, flags=re.IGNORECASE)
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
        cnonce_input = f"{nonce}:{time.time()}:{os.urandom(8).hex()}"
        cnonce = hashlib.md5(cnonce_input.encode()).hexdigest()[:16]  # noqa: S324
        response = calculate_digest_response(
            username, password, realm, nonce, method, uri, qop, nc, cnonce
        )
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
        response = calculate_digest_response(username, password, realm, nonce, method, uri)
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
    uri: str = ENDPOINT_LIVEDATA,
    method: str = "GET",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Get VSN300 X-Digest authentication header via challenge-response."""
    url = f"{base_url.rstrip('/')}{uri}"

    _LOGGER.debug("Requesting digest challenge: %s %s", method, url)

    try:
        async with session.request(
            method, url, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "")

                if not www_authenticate or "digest" not in www_authenticate.lower():
                    raise VSNAuthenticationError("VSN300 challenge missing or not digest-based")

                challenge_params = parse_digest_challenge(www_authenticate)
                digest_value = build_digest_header(
                    username, password, challenge_params, method, uri
                )
                _LOGGER.debug("Generated X-Digest header for %s", username)
                return digest_value

            raise VSNAuthenticationError(f"Expected 401 challenge, got {response.status}")
    except aiohttp.ClientError as err:
        raise VSNConnectionError(f"VSN300 challenge request failed: {err}") from err


def get_vsn700_basic_auth(username: str, password: str) -> str:
    """Get VSN700 HTTP Basic authentication header value (base64)."""
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode("utf-8")).decode("utf-8")


# ── Model Detection ──────────────────────────────────────────────────


async def detect_vsn_model(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    password: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, bool]:
    """Detect VSN model by examining response and data structure.

    Returns:
        Tuple of (vsn_model, requires_auth)

    """
    base_url = base_url.rstrip("/")
    check_socket_connection(base_url, timeout=5)

    detection_url = f"{base_url}{ENDPOINT_STATUS}"
    _LOGGER.debug("Detecting VSN model at %s", detection_url)

    try:
        async with session.get(
            detection_url, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            _LOGGER.debug("Detection response: status=%d", response.status)

            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "").lower()

                # Digest auth = VSN300
                if www_authenticate and (
                    "x-digest" in www_authenticate or "digest" in www_authenticate
                ):
                    _LOGGER.info("Detected VSN300 (digest auth)")
                    return ("VSN300", True)

                # Try preemptive Basic auth for VSN700
                _LOGGER.debug("Trying preemptive Basic auth for VSN700")
                basic_auth = get_vsn700_basic_auth(username, password)
                auth_headers = {"Authorization": f"Basic {basic_auth}"}

                async with session.get(
                    detection_url,
                    headers=auth_headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as auth_response:
                    if auth_response.status in (200, 204):
                        _LOGGER.info("Detected VSN700 (preemptive Basic auth)")
                        return ("VSN700", True)

                    raise VSNDetectionError(
                        f"Authentication failed (status {auth_response.status}). "
                        "Not VSN300/VSN700 compatible."
                    )

            if response.status == 200:
                _LOGGER.info("No authentication required (HTTP 200)")
                status_data = await response.json()
                model = _detect_model_from_status(status_data)
                return (model, False)

            if response.status == 404:
                raise VSNUnsupportedDeviceError(
                    f"Device at {base_url} returned 404 - REST API not available"
                )

            raise VSNDetectionError(f"Unexpected response status {response.status}")
    except aiohttp.ClientError as err:
        raise VSNConnectionError(f"Device detection connection error: {err}") from err


def _detect_model_from_status(status_data: dict) -> str:
    """Detect VSN model from status data structure."""
    keys = status_data.get("keys", {})

    # VSN300: board_model = "WIFI LOGGER CARD"
    board_model = keys.get("logger.board_model", {}).get("value", "")
    if board_model == "WIFI LOGGER CARD":
        _LOGGER.info("Detected VSN300 (board_model='WIFI LOGGER CARD')")
        return "VSN300"

    # VSN300: serial number format XXXXXX-XXXX-XXXX
    logger_sn = keys.get("logger.sn", {}).get("value", "")
    if logger_sn and re.match(r"^\d{6}-\w{4}-\d{4}$", logger_sn):
        _LOGGER.info("Detected VSN300 (S/N format: %s)", logger_sn)
        return "VSN300"

    # VSN700: loggerId is MAC address xx:xx:xx:xx:xx:xx
    logger_id = keys.get("logger.loggerId", {}).get("value", "")
    if logger_id and re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", logger_id):
        _LOGGER.info("Detected VSN700 (MAC: %s)", logger_id)
        return "VSN700"

    # Fallback: VSN300 has many more keys
    if len(keys) > 10:
        _LOGGER.info("Detected VSN300 (rich status: %d keys)", len(keys))
        return "VSN300"

    if len(keys) <= 3:
        _LOGGER.info("Detected VSN700 (minimal status: %d keys)", len(keys))
        return "VSN700"

    raise VSNDetectionError(f"Could not determine VSN model. Status keys: {list(keys.keys())}")


# ── Authenticated Fetch ──────────────────────────────────────────────


async def fetch_endpoint(
    session: aiohttp.ClientSession,
    base_url: str,
    endpoint: str,
    vsn_model: str,
    username: str,
    password: str,
    timeout: int,
    requires_auth: bool = True,
) -> dict[str, Any]:
    """Fetch a VSN endpoint with proper authentication."""
    check_socket_connection(base_url, timeout=5)

    url = f"{base_url}{endpoint}"

    if not requires_auth:
        headers: dict[str, str] = {}
    elif vsn_model == "VSN300":
        digest_value = await get_vsn300_digest_header(
            session, base_url, username, password, endpoint, "GET", timeout
        )
        headers = {"Authorization": f"X-Digest {digest_value}"}
    else:
        basic_auth = get_vsn700_basic_auth(username, password)
        headers = {"Authorization": f"Basic {basic_auth}"}

    _LOGGER.debug("Fetching %s (auth=%s)", url, vsn_model if requires_auth else "None")

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            if response.status == 200:
                return await response.json()

            if response.status == 401:
                raise VSNAuthenticationError(f"Authentication failed for {endpoint}: HTTP 401")

            raise VSNConnectionError(f"Request to {endpoint} failed: HTTP {response.status}")
    except aiohttp.ClientError as err:
        raise VSNConnectionError(f"Request to {endpoint} error: {err}") from err


# ── Discovery ────────────────────────────────────────────────────────


async def discover_vsn_device(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    timeout: int = DEFAULT_TIMEOUT,
) -> DiscoveryResult:
    """Discover VSN device and all connected devices."""
    _LOGGER.debug("Starting VSN device discovery at %s", base_url)

    # Step 1: Detect model
    vsn_model, requires_auth = await detect_vsn_model(
        session, base_url, username, password, timeout
    )
    _LOGGER.info("Detected %s (requires_auth=%s)", vsn_model, requires_auth)

    # Step 2: Fetch status
    status_data = await fetch_endpoint(
        session,
        base_url,
        ENDPOINT_STATUS,
        vsn_model,
        username,
        password,
        timeout,
        requires_auth,
    )

    # Step 3: Fetch livedata
    livedata = await fetch_endpoint(
        session,
        base_url,
        ENDPOINT_LIVEDATA,
        vsn_model,
        username,
        password,
        timeout,
        requires_auth,
    )

    # Step 4: Extract logger info
    logger_info = _extract_logger_info(status_data, vsn_model)

    # Step 5: Extract all devices
    devices = _extract_devices(livedata, vsn_model, status_data)

    _LOGGER.info("Discovery complete: %s with %d devices", vsn_model, len(devices))

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


def _extract_logger_info(status_data: dict[str, Any], vsn_model: str) -> dict[str, Any]:
    """Extract logger information from status data."""
    keys = status_data.get("keys", {})

    logger_info = {
        "logger_sn": keys.get("logger.sn", {}).get("value", "Unknown"),
        "logger_model": keys.get("logger.board_model", {}).get("value"),
        "firmware_version": keys.get("fw.release_number", {}).get("value"),
        "hostname": keys.get("logger.hostname", {}).get("value"),
    }

    if logger_info["logger_sn"] == "Unknown" and vsn_model == "VSN700":
        logger_info["logger_sn"] = keys.get("logger.loggerId", {}).get("value", "Unknown")

    return logger_info


def _extract_devices(
    livedata: dict[str, Any], vsn_model: str, status_data: dict[str, Any]
) -> list[DiscoveredDevice]:
    """Extract all devices from livedata."""
    devices = []
    keys = status_data.get("keys", {})

    # Create synthetic datalogger device
    logger_sn = keys.get("logger.sn", {}).get("value", "Unknown")
    if logger_sn == "Unknown" and vsn_model == "VSN700":
        logger_sn = keys.get("logger.loggerId", {}).get("value", "Unknown")

    logger_id = logger_sn.replace(":", "") if ":" in logger_sn else logger_sn

    devices.append(
        DiscoveredDevice(
            device_id=logger_id,
            raw_device_id=logger_sn,
            device_type="datalogger",
            device_model=vsn_model,
            manufacturer="ABB" if vsn_model == "VSN300" else "FIMER",
            firmware_version=keys.get("fw.release_number", {}).get("value"),
            is_datalogger=True,
        )
    )

    # Process livedata devices
    for raw_device_id, device_data in livedata.items():
        is_datalogger = ":" in raw_device_id
        device_id = raw_device_id

        if is_datalogger:
            sn_found = False
            for point in device_data.get("points", []):
                if point.get("name") == "sn":
                    device_id = point["value"]
                    sn_found = True
                    break
            if not sn_found:
                device_id = raw_device_id.replace(":", "")

        device_type = device_data.get("device_type", "unknown")
        device_model = None

        if is_datalogger:
            device_model = vsn_model
            device_type = "datalogger"
        elif vsn_model == "VSN700":
            device_model = device_data.get("device_model")
        elif vsn_model == "VSN300":
            device_model = keys.get("device.modelDesc", {}).get("value")

        manufacturer = None
        firmware_version = None
        hardware_version = None

        for point in device_data.get("points", []):
            point_name = point.get("name")
            if point_name == "C_Mn":
                manufacturer = point.get("value")
            elif point_name in ("C_Vr", "fw_ver"):
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
            "Discovered: %s (%s) Model=%s Mfr=%s FW=%s",
            device_id,
            device_type,
            device_model or "?",
            manufacturer or "?",
            firmware_version or "?",
        )

    return devices


# ── Mapping Loader ───────────────────────────────────────────────────


class MappingLoader:
    """Load VSN-SunSpec point mappings from GitHub."""

    def __init__(self) -> None:
        """Initialize the mapping loader."""
        self._mappings: dict[str, PointMapping] = {}
        self._vsn300_index: dict[str, str] = {}
        self._vsn700_index: dict[str, str] = {}
        self._loaded = False

    async def async_load(self, session: aiohttp.ClientSession) -> None:
        """Load mappings from GitHub."""
        if self._loaded:
            return

        _LOGGER.info("Downloading mapping file from GitHub...")

        try:
            async with session.get(
                MAPPING_URL, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    _LOGGER.warning("Failed to download mapping: HTTP %d", response.status)
                    return
                content = await response.text()
                mappings_data = json.loads(content)
        except (aiohttp.ClientError, json.JSONDecodeError) as err:
            _LOGGER.warning("Failed to load mapping: %s", err)
            return

        for row in mappings_data:
            vsn700 = row.get("REST Name (VSN700)")
            vsn300 = row.get("REST Name (VSN300)")
            ha_entity = row.get("HA Name")

            if vsn700 == "N/A":
                vsn700 = None
            if vsn300 == "N/A":
                vsn300 = None

            sunspec = row.get("SunSpec Normalized Name")
            if sunspec == "N/A":
                sunspec = None

            if not ha_entity:
                continue

            entity_category = row.get("Entity Category") or None
            if entity_category == "":
                entity_category = None

            mapping = PointMapping(
                vsn700_name=vsn700,
                vsn300_name=vsn300,
                sunspec_name=sunspec,
                ha_entity_name=ha_entity,
                in_livedata=row.get("In /livedata") == "\u2713",
                in_feeds=row.get("In /feeds") == "\u2713",
                label=row.get("Label") or "",
                description=row.get("Description") or "",
                ha_display_name=(
                    row.get("HA Display Name") or row.get("Description") or row.get("Label") or ""
                ),
                models=row.get("models") or [],
                category=row.get("Category") or "",
                units=row.get("HA Unit of Measurement") or "",
                state_class=row.get("HA State Class") or "",
                device_class=row.get("HA Device Class") or "",
                entity_category=entity_category,
                available_in_modbus=row.get("Available in Modbus") or "",
                icon=row.get("HA Icon") or "",
                suggested_display_precision=row.get("Suggested Display Precision"),
            )

            self._mappings[ha_entity] = mapping

            if vsn300:
                self._vsn300_index[vsn300] = ha_entity
            if vsn700:
                self._vsn700_index[vsn700] = ha_entity

        self._loaded = True
        _LOGGER.info(
            "Loaded %d mappings (%d VSN300, %d VSN700)",
            len(self._mappings),
            len(self._vsn300_index),
            len(self._vsn700_index),
        )

    def get_by_vsn300(self, vsn300_name: str) -> PointMapping | None:
        """Get mapping by VSN300 point name."""
        key = self._vsn300_index.get(vsn300_name)
        return self._mappings.get(key) if key else None

    def get_by_vsn700(self, vsn700_name: str) -> PointMapping | None:
        """Get mapping by VSN700 point name."""
        key = self._vsn700_index.get(vsn700_name)
        return self._mappings.get(key) if key else None


# ── Normalizer ───────────────────────────────────────────────────────


def normalize_vsn300_point_name(point_name: str) -> str:
    """Normalize VSN300 point names (M101/M102 -> M103)."""
    if point_name.startswith(("m101_", "m102_")):
        return "m103_" + point_name[5:]
    return point_name


def normalize_vsn700_point_name(point_name: str) -> str:
    """Normalize VSN700 alternate names (e.g., TSoc -> Soc)."""
    return VSN700_NAME_NORMALIZATION.get(point_name, point_name)


def apply_value_transformations(point_name: str, point_value: Any, vsn_model: str) -> Any:
    """Apply all unit conversions and value transformations."""
    if point_value is None:
        return point_value

    # uA to mA (divide by 1000)
    if point_name in UA_TO_MA_POINTS and isinstance(point_value, (int, float)):
        point_value = point_value / 1000

    # A to mA for VSN700 leakage current (multiply by 1000)
    if (
        vsn_model == "VSN700"
        and point_name in A_TO_MA_POINTS
        and isinstance(point_value, (int, float))
        and point_value != 0
    ):
        point_value = point_value * 1000

    # Temperature scale factor correction
    if (
        point_name in TEMP_CORRECTION_POINTS
        and isinstance(point_value, (int, float))
        and point_value > TEMP_THRESHOLD_CELSIUS
    ):
        point_value = point_value / 10

    # String cleanup - strip dashes
    if point_name in STRING_STRIP_POINTS and isinstance(point_value, str):
        point_value = point_value.strip("-")

    # Title case normalization
    if point_name in TITLE_CASE_POINTS and isinstance(point_value, str):
        point_value = point_value.title()

    # Bytes to MB
    if point_name in B_TO_MB_POINTS and isinstance(point_value, (int, float)):
        point_value = point_value / 1048576

    return point_value


def translate_state(point_name: str, value: Any) -> str | None:
    """Translate Aurora state codes to human-readable text."""
    state_map = STATE_ENTITY_MAPPINGS.get(point_name)
    if state_map and isinstance(value, (int, float)):
        int_value = int(value)
        return state_map.get(int_value, f"Unknown ({int_value})")
    return None


def normalize_livedata(
    livedata: dict[str, Any],
    vsn_model: str,
    mapping_loader: MappingLoader,
) -> dict[str, Any]:
    """Normalize VSN livedata to SunSpec schema with HA metadata."""
    normalized: dict[str, Any] = {"devices": {}}

    for device_id, device_data in livedata.items():
        if "points" not in device_data:
            continue

        # Use logger S/N instead of MAC for datalogger
        actual_device_id = device_id
        if ":" in device_id:
            for point in device_data["points"]:
                if point.get("name") == "sn":
                    actual_device_id = point.get("value", device_id)
                    break

        normalized_points = {}
        unmapped_points = []

        for point in device_data["points"]:
            point_name = point.get("name")
            point_value = point.get("value")

            if not point_name:
                continue

            # Apply value transformations
            point_value = apply_value_transformations(point_name, point_value, vsn_model)

            # Translate state codes
            state_text = translate_state(point_name, point_value)

            # Normalize point name for mapping lookup
            if vsn_model == "VSN300":
                lookup_name = normalize_vsn300_point_name(point_name)
                mapping = mapping_loader.get_by_vsn300(lookup_name)
            else:
                lookup_name = normalize_vsn700_point_name(point_name)
                mapping = mapping_loader.get_by_vsn700(lookup_name)

            if not mapping:
                unmapped_points.append(point_name)
                continue

            # Energy conversion: Wh -> kWh (check device_class, not units)
            unit_to_use = mapping.units
            if mapping.device_class == "energy" and point_value is not None:
                if isinstance(point_value, (int, float)) and point_value != 0:
                    point_value = point_value / 1000
                    unit_to_use = "kWh"

            # Build normalized point
            models_str = ", ".join(mapping.models) if mapping.models else ""
            vsn300_compatible = mapping.vsn300_name not in (None, "N/A", "")
            vsn700_compatible = mapping.vsn700_name not in (None, "N/A", "")

            normalized_point: dict[str, Any] = {
                "value": point_value,
                "label": mapping.label,
                "description": mapping.description,
                "ha_display_name": mapping.ha_display_name,
                "units": unit_to_use,
                "device_class": mapping.device_class,
                "state_class": mapping.state_class,
                "entity_category": mapping.entity_category,
                "category": mapping.category,
                "sunspec_model": models_str,
                "sunspec_name": mapping.sunspec_name,
                "vsn300_rest_name": mapping.vsn300_name,
                "vsn700_rest_name": mapping.vsn700_name,
                "vsn300_compatible": vsn300_compatible,
                "vsn700_compatible": vsn700_compatible,
                "icon": mapping.icon,
                "suggested_display_precision": (mapping.suggested_display_precision),
            }

            # Add state translation if applicable
            if state_text is not None:
                normalized_point["state_text"] = state_text

            normalized_points[mapping.ha_entity_name] = normalized_point

        if unmapped_points:
            _LOGGER.debug(
                "Device %s: %d unmapped points: %s",
                actual_device_id,
                len(unmapped_points),
                ", ".join(unmapped_points[:10])
                + (
                    f" ... and {len(unmapped_points) - 10} more"
                    if len(unmapped_points) > 10
                    else ""
                ),
            )

        if normalized_points:
            normalized["devices"][actual_device_id] = {
                "device_type": device_data.get("device_type", "unknown"),
                "point_count": len(normalized_points),
                "points": normalized_points,
            }

    total_points = sum(len(d["points"]) for d in normalized["devices"].values())
    _LOGGER.info(
        "Normalized %d devices with %d total points",
        len(normalized["devices"]),
        total_points,
    )

    return normalized


# ── Output Formatting ────────────────────────────────────────────────


def format_discovery(discovery: DiscoveryResult) -> dict[str, Any]:
    """Format discovery result for display."""
    result: dict[str, Any] = {
        "vsn_model": discovery.vsn_model,
        "requires_auth": discovery.requires_auth,
        "logger_sn": discovery.logger_sn,
        "logger_model": discovery.logger_model,
        "firmware_version": discovery.firmware_version,
        "hostname": discovery.hostname,
        "device_count": len(discovery.devices),
        "devices": [],
    }

    for device in discovery.devices:
        result["devices"].append(
            {
                "device_id": device.device_id,
                "raw_device_id": device.raw_device_id,
                "device_type": device.device_type,
                "device_model": device.device_model,
                "manufacturer": device.manufacturer,
                "firmware_version": device.firmware_version,
                "is_datalogger": device.is_datalogger,
            }
        )

    return result


def save_json(data: Any, filepath: str) -> None:
    """Save data to JSON file."""
    with Path(filepath).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    _LOGGER.info("Saved: %s", filepath)


# ── Main ─────────────────────────────────────────────────────────────


async def main(args: argparse.Namespace) -> int:
    """Run the VSN REST client."""
    print("\n" + "=" * 60)
    print(" ABB/FIMER VSN REST Client - Standalone Test Script")
    print("=" * 60)

    base_url = f"http://{args.host}"
    _LOGGER.info("Host: %s", args.host)
    _LOGGER.info("Username: %s", args.username)

    # Step 1: Socket check
    _LOGGER.info("Checking connectivity...")
    try:
        check_socket_connection(base_url, timeout=5)
    except VSNConnectionError as err:
        _LOGGER.error("Connectivity check failed: %s", err)
        return 1

    async with aiohttp.ClientSession() as session:
        # Step 2: Discovery (detect model + find all devices)
        _LOGGER.info("Running device discovery...")
        try:
            discovery = await discover_vsn_device(
                session, base_url, args.username, args.password, args.timeout
            )
        except VSNClientError as err:
            _LOGGER.error("Discovery failed: %s", err)
            return 1

        discovery_data = format_discovery(discovery)
        print("\n" + json.dumps(discovery_data, indent=2, default=str))
        save_json(
            discovery_data,
            f"{discovery.vsn_model.lower()}_discovery.json",
        )

        # Step 3: Fetch raw data
        _LOGGER.info("Fetching status...")
        status = await fetch_endpoint(
            session,
            base_url,
            ENDPOINT_STATUS,
            discovery.vsn_model,
            args.username,
            args.password,
            args.timeout,
            discovery.requires_auth,
        )
        save_json(status, f"{discovery.vsn_model.lower()}_status.json")

        _LOGGER.info("Fetching livedata...")
        livedata = await fetch_endpoint(
            session,
            base_url,
            ENDPOINT_LIVEDATA,
            discovery.vsn_model,
            args.username,
            args.password,
            args.timeout,
            discovery.requires_auth,
        )
        save_json(livedata, f"{discovery.vsn_model.lower()}_livedata.json")

        _LOGGER.info("Fetching feeds...")
        try:
            feeds = await fetch_endpoint(
                session,
                base_url,
                ENDPOINT_FEEDS,
                discovery.vsn_model,
                args.username,
                args.password,
                args.timeout,
                discovery.requires_auth,
            )
            save_json(feeds, f"{discovery.vsn_model.lower()}_feeds.json")
        except VSNClientError:
            _LOGGER.warning("Feeds endpoint not available")

        # Step 4: Normalize data
        _LOGGER.info("Loading mapping and normalizing data...")
        mapping_loader = MappingLoader()
        await mapping_loader.async_load(session)

        if mapping_loader._loaded:  # noqa: SLF001
            normalized = normalize_livedata(livedata, discovery.vsn_model, mapping_loader)
            save_json(
                normalized,
                f"{discovery.vsn_model.lower()}_normalized.json",
            )

            # Summary
            print("\n" + "=" * 60)
            print(" Normalization Summary")
            print("=" * 60)
            for dev_id, dev_data in normalized.get("devices", {}).items():
                print(
                    f"  Device {dev_id} ({dev_data.get('device_type', '?')}): "
                    f"{dev_data.get('point_count', 0)} normalized points"
                )

                # Show state translations
                for _pt_name, pt_data in dev_data.get("points", {}).items():
                    if "state_text" in pt_data:
                        print(
                            f"    {pt_data.get('ha_display_name', _pt_name)}: "
                            f"{pt_data['value']} -> {pt_data['state_text']}"
                        )
        else:
            _LOGGER.warning("Mapping not loaded - skipping normalization")

    if args.verbose:
        print("\n" + "=" * 60)
        print(" Raw Status Data")
        print("=" * 60)
        print(json.dumps(status, indent=2, default=str))

    print("\n" + "=" * 60)
    print(" Output Files")
    print("=" * 60)
    model = discovery.vsn_model.lower()
    print(f"  {model}_discovery.json  - Device discovery results")
    print(f"  {model}_status.json     - Raw status data")
    print(f"  {model}_livedata.json   - Raw livedata")
    print(f"  {model}_feeds.json      - Raw feeds data")
    print(f"  {model}_normalized.json - Normalized data with HA metadata")
    print()

    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "ABB/FIMER VSN REST Client - Test connectivity, discovery, and data normalization"
        ),
    )
    parser.add_argument(
        "--host",
        required=True,
        help="VSN datalogger IP address or hostname",
    )
    parser.add_argument(
        "--username",
        default=DEFAULT_USERNAME,
        help=f"Authentication username (default: {DEFAULT_USERNAME})",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Authentication password (default: empty)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show full raw API response data",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    if cli_args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    sys.exit(asyncio.run(main(cli_args)))
