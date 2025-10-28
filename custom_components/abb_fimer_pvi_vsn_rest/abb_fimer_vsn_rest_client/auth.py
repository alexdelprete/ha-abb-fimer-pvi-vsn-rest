"""VSN authentication and model detection.

VSN300: Uses HTTP Digest authentication with custom X-Digest header
VSN700: Uses HTTP Basic authentication (preemptive)

Both models use /v1/* endpoints:
- /v1/status (for device detection)
- /v1/livedata (for live data)
- /v1/feeds (for feed configuration)
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import time

import aiohttp

try:
    from .exceptions import (
        VSNAuthenticationError,
        VSNConnectionError,
        VSNDetectionError,
    )
    from .utils import check_socket_connection
except ImportError:
    from exceptions import VSNAuthenticationError, VSNConnectionError, VSNDetectionError
    from utils import check_socket_connection

_LOGGER = logging.getLogger(__name__)


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
    """Calculate HTTP Digest authentication response.

    Args:
        username: Username
        password: Password
        realm: Authentication realm from challenge
        nonce: Nonce from challenge
        method: HTTP method (GET, POST, etc.)
        uri: Request URI
        qop: Quality of protection from challenge
        nc: Nonce count (hex string)
        cnonce: Client nonce

    Returns:
        Calculated digest response value

    """
    # Calculate HA1 = MD5(username:realm:password)
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()

    # Calculate HA2 = MD5(method:uri)
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

    # Calculate response
    if qop and nc and cnonce:
        # With qop (quality of protection)
        response_str = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        # Without qop (simple digest)
        response_str = f"{ha1}:{nonce}:{ha2}"

    return hashlib.md5(response_str.encode()).hexdigest()


def parse_digest_challenge(www_authenticate: str) -> dict[str, str]:
    """Parse WWW-Authenticate digest challenge header.

    Args:
        www_authenticate: WWW-Authenticate header value

    Returns:
        Dictionary of challenge parameters

    """
    # Remove 'Digest ' or 'X-Digest ' prefix
    challenge = re.sub(
        r"^(Digest|X-Digest)\s+", "", www_authenticate, flags=re.IGNORECASE
    )

    # Parse key="value" pairs
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
    """Build X-Digest authentication header value.

    Args:
        username: Username
        password: Password
        challenge_params: Parsed challenge parameters from WWW-Authenticate
        method: HTTP method
        uri: Request URI

    Returns:
        Complete X-Digest header value

    """
    realm = challenge_params.get("realm", "")
    nonce = challenge_params.get("nonce", "")
    qop = challenge_params.get("qop")
    opaque = challenge_params.get("opaque")

    # For VSN300, we typically don't use qop, but handle it if present
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
            f"qop={qop}",  # No quotes around qop value
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
    """Get VSN300 X-Digest authentication header.

    Args:
        session: aiohttp client session
        base_url: Base URL of VSN300
        username: Username
        password: Password
        uri: Request URI (default: /v1/livedata)
        method: HTTP method (default: GET)
        timeout: Request timeout in seconds

    Returns:
        X-Digest header value

    Raises:
        VSNAuthenticationError: If challenge fails

    """
    # Check socket connection before HTTP request
    await check_socket_connection(base_url, timeout=5)

    url = f"{base_url.rstrip('/')}{uri}"

    try:
        # Make unauthenticated request to get challenge
        async with session.request(
            method,
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "")

                if not www_authenticate or "digest" not in www_authenticate.lower():
                    raise VSNAuthenticationError(
                        "VSN300 challenge missing or not digest-based"
                    )

                # Parse challenge
                challenge_params = parse_digest_challenge(www_authenticate)
                _LOGGER.debug("Challenge params: %s", challenge_params)

                # Build digest header
                digest_value = build_digest_header(
                    username, password, challenge_params, method, uri
                )

                _LOGGER.debug("VSN300 X-Digest header generated: %s", digest_value)
                return digest_value
            raise VSNAuthenticationError(
                f"Expected 401 challenge, got {response.status}"
            )
    except aiohttp.ClientError as err:
        raise VSNConnectionError(f"VSN300 challenge request failed: {err}") from err


async def detect_vsn_model(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str,
    password: str,
    timeout: int = 10,
) -> str:
    """Detect VSN model by examining WWW-Authenticate header.

    Makes an unauthenticated request to /v1/status and examines the 401 response's
    WWW-Authenticate header to determine device type:
    - VSN300: Contains "x-digest" or "digest"
    - VSN700: Contains "basic"

    Args:
        session: aiohttp client session
        base_url: Base URL of the VSN device
        username: Username for authentication (not used for detection)
        password: Password for authentication (not used for detection)
        timeout: Request timeout in seconds

    Returns:
        "VSN300" or "VSN700"

    Raises:
        VSNDetectionError: If detection fails
        VSNConnectionError: If connection fails

    """
    base_url = base_url.rstrip("/")

    # Check socket connection before HTTP request
    await check_socket_connection(base_url, timeout=5)

    try:
        # Make unauthenticated request to /v1/status to trigger 401 with WWW-Authenticate
        async with session.get(
            f"{base_url}/v1/status",
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "").lower()

                if not www_authenticate:
                    raise VSNDetectionError(
                        "Device returned 401 but no WWW-Authenticate header found"
                    )

                # Check for digest authentication (VSN300)
                if "x-digest" in www_authenticate or "digest" in www_authenticate:
                    _LOGGER.info("Detected VSN300 (digest auth in WWW-Authenticate)")
                    return "VSN300"

                # Check for basic authentication (VSN700)
                if "basic" in www_authenticate:
                    _LOGGER.info("Detected VSN700 (basic auth in WWW-Authenticate)")
                    return "VSN700"

                raise VSNDetectionError(
                    f"Unknown authentication scheme in WWW-Authenticate: {www_authenticate}"
                )
            raise VSNDetectionError(
                f"Expected 401 response for detection, got {response.status}"
            )
    except aiohttp.ClientError as err:
        raise VSNConnectionError(f"Device detection connection error: {err}") from err


def get_vsn700_basic_auth(username: str, password: str) -> str:
    """Get VSN700 HTTP Basic authentication header value.

    VSN700 uses preemptive HTTP Basic authentication where credentials are
    base64-encoded and sent with every request.

    Args:
        username: Username
        password: Password

    Returns:
        Basic auth header value (base64-encoded credentials)

    """
    # Encode credentials as "username:password"
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    _LOGGER.debug("VSN700 basic auth credentials encoded")
    return encoded
