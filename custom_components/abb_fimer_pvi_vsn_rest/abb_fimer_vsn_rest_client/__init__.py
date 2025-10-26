"""ABB FIMER VSN REST Client Library."""

from .exceptions import (
    VSNClientError,
    VSNAuthenticationError,
    VSNConnectionError,
    VSNDetectionError,
)

__all__ = [
    "VSNClientError",
    "VSNAuthenticationError",
    "VSNConnectionError",
    "VSNDetectionError",
]
