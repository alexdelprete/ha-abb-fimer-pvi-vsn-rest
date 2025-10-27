"""Constants for ABB FIMER PVI VSN REST integration."""

DOMAIN = "abb_fimer_pvi_vsn_rest"
VERSION = "1.0.0-beta.4"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_VSN_MODEL = "vsn_model"  # Cached detection result

DEFAULT_USERNAME = "guest"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 600

# VSN Models
VSN_MODEL_300 = "vsn300"
VSN_MODEL_700 = "vsn700"

# REST API Endpoints
ENDPOINT_STATUS = "/v1/status"
ENDPOINT_LIVEDATA = "/v1/livedata"
ENDPOINT_FEEDS = "/v1/feeds"

STARTUP_MESSAGE = """
-------------------------------------------------------------------
ABB/FIMER PVI VSN REST
Version: 1.0.0-beta.4
This is a custom integration for Home Assistant
If you have any issues, please report them at:
https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/issues
-------------------------------------------------------------------
"""
