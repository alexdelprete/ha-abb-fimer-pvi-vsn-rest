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
VERSION = "1.3.3"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_VSN_MODEL = "vsn_model"  # Cached detection result
CONF_REQUIRES_AUTH = "requires_auth"  # Whether device requires authentication

# Device name prefix options (empty = use default naming)
CONF_PREFIX_INVERTER = "prefix_inverter"
CONF_PREFIX_DATALOGGER = "prefix_datalogger"
CONF_PREFIX_METER = "prefix_meter"
CONF_PREFIX_BATTERY = "prefix_battery"

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

# VSN Models
VSN_MODEL_300 = "VSN300"
VSN_MODEL_700 = "VSN700"

# Integration-level mapping: SunSpec entity names → Aurora state maps
# This is HA-specific glue that connects normalized SunSpec point names
# to Aurora protocol state translations for display in Home Assistant.
# The state map data itself is imported from the client library above.
# Keys must match the SunSpec normalized names from vsn-sunspec-point-mapping.json
STATE_ENTITY_MAPPINGS = {
    "GlobalSt": GLOBAL_STATE_MAP,  # VSN300: m64061_1_GlobalSt
    "DcSt1": DCDC_STATE_MAP,  # VSN300: m64061_1_DcSt1
    "DcSt2": DCDC_STATE_MAP,  # VSN300: m64061_1_DcSt2
    "InverterSt": INVERTER_STATE_MAP,  # VSN300: m64061_1_InverterSt
    "AlarmState": ALARM_STATE_MAP,
    "AlarmSt": ALARM_STATE_MAP,  # VSN300: m64061_1_AlarmSt
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
