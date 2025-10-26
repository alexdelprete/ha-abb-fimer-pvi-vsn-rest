"""Exceptions for abb-fimer-vsn-rest-client."""


class VSNClientError(Exception):
    """Base exception for VSN client."""


class VSNConnectionError(VSNClientError):
    """Connection error."""


class VSNAuthenticationError(VSNClientError):
    """Authentication error."""


class VSNDetectionError(VSNClientError):
    """VSN model detection error."""
