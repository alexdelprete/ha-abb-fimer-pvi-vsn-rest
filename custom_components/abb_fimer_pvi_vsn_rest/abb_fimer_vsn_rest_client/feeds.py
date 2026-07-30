"""/v1/feeds fallback adapter for VSN300 firmware where /v1/livedata is dead.

Some VSN300 firmware (e.g. 2.0.0) drops the TCP connection on every /v1/livedata
request. The web UI reads live data from /v1/feeds/ser4:<invID>/datastreams
instead. This module fetches that endpoint and reshapes it into the same
{device_id: {device_type, points: [{name, value}]}} structure the normalizer
already consumes from livedata, so no normalizer changes are needed.

See issue #68 item 3.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

FEED_KEY_PREFIX = "ser4:"


def build_feed_key(inv_id: str) -> str:
    """Build the /v1/feeds device key from an inverter serial (device.invID)."""
    return f"{FEED_KEY_PREFIX}{inv_id}"


def parse_status_devices(status_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate real inverter devices from /v1/status.

    Bare /v1/feeds is empty on this firmware, so devices are enumerated from the
    status endpoint's flattened dotted keys (``keys["device.invID"]``) and
    addressed as ``ser4:<invID>``.

    Args:
        status_data: The parsed /v1/status JSON.

    Returns:
        One dict per real inverter, each with ``feed_key``, ``inv_id``,
        ``device_model`` and ``ac_type``. Empty list when no ``device.invID``.

    """
    keys = status_data.get("keys", {})
    inv_id = keys.get("device.invID", {}).get("value")
    if not inv_id:
        return []
    return [
        {
            "feed_key": build_feed_key(inv_id),
            "inv_id": inv_id,
            "device_model": keys.get("device.modelDesc", {}).get("value"),
            "ac_type": keys.get("device.ACType", {}).get("value"),
        }
    ]
