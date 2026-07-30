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

# The /v1/feeds endpoint reports values in display units (e.g. m101_1_W in kW,
# m101_1_WH in kWh), but the normalizer expects the raw SunSpec magnitudes that
# /v1/livedata delivers (W, Wh). Scale by the SI prefix of the datastream's
# "units" field so feeds-sourced values match the livedata scale.
# Verified on hardware: feeds m101_1_W=1.599 kW == Modbus 1587 W;
# feeds m101_1_WH=35585.96 kWh == Modbus 35586016 Wh.
_SI_PREFIX_SCALE = {"k": 1000.0, "M": 1_000_000.0, "G": 1_000_000_000.0}


def _scale_for_units(units: str | None) -> float:
    """Return the multiplier that converts a display unit to its base SI unit.

    Only power/energy magnitudes carry SI prefixes here (kW, kWh, MWh). Base
    units (A, V, Hz, W, Wh) and missing/unknown units pass through unscaled.
    """
    if not units or len(units) < 2:
        return 1.0
    return _SI_PREFIX_SCALE.get(units[0], 1.0)


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


def reshape_datastreams(
    feeds_response: dict[str, Any], feed_key: str, device_type: str
) -> dict[str, Any]:
    """Reshape a /v1/feeds datastreams response into livedata shape.

    Args:
        feeds_response: The parsed /v1/feeds/<feed_key>/datastreams JSON.
        feed_key: The device key (e.g. ``ser4:<invID>``) to extract.
        device_type: The device type label to stamp on the output.

    Returns:
        ``{feed_key: {"device_type": ..., "points": [{"name", "value"}, ...]}}``.
        Uses the newest sample (``data[0]``); skips empty datastreams; scales
        display units (kW/kWh/MWh) to base SI units (W/Wh) so values match the
        magnitudes the normalizer expects from /v1/livedata.

    """
    feed = feeds_response.get("feeds", {}).get(feed_key, {})
    datastreams = feed.get("datastreams", {})
    points: list[dict[str, Any]] = []
    for point_name, stream in datastreams.items():
        data = stream.get("data") or []
        if not data:
            continue
        value = data[0].get("value")
        scale = _scale_for_units(stream.get("units"))
        if value is not None and scale != 1.0:
            value = value * scale
        points.append({"name": point_name, "value": value})
    return {feed_key: {"device_type": device_type, "points": points}}
