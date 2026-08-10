"""Exceptions for abb-fimer-vsn-rest-client."""


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


class VSNUnsupportedFirmwareError(VSNClientError):
    """Datalogger firmware has a known bug that prevents operation.

    VSN300 firmware 2.0.0 drops the TCP connection on every /v1/livedata
    request (vendor regression, fixed in firmware 2.0.1). See issue #68.
    """

    def __init__(self, message: str, firmware_version: str | None = None) -> None:
        """Initialize with the offending firmware version.

        Args:
            message: Error message.
            firmware_version: The unsupported firmware version (e.g. "2.0.0").

        """
        super().__init__(message)
        self.firmware_version = firmware_version
