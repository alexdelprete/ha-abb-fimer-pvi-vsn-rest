"""Data update coordinator for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .abb_fimer_vsn_rest_client.client import ABBFimerVSNRestClient
from .abb_fimer_vsn_rest_client.discovery import DiscoveredDevice, DiscoveryResult
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_RECOVERY_SCRIPT,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DOMAIN,
)
from .repairs import create_connection_issue, create_recovery_notification, delete_connection_issue

_LOGGER = logging.getLogger(__name__)


class ABBFimerPVIVSNRestCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data updates from VSN device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ABBFimerVSNRestClient,
        update_interval: timedelta,
        discovery_result: DiscoveryResult | None = None,
        entry_id: str | None = None,
        host: str | None = None,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            client: VSN REST API client
            update_interval: How often to fetch data
            discovery_result: Optional discovery result from initial setup
            entry_id: Config entry ID for repair issues
            host: Device host for repair issues
            config_entry: Config entry for accessing options

        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.vsn_model: str | None = discovery_result.vsn_model if discovery_result else None
        self.discovery_result: DiscoveryResult | None = discovery_result
        self.discovered_devices: list[DiscoveredDevice] = (
            discovery_result.devices if discovery_result else []
        )

        # Failure tracking for repair issues
        self._entry_id = entry_id
        self._host = host
        self._consecutive_failures = 0
        self._repair_issue_created = False
        self._failure_start_time: float | None = None
        self._last_error_type: str | None = None
        self._recovery_script_executed = False
        self._script_executed_time: float | None = None

        # Device trigger tracking
        self.device_id: str | None = None

        # Repair notification options from config entry
        if config_entry:
            self._enable_repair_notification = config_entry.options.get(
                CONF_ENABLE_REPAIR_NOTIFICATION, DEFAULT_ENABLE_REPAIR_NOTIFICATION
            )
            self._failures_threshold = config_entry.options.get(
                CONF_FAILURES_THRESHOLD, DEFAULT_FAILURES_THRESHOLD
            )
            self._recovery_script = config_entry.options.get(
                CONF_RECOVERY_SCRIPT, DEFAULT_RECOVERY_SCRIPT
            )
        else:
            self._enable_repair_notification = DEFAULT_ENABLE_REPAIR_NOTIFICATION
            self._failures_threshold = DEFAULT_FAILURES_THRESHOLD
            self._recovery_script = DEFAULT_RECOVERY_SCRIPT

        _LOGGER.debug(
            "Repair notification options: enabled=%s, threshold=%s, script=%s",
            self._enable_repair_notification,
            self._failures_threshold,
            self._recovery_script,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from VSN device.

        Returns:
            Normalized data structure from the client

        Raises:
            UpdateFailed: If data fetch fails

        """
        try:
            # Ensure client is connected and model is detected
            if not self.vsn_model:
                self.vsn_model = await self.client.connect()
                _LOGGER.info("Connected to %s", self.vsn_model)

            # Fetch normalized data (includes mapping to HA entities)
            data = await self.client.get_normalized_data()

            _LOGGER.debug(
                "Successfully fetched data: %d devices",
                len(data.get("devices", {})),
            )

            # Handle recovery after repair issue was created
            if self._repair_issue_created:
                await self._handle_recovery()

            # Reset failure counter on success
            self._consecutive_failures = 0

            return data  # noqa: TRY300

        except VSNAuthenticationError as err:
            self._handle_failure("device_unreachable", err)
            raise UpdateFailed(f"Authentication failed: {err}") from err

        except VSNConnectionError as err:
            self._handle_failure("device_unreachable", err)
            raise UpdateFailed(f"Connection error: {err}") from err

        except VSNClientError as err:
            self._handle_failure("device_not_responding", err)
            raise UpdateFailed(f"Client error: {err}") from err

        except Exception as err:
            self._handle_failure("device_unreachable", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _handle_failure(self, error_type: str, error: Exception) -> None:
        """Handle a data fetch failure.

        Args:
            error_type: Type of error for device trigger
            error: The exception that occurred

        """
        self._consecutive_failures += 1
        self._last_error_type = error_type

        _LOGGER.debug(
            "Update error (failure %d/%d): %s",
            self._consecutive_failures,
            self._failures_threshold,
            error,
        )

        # Create repair issue after threshold reached
        if (
            self._consecutive_failures >= self._failures_threshold
            and not self._repair_issue_created
            and self._entry_id
        ):
            # Record failure start time for downtime tracking
            self._failure_start_time = time.time()

            # Fire device trigger event
            self._fire_device_event(
                error_type,
                {
                    "error": str(error),
                    "failures_threshold": self._failures_threshold,
                },
            )

            # Create repair issue (if enabled)
            if self._enable_repair_notification:
                device_name = self._get_device_name()
                create_connection_issue(
                    self.hass,
                    self._entry_id,
                    device_name,
                    self._host or "unknown",
                )
                _LOGGER.info(
                    "Repair issue created after %d consecutive failures",
                    self._consecutive_failures,
                )

            self._repair_issue_created = True

            # Execute recovery script if configured
            if self._recovery_script:
                self.hass.async_create_task(self._execute_recovery_script())

    async def _handle_recovery(self) -> None:
        """Handle recovery after connection was restored."""
        # Calculate downtime
        downtime_seconds = 0
        if self._failure_start_time:
            downtime_seconds = int(time.time() - self._failure_start_time)

        # Format times using locale-aware format
        ended_at = dt_util.as_local(dt_util.utcnow()).strftime("%X")
        started_at = ""
        if self._failure_start_time:
            started_at = dt_util.as_local(
                dt_util.utc_from_timestamp(self._failure_start_time)
            ).strftime("%X")
        downtime = self._format_downtime(downtime_seconds)

        # Get script execution time if script was executed
        script_executed_at = None
        if self._recovery_script_executed and self._script_executed_time:
            script_executed_at = dt_util.as_local(
                dt_util.utc_from_timestamp(self._script_executed_time)
            ).strftime("%X")

        # Fire device_recovered event
        self._fire_device_event(
            "device_recovered",
            {
                "previous_failures": self._consecutive_failures,
                "downtime_seconds": downtime_seconds,
            },
        )

        # Delete connection issue and create recovery notification
        if self._entry_id:
            delete_connection_issue(self.hass, self._entry_id)
            _LOGGER.info(
                "Connection restored, repair issue deleted (downtime: %s)",
                downtime,
            )

            # Create recovery notification (if notifications are enabled)
            if self._enable_repair_notification:
                device_name = self._get_device_name()
                create_recovery_notification(
                    self.hass,
                    self._entry_id,
                    device_name,
                    started_at=started_at,
                    ended_at=ended_at,
                    downtime=downtime,
                    script_name=self._recovery_script if self._recovery_script_executed else None,
                    script_executed_at=script_executed_at,
                )

        # Reset tracking variables
        self._repair_issue_created = False
        self._failure_start_time = None
        self._last_error_type = None
        self._recovery_script_executed = False
        self._script_executed_time = None

    async def _execute_recovery_script(self) -> None:
        """Execute the configured recovery script."""
        if not self._recovery_script:
            return

        try:
            # Extract script name from entity_id (e.g., "script.restart_wifi" -> "restart_wifi")
            script_name = self._recovery_script.replace("script.", "")

            _LOGGER.info(
                "Executing recovery script: %s for device %s",
                self._recovery_script,
                self._get_device_name(),
            )

            # Call the script with device information as variables
            await self.hass.services.async_call(
                domain="script",
                service=script_name,
                service_data={
                    "device_name": self._get_device_name(),
                    "host": self._host or "",
                    "vsn_model": self.vsn_model or "",
                    "logger_sn": self.discovery_result.logger_sn if self.discovery_result else "",
                    "failures_count": self._consecutive_failures,
                },
                blocking=False,  # Don't wait for script completion
            )

            self._recovery_script_executed = True
            self._script_executed_time = time.time()
            _LOGGER.info(
                "Recovery script executed successfully: %s",
                self._recovery_script,
            )
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Failed to execute recovery script %s: %s",
                self._recovery_script,
                err,
            )

    def _get_device_name(self) -> str:
        """Get a display name for the device."""
        if self.discovery_result:
            return f"{self.discovery_result.vsn_model} ({self.discovery_result.logger_sn})"
        return self._host or "VSN Device"

    def _format_downtime(self, seconds: int) -> str:
        """Format downtime in compact format (e.g., '5m 23s')."""
        if seconds < 60:
            return f"{seconds}s"
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        hours, mins = divmod(minutes, 60)
        if mins:
            return f"{hours}h {mins}m"
        return f"{hours}h"

    def _fire_device_event(self, event_type: str, extra_data: dict[str, Any] | None = None) -> None:
        """Fire a device event on the HA event bus for device triggers."""
        if not self.device_id:
            _LOGGER.debug(
                "Cannot fire event, device_id not set: %s",
                event_type,
            )
            return

        event_data: dict[str, Any] = {
            "device_id": self.device_id,
            "type": event_type,
            "host": self._host or "",
            "vsn_model": self.vsn_model or "",
        }
        if self.discovery_result:
            event_data["logger_sn"] = self.discovery_result.logger_sn

        if extra_data:
            event_data.update(extra_data)

        self.hass.bus.async_fire(f"{DOMAIN}_event", event_data)
        _LOGGER.debug(
            "Device event fired: %s for device %s",
            event_type,
            self.device_id,
        )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        _LOGGER.debug("Shutting down coordinator")
        await self.client.close()
