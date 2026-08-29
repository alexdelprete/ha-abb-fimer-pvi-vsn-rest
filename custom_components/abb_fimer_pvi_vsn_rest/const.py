"""Constants for ABB FIMER PVI VSN REST integration."""

# Import protocol-level constants from client library
# Re-exported for integration use
from .abb_fimer_vsn_rest_client import (  # noqa: F401
    ALARM_STATE_MAP,
    AURORA_EPOCH_OFFSET,
    DCDC_STATE_MAP,
    GLOBAL_STATE_MAP,
    INVERTER_STATE_MAP,
)

DOMAIN = "abb_fimer_pvi_vsn_rest"
VERSION = "1.5.12"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"  # noqa: S105
CONF_SCAN_INTERVAL = "scan_interval"
CONF_VSN_MODEL = "vsn_model"  # Cached detection result
CONF_REQUIRES_AUTH = "requires_auth"  # Whether device requires authentication
CONF_KNOWN_DEVICES = "known_devices"  # Persisted list of known devices across restarts

# Device name prefix options (empty = use default naming)
# When a single device of a type exists, use the base key (e.g., "prefix_battery").
# When multiple devices of the same type exist, use indexed keys (e.g., "prefix_battery_1").
CONF_PREFIX_INVERTER = "prefix_inverter"
CONF_PREFIX_DATALOGGER = "prefix_datalogger"
CONF_PREFIX_METER = "prefix_meter"
CONF_PREFIX_BATTERY = "prefix_battery"

# Mapping from simplified device type to its config prefix key base
TYPE_TO_CONF_PREFIX: dict[str, str] = {
    "inverter": CONF_PREFIX_INVERTER,
    "datalogger": CONF_PREFIX_DATALOGGER,
    "meter": CONF_PREFIX_METER,
    "battery": CONF_PREFIX_BATTERY,
}

# Entity ID regeneration option (one-time action, not persisted)
CONF_REGENERATE_ENTITY_IDS = "regenerate_entity_ids"

# Repair notification options
CONF_ENABLE_REPAIR_NOTIFICATION = "enable_repair_notification"
CONF_ENABLE_STARTUP_NOTIFICATION = "enable_startup_notification"
CONF_FAILURES_THRESHOLD = "failures_threshold"
CONF_RECOVERY_SCRIPT = "recovery_script"

DEFAULT_USERNAME = "guest"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600

# Failure tracking for repair issues
DEFAULT_ENABLE_REPAIR_NOTIFICATION = True
DEFAULT_ENABLE_STARTUP_NOTIFICATION = False
DEFAULT_FAILURES_THRESHOLD = 3  # Number of consecutive failures before creating repair issue
DEFAULT_RECOVERY_SCRIPT = ""  # Empty = no script
MIN_FAILURES_THRESHOLD = 1
MAX_FAILURES_THRESHOLD = 10

# Seconds the datalogger may be absent from livedata (while polls succeed)
# before a repair issue is raised. Time-based rather than poll-based so the
# behavior is independent of scan_interval. Generous enough to cover the
# normal post-boot window where the datalogger omits its own livedata
# section until its clock syncs (VSN300 fw 1.9.2 quirk).
DATALOGGER_SILENT_THRESHOLD = 1800

# VSN Models
VSN_MODEL_300 = "VSN300"
VSN_MODEL_700 = "VSN700"

# VSN300 datalogger WiFi operating mode (wlan0_mode livedata point).
# Values verified against the firmware's own web UI code (wifi-ap-svc.js,
# fetched from a live fw 2.0.1 logger): getMode() treats 1 as station and
# anything else as AP; setMode() writes '1' for station, '0' for AP (config
# key wlan.0.connect). Value 1 additionally hardware-verified in livedata
# captures (fw 1.9.2 and 2.0.1, logger connected as WiFi client). SunSpec has
# no WLAN model, so no register-map enumeration exists for this point.
WLAN_MODE_STATE_MAP = {
    0: "Access Point",
    1: "Station (Client)",
}

# Integration-level mapping: SunSpec entity names → Aurora state maps
# This is HA-specific glue that connects normalized SunSpec point names
# to Aurora protocol state translations for display in Home Assistant.
# The state map data itself is imported from the client library above.
# Keys must match the SunSpec normalized names from vsn-sunspec-point-mapping.json
STATE_ENTITY_MAPPINGS = {
    # VSN300 (SunSpec) names
    "GlobalSt": GLOBAL_STATE_MAP,  # VSN300: m64061_1_GlobalSt
    "DcSt1": DCDC_STATE_MAP,  # VSN300: m64061_1_DcSt1
    "DcSt2": DCDC_STATE_MAP,  # VSN300: m64061_1_DcSt2
    "DcSt3": DCDC_STATE_MAP,  # VSN300: m64061_1_DcSt3 (TRIO-TM 3rd MPPT)
    "InverterSt": INVERTER_STATE_MAP,  # VSN300: m64061_1_InverterSt
    "AlarmSt": ALARM_STATE_MAP,  # VSN300: m64061_1_AlarmSt
    # VSN700 names (different from the VSN300/SunSpec names for the same states)
    "GlobState": GLOBAL_STATE_MAP,  # VSN700
    "InvState": INVERTER_STATE_MAP,  # VSN700
    "DC1State": DCDC_STATE_MAP,  # VSN700
    "DC2State": DCDC_STATE_MAP,  # VSN700
    "DC3State": DCDC_STATE_MAP,  # VSN700 (TRIO-TM 3rd MPPT)
    "AlarmState": ALARM_STATE_MAP,  # shared VSN700/VSN300 name
    # VSN300 datalogger points (not Aurora protocol states)
    "wlan0_mode": WLAN_MODE_STATE_MAP,  # WiFi operating mode
}

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
ABB/FIMER PVI VSN REST
Version: {VERSION}
This is a custom integration for Home Assistant
If you have any issues, please report them at:
https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/issues
-------------------------------------------------------------------
"""
