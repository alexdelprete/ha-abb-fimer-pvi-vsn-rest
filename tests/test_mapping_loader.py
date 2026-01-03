"""Tests for ABB FIMER PVI VSN REST mapping loader."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.mapping_loader import (
    PointMapping,
    VSNMappingLoader,
)


class TestPointMapping:
    """Tests for PointMapping dataclass."""

    def test_point_mapping_creation(self) -> None:
        """Test PointMapping can be created with all fields."""
        mapping = PointMapping(
            vsn700_name="Pgrid",
            vsn300_name="m103_1_W",
            sunspec_name="W",
            ha_entity_name="watts",
            in_livedata=True,
            in_feeds=False,
            label="Watts",
            description="AC Power",
            ha_display_name="Power AC",
            models=["M103", "M802"],
            category="Inverter",
            units="W",
            state_class="measurement",
            device_class="power",
            entity_category=None,
            available_in_modbus="Yes",
            icon="mdi:flash",
            suggested_display_precision=0,
        )

        assert mapping.vsn700_name == "Pgrid"
        assert mapping.vsn300_name == "m103_1_W"
        assert mapping.sunspec_name == "W"
        assert mapping.ha_entity_name == "watts"
        assert mapping.in_livedata is True
        assert mapping.in_feeds is False
        assert mapping.label == "Watts"
        assert mapping.models == ["M103", "M802"]
        assert mapping.icon == "mdi:flash"
        assert mapping.suggested_display_precision == 0

    def test_point_mapping_optional_fields(self) -> None:
        """Test PointMapping with optional fields as None."""
        mapping = PointMapping(
            vsn700_name=None,
            vsn300_name="m103_1_W",
            sunspec_name=None,
            ha_entity_name="watts",
            in_livedata=True,
            in_feeds=False,
            label="",
            description="",
            ha_display_name="",
            models=[],
            category="",
            units="",
            state_class="",
            device_class="",
            entity_category=None,
            available_in_modbus="",
        )

        assert mapping.vsn700_name is None
        assert mapping.sunspec_name is None
        assert mapping.icon == ""  # Default value
        assert mapping.suggested_display_precision is None  # Default value


class TestVSNMappingLoaderInit:
    """Tests for VSNMappingLoader initialization."""

    def test_init_default_path(self) -> None:
        """Test initialization uses default path."""
        loader = VSNMappingLoader()
        assert loader._mapping_file_path.name == "vsn-sunspec-point-mapping.json"
        assert "data" in str(loader._mapping_file_path)

    def test_init_custom_path_string(self) -> None:
        """Test initialization with custom path as string."""
        loader = VSNMappingLoader("/custom/path/mapping.json")
        assert loader._mapping_file_path == Path("/custom/path/mapping.json")

    def test_init_custom_path_object(self) -> None:
        """Test initialization with custom path as Path object."""
        custom_path = Path("/custom/path/mapping.json")
        loader = VSNMappingLoader(custom_path)
        assert loader._mapping_file_path == custom_path

    def test_init_empty_state(self) -> None:
        """Test loader starts with empty state."""
        loader = VSNMappingLoader()
        assert loader._mappings == {}
        assert loader._vsn300_index == {}
        assert loader._vsn700_index == {}
        assert loader._ha_entity_index == {}
        assert loader._loaded is False


class TestVSNMappingLoaderAsyncLoad:
    """Tests for async_load method."""

    @pytest.fixture
    def sample_mapping_data(self) -> list[dict[str, Any]]:
        """Create sample mapping data."""
        return [
            {
                "REST Name (VSN700)": "Pgrid",
                "REST Name (VSN300)": "m103_1_W",
                "SunSpec Normalized Name": "W",
                "HA Name": "watts",
                "In /livedata": "✓",
                "In /feeds": "",
                "Label": "Watts",
                "Description": "AC Power",
                "HA Display Name": "Power AC",
                "models": ["M103"],
                "Category": "Inverter",
                "HA Unit of Measurement": "W",
                "HA State Class": "measurement",
                "HA Device Class": "power",
                "Entity Category": "",
                "Available in Modbus": "Yes",
                "HA Icon": "mdi:flash",
                "Suggested Display Precision": 0,
            },
            {
                "REST Name (VSN700)": "N/A",
                "REST Name (VSN300)": "fw_ver",
                "SunSpec Normalized Name": "N/A",
                "HA Name": "firmware_version",
                "In /livedata": "✓",
                "In /feeds": "",
                "Label": "Firmware Version",
                "Description": "Firmware version",
                "HA Display Name": "Firmware Version",
                "models": [],
                "Category": "System",
                "HA Unit of Measurement": "",
                "HA State Class": "",
                "HA Device Class": "",
                "Entity Category": "diagnostic",
                "Available in Modbus": "No",
                "HA Icon": "mdi:information",
                "Suggested Display Precision": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_async_load_from_file(
        self, sample_mapping_data: list[dict[str, Any]], tmp_path: Path
    ) -> None:
        """Test loading mappings from file."""
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(sample_mapping_data))

        loader = VSNMappingLoader(mapping_file)
        await loader.async_load()

        assert loader._loaded is True
        assert len(loader._mappings) == 2
        assert "watts" in loader._mappings
        assert "firmware_version" in loader._mappings

    @pytest.mark.asyncio
    async def test_async_load_builds_indexes(
        self, sample_mapping_data: list[dict[str, Any]], tmp_path: Path
    ) -> None:
        """Test indexes are built correctly."""
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(sample_mapping_data))

        loader = VSNMappingLoader(mapping_file)
        await loader.async_load()

        # Check VSN300 index
        assert "m103_1_W" in loader._vsn300_index
        assert "fw_ver" in loader._vsn300_index
        assert loader._vsn300_index["m103_1_W"] == "watts"

        # Check VSN700 index
        assert "Pgrid" in loader._vsn700_index
        assert loader._vsn700_index["Pgrid"] == "watts"
        # N/A should not be in index
        assert "N/A" not in loader._vsn700_index

    @pytest.mark.asyncio
    async def test_async_load_only_loads_once(
        self, sample_mapping_data: list[dict[str, Any]], tmp_path: Path
    ) -> None:
        """Test async_load only loads once."""
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(sample_mapping_data))

        loader = VSNMappingLoader(mapping_file)

        await loader.async_load()
        mappings_count = len(loader._mappings)

        # Modify file (should not affect since already loaded)
        mapping_file.write_text(json.dumps([]))

        await loader.async_load()

        assert len(loader._mappings) == mappings_count

    @pytest.mark.asyncio
    async def test_async_load_normalizes_na_values(
        self, sample_mapping_data: list[dict[str, Any]], tmp_path: Path
    ) -> None:
        """Test N/A values are normalized to None."""
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(sample_mapping_data))

        loader = VSNMappingLoader(mapping_file)
        await loader.async_load()

        firmware_mapping = loader._mappings["firmware_version"]
        assert firmware_mapping.vsn700_name is None
        assert firmware_mapping.sunspec_name is None

    @pytest.mark.asyncio
    async def test_async_load_handles_empty_entity_category(
        self, sample_mapping_data: list[dict[str, Any]], tmp_path: Path
    ) -> None:
        """Test empty entity_category is normalized to None."""
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(sample_mapping_data))

        loader = VSNMappingLoader(mapping_file)
        await loader.async_load()

        watts_mapping = loader._mappings["watts"]
        assert watts_mapping.entity_category is None

        firmware_mapping = loader._mappings["firmware_version"]
        assert firmware_mapping.entity_category == "diagnostic"

    @pytest.mark.asyncio
    async def test_async_load_skips_rows_without_ha_name(self, tmp_path: Path) -> None:
        """Test rows without HA Name are skipped."""
        data = [
            {
                "REST Name (VSN700)": "Pgrid",
                "REST Name (VSN300)": "m103_1_W",
                # No "HA Name" field
            }
        ]
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(data))

        loader = VSNMappingLoader(mapping_file)
        await loader.async_load()

        assert len(loader._mappings) == 0

    @pytest.mark.asyncio
    async def test_async_load_github_fallback(self, tmp_path: Path) -> None:
        """Test GitHub fallback when local file missing."""
        nonexistent_file = tmp_path / "nonexistent.json"
        loader = VSNMappingLoader(nonexistent_file)

        with patch.object(loader, "_fetch_from_github", new_callable=AsyncMock) as mock_fetch:
            # Make fetch create a file with minimal data
            async def create_file(*args: Any) -> None:
                nonexistent_file.write_text('[{"HA Name": "test"}]')

            mock_fetch.side_effect = create_file

            await loader.async_load()

            mock_fetch.assert_called_once_with(nonexistent_file)


class TestVSNMappingLoaderLookups:
    """Tests for lookup methods."""

    @pytest.fixture
    def loaded_loader(self, tmp_path: Path) -> VSNMappingLoader:
        """Create a loader with sample data."""
        data = [
            {
                "REST Name (VSN700)": "Pgrid",
                "REST Name (VSN300)": "m103_1_W",
                "SunSpec Normalized Name": "W",
                "HA Name": "watts",
                "In /livedata": "✓",
                "In /feeds": "",
                "Label": "Watts",
                "Description": "AC Power",
                "HA Display Name": "Power AC",
                "models": ["M103"],
                "Category": "Inverter",
                "HA Unit of Measurement": "W",
                "HA State Class": "measurement",
                "HA Device Class": "power",
                "Entity Category": "",
                "Available in Modbus": "Yes",
            },
            {
                "REST Name (VSN700)": "Etot",
                "REST Name (VSN300)": "m103_1_WH",
                "SunSpec Normalized Name": "WH",
                "HA Name": "watthours",
                "In /livedata": "✓",
                "In /feeds": "",
                "Label": "Watt-Hours",
                "Description": "Lifetime Energy",
                "HA Display Name": "Energy AC",
                "models": ["M103"],
                "Category": "Inverter",
                "HA Unit of Measurement": "Wh",
                "HA State Class": "total_increasing",
                "HA Device Class": "energy",
                "Entity Category": "",
                "Available in Modbus": "Yes",
            },
        ]
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text(json.dumps(data))

        loader = VSNMappingLoader(mapping_file)
        # Manually load synchronously for fixture
        asyncio.get_event_loop().run_until_complete(loader.async_load())
        return loader

    def test_get_by_vsn300_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by VSN300 name when found."""
        result = loaded_loader.get_by_vsn300("m103_1_W")
        assert result is not None
        assert result.ha_entity_name == "watts"

    def test_get_by_vsn300_not_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by VSN300 name when not found."""
        result = loaded_loader.get_by_vsn300("unknown_point")
        assert result is None

    def test_get_by_vsn700_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by VSN700 name when found."""
        result = loaded_loader.get_by_vsn700("Pgrid")
        assert result is not None
        assert result.ha_entity_name == "watts"

    def test_get_by_vsn700_not_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by VSN700 name when not found."""
        result = loaded_loader.get_by_vsn700("unknown_point")
        assert result is None

    def test_get_by_ha_entity_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by HA entity name when found."""
        result = loaded_loader.get_by_ha_entity("watts")
        assert result is not None
        assert result.vsn700_name == "Pgrid"

    def test_get_by_ha_entity_not_found(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting mapping by HA entity name when not found."""
        result = loaded_loader.get_by_ha_entity("unknown")
        assert result is None

    def test_get_all_mappings(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting all mappings."""
        result = loaded_loader.get_all_mappings()
        assert len(result) == 2
        assert "watts" in result
        assert "watthours" in result

    def test_get_all_mappings_returns_copy(self, loaded_loader: VSNMappingLoader) -> None:
        """Test get_all_mappings returns a copy."""
        result1 = loaded_loader.get_all_mappings()
        result2 = loaded_loader.get_all_mappings()
        assert result1 is not result2

    def test_get_vsn300_to_vsn700_map(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting VSN300 to VSN700 name mapping."""
        result = loaded_loader.get_vsn300_to_vsn700_map()
        assert result["m103_1_W"] == "Pgrid"
        assert result["m103_1_WH"] == "Etot"

    def test_get_vsn700_to_vsn300_map(self, loaded_loader: VSNMappingLoader) -> None:
        """Test getting VSN700 to VSN300 name mapping."""
        result = loaded_loader.get_vsn700_to_vsn300_map()
        assert result["Pgrid"] == "m103_1_W"
        assert result["Etot"] == "m103_1_WH"


class TestVSNMappingLoaderFileOperations:
    """Tests for file operations."""

    def test_write_file(self, tmp_path: Path) -> None:
        """Test _write_file writes content correctly."""
        loader = VSNMappingLoader()
        file_path = tmp_path / "test.json"

        loader._write_file(file_path, '{"test": "data"}')

        assert file_path.exists()
        assert file_path.read_text() == '{"test": "data"}'

    def test_write_file_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test _write_file creates parent directories."""
        loader = VSNMappingLoader()
        file_path = tmp_path / "subdir" / "nested" / "test.json"

        loader._write_file(file_path, '{"test": "data"}')

        assert file_path.exists()

    def test_read_and_parse_json(self, tmp_path: Path) -> None:
        """Test _read_and_parse_json reads and parses correctly."""
        loader = VSNMappingLoader()
        file_path = tmp_path / "test.json"
        file_path.write_text('[{"key": "value"}]')

        result = loader._read_and_parse_json(file_path)

        assert result == [{"key": "value"}]
