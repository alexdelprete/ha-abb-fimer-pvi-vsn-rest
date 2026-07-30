"""Tests for the /v1/feeds fallback adapter."""

from __future__ import annotations

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.feeds import (
    build_feed_key,
    parse_status_devices,
)


def test_build_feed_key() -> None:
    assert build_feed_key("010261-3G97-1021") == "ser4:010261-3G97-1021"


def test_parse_status_devices_single_inverter() -> None:
    status = {
        "keys": {
            "device.invID": {"value": "010261-3G97-1021"},
            "device.modelDesc": {"value": "PVI-3.6-OUTD"},
            "device.ACType": {"value": "Single"},
            "logger.sn": {"value": "124437-3N16-2721"},
        }
    }
    devices = parse_status_devices(status)
    assert devices == [
        {
            "feed_key": "ser4:010261-3G97-1021",
            "inv_id": "010261-3G97-1021",
            "device_model": "PVI-3.6-OUTD",
            "ac_type": "Single",
        }
    ]


def test_parse_status_devices_no_inverter() -> None:
    assert parse_status_devices({"keys": {}}) == []
