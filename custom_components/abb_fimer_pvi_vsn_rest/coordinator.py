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
from .abb_fimer_vsn_rest_client.discovery import (
    DiscoveredDevice,
    DiscoveryResult,
    discover_vsn_device,
)
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNClientError,
    VSNConnectionError,
)
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_KNOWN_DEVICES,
    CONF_RECOVERY_SCRIPT,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DOMAIN,
)
from .repairs import (
    create_connection_issue,
    create_partial_discovery_issue,
    create_recovery_notification,
    delete_connection_issue,
    delete_partial_discovery_issue,
)

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
        missing_devices: set[str] | None = None,
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
            missing_devices: Set of known device IDs not found during discovery

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
        self._config_entry = config_entry

        # Partial discovery tracking
        self._missing_devices: set[str] = missing_devices or set()
        self._reload_scheduled = False
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

            # --- Re-discovery and idempotency checks ---
            if not self._reload_scheduled:
                # Check 1: Re-discover missing known devices
                if self._missing_devices:
                    await self._attempt_rediscovery()

                # Check 2: Detect unknown devices in data (idempotency)
                if not self._reload_scheduled and self._config_entry:
                    data_device_ids = set(data.get("devices", {}).keys())
                    known_device_ids = {
                        d["device_id"] for d in self._config_entry.data.get(CONF_KNOWN_DEVICES, [])
                    }
                    unknown_devices = data_device_ids - known_device_ids
                    if unknown_devices:
                        _LOGGER.info(
                            "Unknown devices detected in data: %s — scheduling reload",
                            ", ".join(sorted(unknown_devices)),
                        )
                        self._reload_scheduled = True
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(self._entry_id)
                        )

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

    async def _attempt_rediscovery(self) -> None:
        """Attempt to re-discover missing devices.

        Runs discover_vsn_device() to check if previously missing devices are now
        available. On full recovery, schedules a config entry reload to create entities.
        """
        if not self._missing_devices or self._reload_scheduled:
            return

        try:
            discovery_result = await discover_vsn_device(
                session=self.client.session,
                base_url=self.client.base_url,
                username=self.client.username,
                password=self.client.password,
                timeout=self.client.timeout,
            )

            discovered_ids = {d.device_id for d in discovery_result.devices}
            recovered = self._missing_devices & discovered_ids

            if not recovered:
                _LOGGER.debug(
                    "Re-discovery: %d devices still missing",
                    len(self._missing_devices),
                )
                return

            _LOGGER.info(
                "Re-discovery found previously missing devices: %s",
                ", ".join(sorted(recovered)),
            )

            # Sync all components with new discovery state
            self._update_discovery_state(discovery_result)
            self._missing_devices -= recovered

            # Sync known_devices in config_entry.data
            self._sync_known_devices(discovery_result)

            # Handle recovery outcome
            if not self._missing_devices:
                self._handle_full_recovery()
            else:
                self._handle_partial_recovery()

        except (VSNConnectionError, VSNAuthenticationError, VSNClientError):
            _LOGGER.debug("Re-discovery failed, will retry next cycle", exc_info=True)

    def _update_discovery_state(self, discovery_result: DiscoveryResult) -> None:
        """Update coordinator and client with new discovery results.

        Ensures all components (coordinator, client, device_type map) stay in sync.
        """
        self.discovery_result = discovery_result
        self.discovered_devices = discovery_result.devices
        # Keep client's device list and type map in sync
        self.client.update_discovered_devices(discovery_result.devices)

    def _sync_known_devices(self, discovery_result: DiscoveryResult) -> None:
        """Sync config_entry known_devices with newly discovered devices.

        Adds any devices found in discovery that aren't already in the persisted list.
        Also updates device_type for existing entries with stale values.
        """
        if not self._config_entry:
            return

        known_devices = list(self._config_entry.data.get(CONF_KNOWN_DEVICES, []))
        known_ids = {d["device_id"] for d in known_devices}
        changed = False

        # Update device_type for existing entries where discovery has better info
        discovered_by_id = {d.device_id: d for d in discovery_result.devices}
        for known in known_devices:
            discovered = discovered_by_id.get(known["device_id"])
            if discovered and known.get("device_type") != discovered.device_type:
                known["device_type"] = discovered.device_type
                known["is_datalogger"] = discovered.is_datalogger
                changed = True

        # Add newly discovered devices not yet in known list
        for device in discovery_result.devices:
            if device.device_id not in known_ids:
                known_devices.append(
                    {
                        "device_id": device.device_id,
                        "device_type": device.device_type,
                        "is_datalogger": device.is_datalogger,
                    }
                )
                changed = True

        if changed:
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, CONF_KNOWN_DEVICES: known_devices},
            )

    def _handle_full_recovery(self) -> None:
        """Handle full recovery when all missing devices are found."""
        if self._entry_id:
            delete_partial_discovery_issue(self.hass, self._entry_id)
        _LOGGER.info("All known devices recovered, scheduling reload")
        self._reload_scheduled = True
        self.hass.async_create_task(self.hass.config_entries.async_reload(self._entry_id))

    def _handle_partial_recovery(self) -> None:
        """Handle partial recovery when some devices are still missing."""
        _LOGGER.info(
            "Still missing %d devices: %s",
            len(self._missing_devices),
            ", ".join(sorted(self._missing_devices)),
        )
        if self._entry_id:
            device_name = self._get_device_name()
            create_partial_discovery_issue(
                self.hass,
                self._entry_id,
                device_name,
                sorted(self._missing_devices),
            )

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
