"""Tests for ABB FIMER PVI VSN REST normalizer."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.mapping_loader import (
    PointMapping,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.normalizer import (
    A_TO_MA_POINTS,
    B_TO_MB_POINTS,
    STRING_STRIP_POINTS,
    TEMP_CORRECTION_POINTS,
    TEMP_THRESHOLD_CELSIUS,
    TITLE_CASE_POINTS,
    UA_TO_MA_POINTS,
    VSN700_NAME_NORMALIZATION,
    VSNDataNormalizer,
)


class TestVSNDataNormalizerInit:
    """Tests for VSNDataNormalizer initialization."""

    def test_init_vsn300(self) -> None:
        """Test initialization with VSN300 model."""
        normalizer = VSNDataNormalizer("VSN300")
        assert normalizer.vsn_model == "VSN300"
        assert normalizer._loaded is False

    def test_init_vsn700(self) -> None:
        """Test initialization with VSN700 model."""
        normalizer = VSNDataNormalizer("VSN700")
        assert normalizer.vsn_model == "VSN700"
        assert normalizer._loaded is False

    def test_init_invalid_model(self) -> None:
        """Test initialization with invalid model raises error."""
        with pytest.raises(ValueError, match="Invalid VSN model"):
            VSNDataNormalizer("VSN999")

    def test_init_with_custom_mapping_loader(self) -> None:
        """Test initialization with custom mapping loader."""
        mock_loader = MagicMock()
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        assert normalizer._mapping_loader == mock_loader


class TestVSNDataNormalizerAsyncLoad:
    """Tests for async_load method."""

    @pytest.mark.asyncio
    async def test_async_load_calls_mapping_loader(self) -> None:
        """Test async_load calls mapping loader's async_load."""
        mock_loader = MagicMock()
        mock_loader.async_load = AsyncMock()
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        await normalizer.async_load()

        mock_loader.async_load.assert_called_once()
        assert normalizer._loaded is True

    @pytest.mark.asyncio
    async def test_async_load_only_loads_once(self) -> None:
        """Test async_load only loads once when called multiple times."""
        mock_loader = MagicMock()
        mock_loader.async_load = AsyncMock()
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        await normalizer.async_load()
        await normalizer.async_load()
        await normalizer.async_load()

        # Should only be called once
        mock_loader.async_load.assert_called_once()


class TestVSN300PointNameNormalization:
    """Tests for VSN300 point name normalization."""

    def test_normalize_m101_to_m103(self) -> None:
        """Test M101 prefix normalized to M103."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._normalize_vsn300_point_name("m101_1_W")
        assert result == "m103_1_W"

    def test_normalize_m102_to_m103(self) -> None:
        """Test M102 prefix normalized to M103."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._normalize_vsn300_point_name("m102_1_W")
        assert result == "m103_1_W"

    def test_no_normalization_for_m103(self) -> None:
        """Test M103 prefix not modified."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._normalize_vsn300_point_name("m103_1_W")
        assert result == "m103_1_W"

    def test_no_normalization_for_other_prefixes(self) -> None:
        """Test other prefixes not modified."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._normalize_vsn300_point_name("m64061_1_TmpCab")
        assert result == "m64061_1_TmpCab"


class TestVSN700PointNameNormalization:
    """Tests for VSN700 point name normalization."""

    def test_normalize_tsoc_to_soc(self) -> None:
        """Test TSoc normalized to Soc."""
        normalizer = VSNDataNormalizer("VSN700")
        result = normalizer._normalize_vsn700_point_name("TSoc")
        assert result == "Soc"

    def test_no_normalization_for_unmapped_names(self) -> None:
        """Test unmapped names pass through unchanged."""
        normalizer = VSNDataNormalizer("VSN700")
        result = normalizer._normalize_vsn700_point_name("Pgrid")
        assert result == "Pgrid"

    def test_normalization_map_entries(self) -> None:
        """Test all entries in normalization map work correctly."""
        normalizer = VSNDataNormalizer("VSN700")
        for old_name, new_name in VSN700_NAME_NORMALIZATION.items():
            result = normalizer._normalize_vsn700_point_name(old_name)
            assert result == new_name


class TestValueTransformations:
    """Tests for value transformations."""

    def test_ua_to_ma_conversion(self) -> None:
        """Test uA to mA conversion (divide by 1000)."""
        normalizer = VSNDataNormalizer("VSN300")
        for point_name in UA_TO_MA_POINTS:
            result = normalizer._apply_value_transformations(point_name, 5000)
            assert result == 5.0  # 5000 uA = 5 mA

    def test_ua_to_ma_with_zero(self) -> None:
        """Test uA to mA conversion with zero value."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("m64061_1_ILeakDcAc", 0)
        assert result == 0.0

    def test_a_to_ma_conversion_vsn700(self) -> None:
        """Test A to mA conversion for VSN700 (multiply by 1000)."""
        normalizer = VSNDataNormalizer("VSN700")
        for point_name in A_TO_MA_POINTS:
            result = normalizer._apply_value_transformations(point_name, 0.005)
            assert result == 5.0  # 0.005 A = 5 mA

    def test_a_to_ma_skipped_for_vsn300(self) -> None:
        """Test A to mA conversion skipped for VSN300."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("IleakInv", 0.005)
        assert result == 0.005  # Not converted

    def test_a_to_ma_skipped_for_zero(self) -> None:
        """Test A to mA conversion skipped for zero values."""
        normalizer = VSNDataNormalizer("VSN700")
        result = normalizer._apply_value_transformations("IleakInv", 0)
        assert result == 0

    def test_temperature_correction_above_threshold(self) -> None:
        """Test temperature correction when value exceeds threshold."""
        normalizer = VSNDataNormalizer("VSN300")
        for point_name in TEMP_CORRECTION_POINTS:
            result = normalizer._apply_value_transformations(point_name, 450)
            assert result == 45.0  # 450 / 10 = 45

    def test_temperature_correction_below_threshold(self) -> None:
        """Test temperature correction not applied below threshold."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("m103_1_TmpCab", 45)
        assert result == 45  # No correction (below threshold)

    def test_temperature_threshold_boundary(self) -> None:
        """Test temperature correction at exact threshold."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("m103_1_TmpCab", TEMP_THRESHOLD_CELSIUS)
        assert result == TEMP_THRESHOLD_CELSIUS  # Not corrected at boundary

    def test_string_strip_dashes(self) -> None:
        """Test stripping dashes from string values."""
        normalizer = VSNDataNormalizer("VSN300")
        for point_name in STRING_STRIP_POINTS:
            result = normalizer._apply_value_transformations(point_name, "--PVI-10.0--")
            assert result == "PVI-10.0"

    def test_string_strip_no_dashes(self) -> None:
        """Test string strip with no leading/trailing dashes."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("pn", "PVI-10.0")
        assert result == "PVI-10.0"

    def test_title_case_conversion(self) -> None:
        """Test title case conversion."""
        normalizer = VSNDataNormalizer("VSN300")
        for point_name in TITLE_CASE_POINTS:
            result = normalizer._apply_value_transformations(point_name, "WIFI LOGGER CARD")
            assert result == "Wifi Logger Card"

    def test_bytes_to_mb_conversion(self) -> None:
        """Test bytes to MB conversion."""
        normalizer = VSNDataNormalizer("VSN300")
        for point_name in B_TO_MB_POINTS:
            result = normalizer._apply_value_transformations(point_name, 10485760)  # 10 MB
            assert result == 10.0

    def test_none_value_passthrough(self) -> None:
        """Test None values pass through unchanged."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("m64061_1_ILeakDcAc", None)
        assert result is None

    def test_unregistered_point_passthrough(self) -> None:
        """Test unregistered points pass through unchanged."""
        normalizer = VSNDataNormalizer("VSN300")
        result = normalizer._apply_value_transformations("unknown_point", 12345)
        assert result == 12345


class TestNormalize:
    """Tests for the normalize method."""

    @pytest.fixture
    def mock_mapping(self) -> PointMapping:
        """Create a mock PointMapping."""
        return PointMapping(
            vsn700_name="Pgrid",
            vsn300_name="m103_1_W",
            sunspec_name="W",
            ha_entity_name="watts",
            in_livedata=True,
            in_feeds=False,
            label="Watts",
            description="AC Power",
            ha_display_name="Power AC",
            models=["M103"],
            category="Inverter",
            units="W",
            state_class="measurement",
            device_class="power",
            entity_category=None,
            available_in_modbus="Yes",
            icon="",
            suggested_display_precision=0,
        )

    @pytest.fixture
    def mock_energy_mapping(self) -> PointMapping:
        """Create a mock PointMapping for energy sensor."""
        return PointMapping(
            vsn700_name="Etot",
            vsn300_name="m103_1_WH",
            sunspec_name="WH",
            ha_entity_name="watthours",
            in_livedata=True,
            in_feeds=False,
            label="Watt-Hours",
            description="Lifetime Energy",
            ha_display_name="Energy AC - Produced Lifetime",
            models=["M103"],
            category="Inverter",
            units="Wh",
            state_class="total_increasing",
            device_class="energy",
            entity_category=None,
            available_in_modbus="Yes",
            icon="",
            suggested_display_precision=2,
        )

    def test_normalize_vsn300_data(self, mock_mapping: PointMapping) -> None:
        """Test normalizing VSN300 data."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "077909-3G82-3112": {
                "points": [
                    {"name": "m103_1_W", "value": 5000},
                ],
                "device_type": "inverter_3phases",
            }
        }

        result = normalizer.normalize(raw_data)

        assert "devices" in result
        assert "077909-3G82-3112" in result["devices"]
        device = result["devices"]["077909-3G82-3112"]
        assert "points" in device
        assert "watts" in device["points"]
        assert device["points"]["watts"]["value"] == 5000
        assert device["points"]["watts"]["units"] == "W"

    def test_normalize_vsn700_data(self, mock_mapping: PointMapping) -> None:
        """Test normalizing VSN700 data."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn700.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN700", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "123456-ABCD-1234": {
                "points": [
                    {"name": "Pgrid", "value": 3500},
                ],
                "device_type": "inverter_3phases",
            }
        }

        result = normalizer.normalize(raw_data)

        assert "devices" in result
        assert "123456-ABCD-1234" in result["devices"]
        device = result["devices"]["123456-ABCD-1234"]
        assert device["points"]["watts"]["value"] == 3500

    def test_normalize_energy_wh_to_kwh_conversion(self, mock_energy_mapping: PointMapping) -> None:
        """Test energy sensors are converted from Wh to kWh."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_energy_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "077909-3G82-3112": {
                "points": [
                    {"name": "m103_1_WH", "value": 123456789},
                ],
            }
        }

        result = normalizer.normalize(raw_data)

        device = result["devices"]["077909-3G82-3112"]
        assert device["points"]["watthours"]["value"] == 123456.789  # kWh
        assert device["points"]["watthours"]["units"] == "kWh"

    def test_normalize_datalogger_uses_sn_instead_of_mac(self, mock_mapping: PointMapping) -> None:
        """Test datalogger device uses S/N from data instead of MAC."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "aa:bb:cc:dd:ee:ff": {
                "points": [
                    {"name": "sn", "value": "111033-3N16-1421"},
                    {"name": "m103_1_W", "value": 1000},
                ],
            }
        }

        result = normalizer.normalize(raw_data)

        # Should use S/N as device ID, not MAC
        assert "111033-3N16-1421" in result["devices"]
        assert "aa:bb:cc:dd:ee:ff" not in result["devices"]

    def test_normalize_skips_device_without_points(self) -> None:
        """Test devices without points are skipped."""
        normalizer = VSNDataNormalizer("VSN300")
        normalizer._loaded = True

        raw_data = {
            "077909-3G82-3112": {},  # No points key
        }

        result = normalizer.normalize(raw_data)

        assert result == {"devices": {}}

    def test_normalize_skips_unmapped_points(self) -> None:
        """Test unmapped points are skipped."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = None  # No mapping found
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "077909-3G82-3112": {
                "points": [
                    {"name": "unknown_point", "value": 999},
                ],
            }
        }

        result = normalizer.normalize(raw_data)

        # Device should be skipped if no points were mapped
        assert result == {"devices": {}}

    def test_normalize_skips_points_without_name(self, mock_mapping: PointMapping) -> None:
        """Test points without name are skipped."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)
        normalizer._loaded = True

        raw_data = {
            "077909-3G82-3112": {
                "points": [
                    {"value": 5000},  # No name
                    {"name": "m103_1_W", "value": 3000},
                ],
            }
        }

        result = normalizer.normalize(raw_data)

        device = result["devices"]["077909-3G82-3112"]
        assert len(device["points"]) == 1
        assert "watts" in device["points"]


class TestGetPointMetadata:
    """Tests for get_point_metadata method."""

    def test_get_point_metadata_vsn300(self) -> None:
        """Test getting metadata for VSN300 point."""
        mock_mapping = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        result = normalizer.get_point_metadata("m103_1_W")

        mock_loader.get_by_vsn300.assert_called_once_with("m103_1_W")
        assert result == mock_mapping

    def test_get_point_metadata_vsn700(self) -> None:
        """Test getting metadata for VSN700 point."""
        mock_mapping = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_by_vsn700.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN700", mapping_loader=mock_loader)

        result = normalizer.get_point_metadata("Pgrid")

        mock_loader.get_by_vsn700.assert_called_once_with("Pgrid")
        assert result == mock_mapping


class TestGetAllExpectedPoints:
    """Tests for get_all_expected_points method."""

    def test_get_all_expected_points_vsn300(self) -> None:
        """Test getting all expected points for VSN300."""
        mock_mapping_vsn300 = MagicMock()
        mock_mapping_vsn300.vsn300_name = "m103_1_W"
        mock_mapping_vsn300.vsn700_name = None

        mock_mapping_both = MagicMock()
        mock_mapping_both.vsn300_name = "m103_1_WH"
        mock_mapping_both.vsn700_name = "Etot"

        mock_mapping_vsn700_only = MagicMock()
        mock_mapping_vsn700_only.vsn300_name = None
        mock_mapping_vsn700_only.vsn700_name = "Pgrid"

        mock_loader = MagicMock()
        mock_loader.get_all_mappings.return_value = {
            "watts": mock_mapping_vsn300,
            "watthours": mock_mapping_both,
            "grid_power": mock_mapping_vsn700_only,
        }
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        result = normalizer.get_all_expected_points()

        # Should include VSN300-only and both, but not VSN700-only
        assert len(result) == 2
        assert mock_mapping_vsn300 in result
        assert mock_mapping_both in result
        assert mock_mapping_vsn700_only not in result

    def test_get_all_expected_points_vsn700(self) -> None:
        """Test getting all expected points for VSN700."""
        mock_mapping_vsn300_only = MagicMock()
        mock_mapping_vsn300_only.vsn300_name = "m103_1_W"
        mock_mapping_vsn300_only.vsn700_name = None

        mock_mapping_vsn700 = MagicMock()
        mock_mapping_vsn700.vsn300_name = None
        mock_mapping_vsn700.vsn700_name = "Pgrid"

        mock_loader = MagicMock()
        mock_loader.get_all_mappings.return_value = {
            "watts": mock_mapping_vsn300_only,
            "grid_power": mock_mapping_vsn700,
        }
        normalizer = VSNDataNormalizer("VSN700", mapping_loader=mock_loader)

        result = normalizer.get_all_expected_points()

        assert len(result) == 1
        assert mock_mapping_vsn700 in result
        assert mock_mapping_vsn300_only not in result


class TestGetVSNCrossReference:
    """Tests for get_vsn_cross_reference method."""

    def test_cross_reference_vsn300_to_vsn700(self) -> None:
        """Test getting VSN700 equivalent for VSN300 point."""
        mock_mapping = MagicMock()
        mock_mapping.vsn700_name = "Pgrid"
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        result = normalizer.get_vsn_cross_reference("m103_1_W")

        assert result == "Pgrid"

    def test_cross_reference_vsn700_to_vsn300(self) -> None:
        """Test getting VSN300 equivalent for VSN700 point."""
        mock_mapping = MagicMock()
        mock_mapping.vsn300_name = "m103_1_W"
        mock_loader = MagicMock()
        mock_loader.get_by_vsn700.return_value = mock_mapping
        normalizer = VSNDataNormalizer("VSN700", mapping_loader=mock_loader)

        result = normalizer.get_vsn_cross_reference("Pgrid")

        assert result == "m103_1_W"

    def test_cross_reference_not_found(self) -> None:
        """Test cross reference returns None when point not found."""
        mock_loader = MagicMock()
        mock_loader.get_by_vsn300.return_value = None
        normalizer = VSNDataNormalizer("VSN300", mapping_loader=mock_loader)

        result = normalizer.get_vsn_cross_reference("unknown_point")

        assert result is None
