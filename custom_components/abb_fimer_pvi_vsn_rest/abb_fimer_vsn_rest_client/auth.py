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
    from .constants import ENDPOINT_LIVEDATA, ENDPOINT_STATUS
    from .exceptions import (
        VSNAuthenticationError,
        VSNConnectionError,
        VSNDetectionError,
    )
    from .utils import check_socket_connection
except ImportError:
    from constants import ENDPOINT_LIVEDATA, ENDPOINT_STATUS
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
    uri: str = ENDPOINT_LIVEDATA,
    method: str = "GET",
    timeout: int = 10,
) -> str:
    """Get VSN300 X-Digest authentication header.

    Args:
        session: aiohttp client session
        base_url: Base URL of VSN300
        username: Username
        password: Password
        uri: Request URI (default: ENDPOINT_LIVEDATA)
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

    _LOGGER.debug(
        "[VSN300 Auth] Requesting digest challenge: method=%s, url=%s, timeout=%ds",
        method,
        url,
        timeout,
    )

    try:
        # Make unauthenticated request to get challenge
        async with session.request(
            method,
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            # Log response details
            _LOGGER.debug(
                "[VSN300 Auth] Challenge response: status=%d, headers=%s",
                response.status,
                dict(response.headers),
            )

            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "")

                # Log raw challenge header
                _LOGGER.debug(
                    "[VSN300 Auth] WWW-Authenticate header (raw): %s",
                    repr(www_authenticate) if www_authenticate else "NOT PRESENT",
                )

                if not www_authenticate or "digest" not in www_authenticate.lower():
                    _LOGGER.error(
                        "[VSN300 Auth] Invalid or missing digest challenge. "
                        "WWW-Authenticate: %s, All headers: %s",
                        repr(www_authenticate),
                        dict(response.headers),
                    )
                    raise VSNAuthenticationError(
                        "VSN300 challenge missing or not digest-based. Enable debug logging for details."
                    )

                # Parse challenge
                challenge_params = parse_digest_challenge(www_authenticate)
                _LOGGER.debug(
                    "[VSN300 Auth] Parsed challenge params: realm=%s, nonce=%s, qop=%s, algorithm=%s",
                    challenge_params.get("realm"),
                    challenge_params.get("nonce", "")[:20] + "..."
                    if challenge_params.get("nonce")
                    else None,
                    challenge_params.get("qop"),
                    challenge_params.get("algorithm"),
                )

                # Build digest header
                digest_value = build_digest_header(
                    username, password, challenge_params, method, uri
                )

                # Log digest generation (sanitized - don't log the full digest or password)
                _LOGGER.debug(
                    "[VSN300 Auth] Generated X-Digest header for username=%s (length=%d chars)",
                    username,
                    len(digest_value) if digest_value else 0,
                )
                return digest_value

            # Got non-401 response
            _LOGGER.error(
                "[VSN300 Auth] Expected 401 challenge response, got %d. Headers: %s",
                response.status,
                dict(response.headers),
            )
            raise VSNAuthenticationError(
                f"Expected 401 challenge, got {response.status}"
            )
    except aiohttp.ClientError as err:
        _LOGGER.debug(
            "[VSN300 Auth] Connection error during challenge: %s (type=%s)",
            err,
            type(err).__name__,
        )
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

    detection_url = f"{base_url}{ENDPOINT_STATUS}"
    protocol = "HTTPS" if base_url.startswith("https") else "HTTP"
    _LOGGER.debug(
        "[VSN Detection] Making unauthenticated request to %s (protocol=%s, timeout=%ds)",
        detection_url,
        protocol,
        timeout,
    )

    try:
        # Make unauthenticated request to ENDPOINT_STATUS to trigger 401 with WWW-Authenticate
        async with session.get(
            detection_url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            # Log complete response details for debugging
            _LOGGER.debug(
                "[VSN Detection] Response received: status=%d, headers=%s",
                response.status,
                dict(response.headers),
            )

            if response.status == 401:
                www_authenticate = response.headers.get("WWW-Authenticate", "").lower()
                www_authenticate_raw = response.headers.get("WWW-Authenticate", "")

                # Log raw WWW-Authenticate header value
                _LOGGER.debug(
                    "[VSN Detection] WWW-Authenticate header (raw): %s",
                    repr(www_authenticate_raw)
                    if www_authenticate_raw
                    else "NOT PRESENT",
                )

                # Check for digest authentication (VSN300) - unique identifier
                if www_authenticate and (
                    "x-digest" in www_authenticate or "digest" in www_authenticate
                ):
                    _LOGGER.info(
                        "[VSN Detection] Detected VSN300 (digest auth in WWW-Authenticate: %s)",
                        www_authenticate_raw,
                    )
                    return "VSN300"

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
                            "[VSN Detection] Preemptive auth response: status=%d, headers=%s",
                            auth_response.status,
                            dict(auth_response.headers),
                        )

                        # Check if preemptive Basic auth succeeded
                        if auth_response.status in (200, 204):
                            _LOGGER.info(
                                "[VSN Detection] Detected VSN700 (preemptive Basic authentication)"
                            )
                            return "VSN700"

                        # Preemptive auth failed
                        _LOGGER.error(
                            "[VSN Detection] Preemptive Basic auth failed with status %d. "
                            "WWW-Authenticate: %s. Device is not compatible.",
                            auth_response.status,
                            repr(www_authenticate_raw)
                            if www_authenticate_raw
                            else "NOT PRESENT",
                        )
                        raise VSNDetectionError(
                            f"Device authentication failed. Not VSN300/VSN700 compatible. "
                            f"Preemptive Basic auth returned {auth_response.status}. "
                            "Enable debug logging for details."
                        )

                except aiohttp.ClientError as auth_err:
                    _LOGGER.error(
                        "[VSN Detection] Preemptive Basic auth connection error: %s. "
                        "WWW-Authenticate was: %s",
                        auth_err,
                        repr(www_authenticate_raw)
                        if www_authenticate_raw
                        else "NOT PRESENT",
                    )
                    raise VSNDetectionError(
                        f"Device authentication connection failed: {auth_err}"
                    ) from auth_err

            # Got non-401 response
            _LOGGER.error(
                "[VSN Detection] Expected 401 response for detection, got %d. Headers: %s",
                response.status,
                dict(response.headers),
            )
            raise VSNDetectionError(
                f"Expected 401 response for detection, got {response.status}"
            )
    except aiohttp.ClientError as err:
        _LOGGER.debug(
            "[VSN Detection] Connection error: %s (type=%s)",
            err,
            type(err).__name__,
        )
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
