"""ABB FIMER VSN REST Client Library."""

from .exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
    VSNDetectionError,
)

__all__ = [
    "VSNAuthenticationError",
    "VSNClientError",
    "VSNConnectionError",
    "VSNDetectionError",
]
