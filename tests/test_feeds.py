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


def test_reshape_datastreams_takes_newest_sample_and_scales_units() -> None:
    """Newest sample = data[0]; feeds display units (kW/kWh) scale to SunSpec W/Wh.

    The /v1/feeds endpoint reports m101_1_W in kW and m101_1_WH in kWh, but the
    normalizer expects raw SunSpec magnitudes (W, Wh) as /v1/livedata delivers.
    Verified against hardware: feeds m101_1_W=1.599 kW == Modbus 1587 W.
    """
    from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.feeds import (
        reshape_datastreams,
    )

    feeds_response = {
        "feeds": {
            "ser4:010261-3G97-1021": {
                "datastreams": {
                    "m101_1_W": {
                        "data": [
                            {"value": 1.599, "timestamp": "2026-07-30T08:50:16"},
                            {"value": 1.500, "timestamp": "2026-07-30T08:45:16"},
                        ],
                        "units": "kW",
                    },
                    "m101_1_WH": {
                        "data": [{"value": 35585.96, "timestamp": "2026-07-30T08:50:16"}],
                        "units": "kWh",
                    },
                    "m101_1_A": {
                        "data": [{"value": 6.55, "timestamp": "2026-07-30T08:50:16"}],
                        "units": "A",
                    },
                    "m101_1_empty": {"data": [], "units": "A"},
                }
            }
        }
    }
    result = reshape_datastreams(feeds_response, "ser4:010261-3G97-1021", "inverter")
    assert result["ser4:010261-3G97-1021"]["device_type"] == "inverter"
    points = {p["name"]: p["value"] for p in result["ser4:010261-3G97-1021"]["points"]}
    # kW -> W (*1000), kWh -> Wh (*1000), A unchanged, empty stream skipped.
    assert points["m101_1_W"] == 1599.0
    assert points["m101_1_WH"] == 35585960.0
    assert points["m101_1_A"] == 6.55
    assert "m101_1_empty" not in points


def test_reshape_datastreams_megawatt_scale() -> None:
    """MW/MWh display units scale by 1e6."""
    from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.feeds import (
        reshape_datastreams,
    )

    feeds_response = {
        "feeds": {
            "ser4:X": {
                "datastreams": {
                    "big_WH": {"data": [{"value": 2.5, "timestamp": "t"}], "units": "MWh"},
                    "plain_W": {"data": [{"value": 900.0, "timestamp": "t"}], "units": "W"},
                    "nounits": {"data": [{"value": 42.0, "timestamp": "t"}]},
                }
            }
        }
    }
    result = reshape_datastreams(feeds_response, "ser4:X", "inverter")
    points = {p["name"]: p["value"] for p in result["ser4:X"]["points"]}
    assert points["big_WH"] == 2_500_000.0
    assert points["plain_W"] == 900.0  # already base unit, unchanged
    assert points["nounits"] == 42.0  # no units field -> passthrough
