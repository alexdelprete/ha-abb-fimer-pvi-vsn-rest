"""Data update coordinator for ABB FIMER PVI VSN REST integration."""

from __future__ import annotations

from datetime import time as dt_time, timedelta
import logging
from statistics import median
import time
from typing import TYPE_CHECKING, Any

from astral import SunDirection
from astral.sun import elevation as astral_sun_elevation, time_at_elevation

from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_observer
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
    CONF_OUTAGE_CALIBRATION_LEGACY,
    CONF_OUTAGE_LEARNING,
    CONF_OUTAGE_MODE,
    CONF_OUTAGE_WINDOW_END,
    CONF_OUTAGE_WINDOW_START,
    CONF_RECOVERY_SCRIPT,
    DATALOGGER_SILENT_THRESHOLD,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_OUTAGE_MODE,
    DEFAULT_OUTAGE_WINDOW_END,
    DEFAULT_OUTAGE_WINDOW_START,
    DEFAULT_RECOVERY_SCRIPT,
    DOMAIN,
    OUTAGE_ELEVATION_MARGIN,
    OUTAGE_LEARNING_MAX_NIGHTS,
    OUTAGE_LEARNING_NIGHTS,
    OUTAGE_MAX_ELEVATION,
    OUTAGE_MODE_AUTO,
    OUTAGE_MODE_OFF,
    OUTAGE_MODE_WINDOW,
    OUTAGE_NIGHT_MIN_DURATION,
    OUTAGE_OUTLIER_ELEVATION,
    OUTAGE_POWER_FACTOR,
    OUTAGE_POWER_MARGIN,
    OUTAGE_STARTER_ENTRY_ELEVATION,
    OUTAGE_STARTER_ENTRY_POWER,
    OUTAGE_STARTER_EXIT_ELEVATION,
)
from .repairs import (
    create_connection_issue,
    create_datalogger_silent_issue,
    create_partial_discovery_issue,
    create_recovery_notification,
    delete_connection_issue,
    delete_datalogger_silent_issue,
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

        # Device IDs that got at least one sensor entity, set by the sensor
        # platform once its setup completes (None until then). Used to detect
        # devices that start reporting data after setup created no entities
        # for them (e.g. datalogger absent from livedata at startup).
        self.entity_device_ids: set[str] | None = None
        self._consecutive_failures = 0
        self._repair_issue_created = False
        self._failure_start_time: float | None = None

        # Silent datalogger tracking: the datalogger can serve the REST API
        # (polls succeed) while omitting its own device section from livedata
        # (VSN300 fw quirk after a reboot with an unsynced clock). None of the
        # re-discovery checks cover this — discovery still sees it (status is
        # healthy) and its entities exist — so it is tracked separately.
        self._datalogger_silent_since: float | None = None
        self._datalogger_silent_issue_created = False
        self._datalogger_healthy_seen = False
        self._last_error_type: str | None = None
        self._recovery_script_executed = False
        self._script_executed_time: float | None = None

        # Device trigger tracking
        self.device_id: str | None = None

        # Expected outage tracking (issue #79). An outage that is expected (auto:
        # the dropout matches the plant's night pattern; window: inside the
        # user's time window) raises no repair issue, trigger or recovery
        # script, and the failure counter only starts once it stops being
        # expected (sun above the start-up bound / window over).
        self._last_poll_power: float | None = None
        self._last_success_elevation: float | None = None
        self._outage_since: float | None = None  # any outage, set on its first failure
        self._outage_start_elevation: float | None = None
        self._outage_start_power: float | None = None
        self._expected_outage_active = False
        self._learned_nights: list[dict[str, float]] = []

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
            self._outage_mode = config_entry.options.get(CONF_OUTAGE_MODE, DEFAULT_OUTAGE_MODE)
            self._outage_window_start = config_entry.options.get(
                CONF_OUTAGE_WINDOW_START, DEFAULT_OUTAGE_WINDOW_START
            )
            self._outage_window_end = config_entry.options.get(
                CONF_OUTAGE_WINDOW_END, DEFAULT_OUTAGE_WINDOW_END
            )
            self._learned_nights = self._load_nights(config_entry.data.get(CONF_OUTAGE_LEARNING))
        else:
            self._enable_repair_notification = DEFAULT_ENABLE_REPAIR_NOTIFICATION
            self._failures_threshold = DEFAULT_FAILURES_THRESHOLD
            self._recovery_script = DEFAULT_RECOVERY_SCRIPT
            self._outage_mode = DEFAULT_OUTAGE_MODE
            self._outage_window_start = DEFAULT_OUTAGE_WINDOW_START
            self._outage_window_end = DEFAULT_OUTAGE_WINDOW_END

        _LOGGER.debug(
            "Repair notification options: enabled=%s, threshold=%s, script=%s, "
            "outage_mode=%s, window=%s-%s, outage_thresholds=%s",
            self._enable_repair_notification,
            self._failures_threshold,
            self._recovery_script,
            self._outage_mode,
            self._outage_window_start,
            self._outage_window_end,
            self.outage_thresholds,
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

            # Expected outage bookkeeping (issue #79): close the outage that
            # just ended (and learn from it if it was a night).
            elevation = self._sun_elevation() if self._outage_mode == OUTAGE_MODE_AUTO else None
            if self._outage_since is not None:
                self._end_outage(elevation)

            # Handle recovery after repair issue was created
            if self._repair_issue_created:
                await self._handle_recovery()

            # Reset failure counter on success
            self._consecutive_failures = 0
            self._last_poll_power = self._plant_power(data)
            self._last_success_elevation = elevation

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

                # Check 3: Detect devices that report data but got no entities.
                # A device present in discovery but absent from livedata at setup
                # (e.g. VSN300 datalogger after a reboot with a stale clock) is
                # never "missing" (Check 1) and already in known_devices
                # (Check 2), so neither check re-creates its sensors when its
                # livedata returns. Guarded on entity_device_ids being set: the
                # sensor platform hasn't run yet during the first refresh.
                if (
                    not self._reload_scheduled
                    and self._entry_id
                    and self.entity_device_ids is not None
                ):
                    devices_without_entities = {
                        device_id
                        for device_id, device_data in data.get("devices", {}).items()
                        if device_data.get("points")
                    } - self.entity_device_ids
                    if devices_without_entities:
                        _LOGGER.info(
                            "Devices reporting data but without entities: %s — scheduling reload",
                            ", ".join(sorted(devices_without_entities)),
                        )
                        self._reload_scheduled = True
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(self._entry_id)
                        )

            # Check 4: Datalogger present in discovery but silent in livedata.
            # Runs on every successful poll (independent of reload scheduling):
            # it creates/clears a repair issue rather than reloading, because
            # the datalogger's entities already exist and flip back to
            # available by themselves once its livedata section returns.
            self._check_datalogger_silent(data)

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
        self._last_error_type = error_type

        # Expected outage (issue #79): classify the dropout once, on the first
        # failed poll, then swallow failures and keep the counter at zero until
        # the outage stops being expected.
        if self._outage_since is None:
            self._begin_outage()
        if self._outage_is_expected():
            self._consecutive_failures = 0
            _LOGGER.debug(
                "Update error during expected outage (mode=%s): %s", self._outage_mode, error
            )
            return

        self._consecutive_failures += 1

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

    # ------------------------------------------------------------------
    # Expected outage handling (issue #79)
    # ------------------------------------------------------------------

    def _sun_elevation(self) -> float | None:
        """Return the current solar elevation in degrees, or None if unknown."""
        try:
            observer = get_astral_observer(self.hass)
            return float(astral_sun_elevation(observer, dt_util.utcnow()))
        except (TypeError, ValueError, AttributeError, OverflowError) as err:
            _LOGGER.debug("Solar elevation unavailable (is the HA location set?): %s", err)
            return None

    @staticmethod
    def _plant_power(data: dict[str, Any]) -> float | None:
        """Return the summed AC power of all inverters, or None if none reported it."""
        total: float | None = None
        for device_data in data.get("devices", {}).values():
            if not isinstance(device_data, dict):
                continue
            if not str(device_data.get("device_type", "")).startswith("inverter"):
                continue
            watts = (device_data.get("points") or {}).get("watts") or {}
            value = watts.get("value") if isinstance(watts, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                total = (total or 0.0) + float(value)
        return total

    @staticmethod
    def _load_nights(raw: Any) -> list[dict[str, float]]:
        """Validate learned nights restored from config_entry.data."""
        nights: list[dict[str, float]] = []
        if not isinstance(raw, list):
            return nights
        for item in raw:
            if not isinstance(item, dict):
                continue
            values = [item.get(key) for key in ("e_off", "p_off", "e_on")]
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
                nights.append(
                    {"e_off": float(values[0]), "p_off": float(values[1]), "e_on": float(values[2])}
                )
        return nights[-OUTAGE_LEARNING_MAX_NIGHTS:]

    def _usable_nights(self) -> list[dict[str, float]]:
        """Return the learned nights minus outliers (far above the median elevations)."""
        if not self._learned_nights:
            return []
        off_median = median(n["e_off"] for n in self._learned_nights)
        on_median = median(n["e_on"] for n in self._learned_nights)
        return [
            n
            for n in self._learned_nights
            if n["e_off"] <= off_median + OUTAGE_OUTLIER_ELEVATION
            and n["e_on"] <= on_median + OUTAGE_OUTLIER_ELEVATION
        ]

    @property
    def outage_thresholds(self) -> dict[str, Any]:
        """Bounds used by auto mode: starter values until enough nights are learned.

        entry_elevation / entry_power: a dropout is expected when, at the last
        good poll, the sun was below entry_elevation and the plant produced
        less than entry_power. exit_elevation: once the sun is above it, a
        logger that is still unreachable is reported normally.
        """
        nights = self._usable_nights()
        if len(self._learned_nights) < OUTAGE_LEARNING_NIGHTS or not nights:
            return {
                "source": "starter",
                "entry_elevation": OUTAGE_STARTER_ENTRY_ELEVATION,
                "entry_power": OUTAGE_STARTER_ENTRY_POWER,
                "exit_elevation": OUTAGE_STARTER_EXIT_ELEVATION,
            }
        return {
            "source": "learned",
            "entry_elevation": round(
                min(
                    max(n["e_off"] for n in nights) + OUTAGE_ELEVATION_MARGIN, OUTAGE_MAX_ELEVATION
                ),
                2,
            ),
            "entry_power": round(
                max(n["p_off"] for n in nights) * OUTAGE_POWER_FACTOR + OUTAGE_POWER_MARGIN, 1
            ),
            "exit_elevation": round(
                min(max(n["e_on"] for n in nights) + OUTAGE_ELEVATION_MARGIN, OUTAGE_MAX_ELEVATION),
                2,
            ),
        }

    def _in_outage_window(self, now: dt_time) -> bool:
        """Return True if the local time falls inside the configured window."""
        start = dt_util.parse_time(self._outage_window_start)
        end = dt_util.parse_time(self._outage_window_end)
        if start is None or end is None or start == end:
            return False
        if start < end:
            return start <= now < end
        # Window crosses midnight (e.g. 21:00 -> 07:00)
        return now >= start or now < end

    def _dropout_matches_night(self) -> bool:
        """Auto mode: does the dropout that just happened look like nightfall?"""
        thresholds = self.outage_thresholds
        elevation = self._last_success_elevation
        if elevation is None:
            elevation = self._sun_elevation()
        if elevation is None or elevation >= thresholds["entry_elevation"]:
            return False
        power = self._last_poll_power
        return power is None or power < thresholds["entry_power"]

    def _begin_outage(self) -> None:
        """Record the start of an outage and classify it (first failed poll)."""
        self._outage_since = time.time()
        self._outage_start_elevation = self._last_success_elevation
        self._outage_start_power = self._last_poll_power
        if self._outage_mode == OUTAGE_MODE_AUTO:
            self._expected_outage_active = self._dropout_matches_night()
        elif self._outage_mode == OUTAGE_MODE_WINDOW:
            self._expected_outage_active = self._in_outage_window(dt_util.now().time())
        else:
            self._expected_outage_active = False
        if self._outage_mode == OUTAGE_MODE_OFF:
            return
        thresholds = self.outage_thresholds
        _LOGGER.info(
            "Datalogger unreachable (mode=%s, sun at last contact %s, plant power %s, "
            "%s rule: sun below %.1f° and power below %.0f W): %s",
            self._outage_mode,
            f"{self._last_success_elevation:.1f}°"
            if self._last_success_elevation is not None
            else "unknown",
            f"{self._last_poll_power:.0f} W" if self._last_poll_power is not None else "unknown",
            thresholds["source"],
            thresholds["entry_elevation"],
            thresholds["entry_power"],
            "expected outage, failure notifications deferred"
            if self._expected_outage_active
            else "not an expected outage, reporting normally",
        )

    def _outage_is_expected(self) -> bool:
        """Decide whether the current failure belongs to an expected outage."""
        if self._outage_mode == OUTAGE_MODE_WINDOW:
            self._expected_outage_active = self._in_outage_window(dt_util.now().time())
            return self._expected_outage_active
        if self._outage_mode != OUTAGE_MODE_AUTO or not self._expected_outage_active:
            return False
        exit_elevation = self.outage_thresholds["exit_elevation"]
        elevation = self._sun_elevation()
        if elevation is not None and elevation < exit_elevation:
            return True
        # The sun is up (or its position is unknown) and the logger is still
        # dark: from now on this outage is counted and reported normally.
        self._expected_outage_active = False
        _LOGGER.info(
            "Datalogger still unreachable with the sun at %s, above the start-up "
            "elevation %.1f°: reporting the outage",
            f"{elevation:.1f}°" if elevation is not None else "unknown",
            exit_elevation,
        )
        return False

    def _end_outage(self, elevation: float | None) -> None:
        """Close an outage after the first successful poll; learn if it was a night."""
        duration = int(time.time() - self._outage_since) if self._outage_since else 0
        start_elevation = self._outage_start_elevation
        recorded = False
        if (
            self._outage_mode == OUTAGE_MODE_AUTO
            and duration >= OUTAGE_NIGHT_MIN_DURATION
            and start_elevation is not None
            and elevation is not None
            and start_elevation < OUTAGE_MAX_ELEVATION
            and elevation < OUTAGE_MAX_ELEVATION
        ):
            self._record_night(
                e_off=start_elevation,
                p_off=self._outage_start_power or 0.0,
                e_on=elevation,
            )
            recorded = True

        if self._outage_mode != OUTAGE_MODE_OFF:
            thresholds = self.outage_thresholds
            _LOGGER.info(
                "Datalogger back online after %s (power-down at %s with %s, power-up at %s; "
                "night %s; %d/%d nights learned, %s rule: sun below %.1f° and power below "
                "%.0f W, start-up by %.1f°)",
                self._format_downtime(duration),
                f"{start_elevation:.1f}°" if start_elevation is not None else "unknown",
                f"{self._outage_start_power:.0f} W"
                if self._outage_start_power is not None
                else "unknown power",
                f"{elevation:.1f}°" if elevation is not None else "unknown",
                "recorded" if recorded else "not recorded",
                len(self._learned_nights),
                OUTAGE_LEARNING_NIGHTS,
                thresholds["source"],
                thresholds["entry_elevation"],
                thresholds["entry_power"],
                thresholds["exit_elevation"],
            )
        self._outage_since = None
        self._outage_start_elevation = None
        self._outage_start_power = None
        self._expected_outage_active = False

    def _record_night(self, e_off: float, p_off: float, e_on: float) -> None:
        """Store one learned night and persist the rolling window."""
        was_learning = len(self._learned_nights) < OUTAGE_LEARNING_NIGHTS
        night = {"e_off": round(e_off, 2), "p_off": round(p_off, 1), "e_on": round(e_on, 2)}
        self._learned_nights = [*self._learned_nights, night][-OUTAGE_LEARNING_MAX_NIGHTS:]
        if was_learning and len(self._learned_nights) >= OUTAGE_LEARNING_NIGHTS:
            _LOGGER.info(
                "Expected outage learning complete after %d nights: %s",
                len(self._learned_nights),
                self.outage_thresholds,
            )
        if self._config_entry:
            data = {
                key: value
                for key, value in self._config_entry.data.items()
                if key != CONF_OUTAGE_CALIBRATION_LEGACY
            }
            data[CONF_OUTAGE_LEARNING] = list(self._learned_nights)
            self.hass.config_entries.async_update_entry(self._config_entry, data=data)

    def _expected_window(self) -> dict[str, str | None]:
        """Today's auto-mode window in local clock time, for diagnostics."""
        window: dict[str, str | None] = {"from": None, "until": None}
        thresholds = self.outage_thresholds
        try:
            observer = get_astral_observer(self.hass)
            tz = dt_util.get_default_time_zone()
            today = dt_util.now().date()
            window["from"] = time_at_elevation(
                observer, thresholds["entry_elevation"], today, SunDirection.SETTING, tzinfo=tz
            ).isoformat(timespec="minutes")
            window["until"] = time_at_elevation(
                observer,
                thresholds["exit_elevation"],
                today + timedelta(days=1),
                SunDirection.RISING,
                tzinfo=tz,
            ).isoformat(timespec="minutes")
        except (TypeError, ValueError, AttributeError, OverflowError) as err:
            _LOGGER.debug("Expected outage window not computable: %s", err)
        return window

    @property
    def outage_status(self) -> dict[str, Any]:
        """Expected-outage state for diagnostics."""
        thresholds = self.outage_thresholds
        status: dict[str, Any] = {
            "mode": self._outage_mode,
            "window_start": self._outage_window_start,
            "window_end": self._outage_window_end,
            "rule": thresholds["source"],
            "nights_learned": len(self._learned_nights),
            "nights_needed": OUTAGE_LEARNING_NIGHTS,
            "entry_elevation": thresholds["entry_elevation"],
            "entry_power": thresholds["entry_power"],
            "exit_elevation": thresholds["exit_elevation"],
            "expected_outage_active": self._expected_outage_active,
            "outage_since": dt_util.utc_from_timestamp(self._outage_since).isoformat()
            if self._outage_since
            else None,
            "last_poll_power": self._last_poll_power,
            "last_success_elevation": self._last_success_elevation,
            "nights": list(self._learned_nights),
        }
        if self._outage_mode == OUTAGE_MODE_AUTO:
            status["today_window"] = self._expected_window()
        return status

    def _check_datalogger_silent(self, data: dict[str, Any]) -> None:
        """Track a datalogger that stopped reporting its own livedata section.

        The datalogger answers every poll (it IS the REST server), so when a
        successful response lacks its device section the device is publishing
        inverter data but not its own — a wedged state that can persist for
        hours (e.g. VSN300 fw 1.9.2 after a reboot without clock sync). Its
        sensors correctly show unavailable, but without this check nothing
        tells the user why. After DATALOGGER_SILENT_THRESHOLD seconds a
        WARNING repair issue is created; it is deleted automatically on the
        first poll where the section is back (entities recover on their own).

        Only the datalogger is tracked: inverters and meters legitimately
        drop out of livedata overnight.
        """
        if not self._entry_id:
            return

        datalogger_id = next(
            (d.device_id for d in self.discovered_devices if d.is_datalogger),
            None,
        )
        if datalogger_id is None:
            return

        # Only meaningful once the sensor platform created entities for it;
        # before that, Check 3 handles the no-entities case via reload.
        if not self.entity_device_ids or datalogger_id not in self.entity_device_ids:
            return

        device_data = data.get("devices", {}).get(datalogger_id)
        if device_data and device_data.get("points"):
            # Datalogger is reporting. Clear any open issue — also on the
            # first healthy poll after a reload, when a previous run may have
            # left a persistent issue behind that this run never created.
            if self._datalogger_silent_issue_created or not self._datalogger_healthy_seen:
                delete_datalogger_silent_issue(self.hass, self._entry_id)
            if self._datalogger_silent_since is not None:
                _LOGGER.info(
                    "Datalogger %s livedata section is back after %.0f seconds",
                    datalogger_id,
                    time.monotonic() - self._datalogger_silent_since,
                )
            self._datalogger_healthy_seen = True
            self._datalogger_silent_since = None
            self._datalogger_silent_issue_created = False
            return

        now = time.monotonic()
        if self._datalogger_silent_since is None:
            self._datalogger_silent_since = now
            _LOGGER.debug(
                "Datalogger %s absent from livedata (poll succeeded) — tracking",
                datalogger_id,
            )
            return

        elapsed = now - self._datalogger_silent_since
        if (
            elapsed >= DATALOGGER_SILENT_THRESHOLD
            and not self._datalogger_silent_issue_created
            and self._enable_repair_notification
        ):
            _LOGGER.warning(
                "Datalogger %s has not reported its own livedata section for "
                "%.0f seconds while polls succeed — creating repair issue",
                datalogger_id,
                elapsed,
            )
            create_datalogger_silent_issue(
                self.hass,
                self._entry_id,
                self._get_device_name(),
                self._host or "",
            )
            self._datalogger_silent_issue_created = True

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

        except VSNConnectionError, VSNAuthenticationError, VSNClientError:
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
