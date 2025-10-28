"""Utility functions for VSN REST client."""

import asyncio
import logging
import socket
from urllib.parse import urlparse

try:
    from .exceptions import VSNConnectionError
except ImportError:
    from exceptions import VSNConnectionError

_LOGGER = logging.getLogger(__name__)


async def check_socket_connection(
    base_url: str,
    timeout: int = 5,
) -> None:
    """Check if TCP socket connection is possible before HTTP request.

    Performs a quick socket connection test to fail fast when device is offline.
    This avoids waiting for full HTTP timeout when device is unreachable.

    Args:
        base_url: Base URL of device (e.g., "http://192.168.1.100")
        timeout: Socket connection timeout in seconds (default: 5)

    Raises:
        VSNConnectionError: If socket connection fails

    Example:
        >>> await check_socket_connection("http://192.168.1.100", timeout=5)
        # Returns silently if connection succeeds
        # Raises VSNConnectionError if connection fails

    """
    # Parse URL to extract hostname and port
    parsed = urlparse(base_url)
    hostname = parsed.hostname or parsed.netloc.split(":")[0]
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Remove any trailing path/query components
    hostname = hostname.replace("http://", "").replace("https://", "").split("/")[0]

    _LOGGER.debug("Checking socket connection to %s:%d", hostname, port)

    try:
        # Run socket connection in executor (blocking operation)
        sock = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: socket.create_connection((hostname, port), timeout=timeout),
            ),
            timeout=timeout,
        )
        sock.close()
        _LOGGER.debug("Socket connection to %s:%d successful", hostname, port)

    except TimeoutError as err:
        msg = f"Timeout connecting to {hostname}:{port}"
        _LOGGER.info("%s - device may be offline", msg)
        raise VSNConnectionError(msg) from err

    except (OSError, ConnectionRefusedError, ConnectionError) as err:
        msg = f"Cannot connect to {hostname}:{port}"
        _LOGGER.info("%s - %s", msg, err)
        raise VSNConnectionError(f"{msg}: {err}") from err
