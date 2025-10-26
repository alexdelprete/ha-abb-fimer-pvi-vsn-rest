"""VSN-SunSpec mapping loader.

Loads the vsn-sunspec-point-mapping.json file to provide lookups for:
- VSN300 → VSN700 cross-references
- VSN700 → SunSpec normalization
- VSN300 → SunSpec normalization
- HA entity metadata (name, label, description, units, device class, etc.)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


@dataclass
class PointMapping:
    """Mapping information for a single point."""

    vsn700_name: str | None
    vsn300_name: str | None
    sunspec_name: str | None
    ha_entity_name: str
    in_livedata: bool
    in_feeds: bool
    label: str
    description: str
    model: str
    category: str
    units: str
    state_class: str
    device_class: str
    available_in_modbus: str


class VSNMappingLoader:
    """Load and provide access to VSN-SunSpec point mappings."""

    def __init__(self, mapping_file_path: str | Path | None = None):
        """Initialize the mapping loader.

        Args:
            mapping_file_path: Path to vsn-sunspec-point-mapping.json.
                              If None, will look in expected location relative to this module.

        """
        self._mappings: dict[str, PointMapping] = {}
        self._vsn300_index: dict[str, str] = {}  # vsn300_name → key
        self._vsn700_index: dict[str, str] = {}  # vsn700_name → key
        self._ha_entity_index: dict[str, str] = {}  # ha_entity_name → key

        if mapping_file_path is None:
            # Default location: docs/vsn-sunspec-point-mapping.json
            module_dir = Path(__file__).parent.parent.parent.parent
            mapping_file_path = module_dir / "docs" / "vsn-sunspec-point-mapping.json"

        self._load_mappings(Path(mapping_file_path))

    def _load_mappings(self, file_path: Path) -> None:
        """Load mappings from JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {file_path}")

        _LOGGER.debug("Loading VSN-SunSpec mappings from %s", file_path)

        with file_path.open(encoding="utf-8") as f:
            mappings_data = json.load(f)

        # Expected fields (from generate_mapping_json.py):
        # - REST Name (VSN700)
        # - REST Name (VSN300)
        # - SunSpec Normalized Name
        # - HA Entity Name
        # - In /livedata
        # - In /feeds
        # - Label
        # - Description
        # - SunSpec Model
        # - Category
        # - Units
        # - State Class
        # - Device Class
        # - Available in Modbus

        for row in mappings_data:
            vsn700 = row.get("REST Name (VSN700)")
            vsn300 = row.get("REST Name (VSN300)")
            sunspec = row.get("SunSpec Normalized Name")
            ha_entity = row.get("HA Entity Name")
            in_livedata = row.get("In /livedata") == "✓"
            in_feeds = row.get("In /feeds") == "✓"
            label = row.get("Label") or ""
            description = row.get("Description") or ""
            model = row.get("SunSpec Model") or ""
            category = row.get("Category") or ""
            units = row.get("Units") or ""
            state_class = row.get("State Class") or ""
            device_class = row.get("Device Class") or ""
            available_in_modbus = row.get("Available in Modbus") or ""

            # Normalize N/A values
            if vsn700 == "N/A":
                vsn700 = None
            if vsn300 == "N/A":
                vsn300 = None
            if sunspec == "N/A":
                sunspec = None

            if not ha_entity:
                _LOGGER.warning("Row missing HA entity name, skipping")
                continue

            mapping = PointMapping(
                vsn700_name=vsn700,
                vsn300_name=vsn300,
                sunspec_name=sunspec,
                ha_entity_name=ha_entity,
                in_livedata=in_livedata,
                in_feeds=in_feeds,
                label=label,
                description=description,
                model=model,
                category=category,
                units=units,
                state_class=state_class,
                device_class=device_class,
                available_in_modbus=available_in_modbus,
            )

            # Use HA entity name as primary key
            self._mappings[ha_entity] = mapping

            # Build indexes
            if vsn300:
                self._vsn300_index[vsn300] = ha_entity
            if vsn700:
                self._vsn700_index[vsn700] = ha_entity
            self._ha_entity_index[ha_entity] = ha_entity

        _LOGGER.info(
            "Loaded %d point mappings (%d VSN300, %d VSN700)",
            len(self._mappings),
            len(self._vsn300_index),
            len(self._vsn700_index),
        )

    def get_by_vsn300(self, vsn300_name: str) -> PointMapping | None:
        """Get mapping by VSN300 point name (e.g., 'm103_1_W')."""
        key = self._vsn300_index.get(vsn300_name)
        return self._mappings.get(key) if key else None

    def get_by_vsn700(self, vsn700_name: str) -> PointMapping | None:
        """Get mapping by VSN700 point name (e.g., 'Pgrid')."""
        key = self._vsn700_index.get(vsn700_name)
        return self._mappings.get(key) if key else None

    def get_by_ha_entity(self, ha_entity_name: str) -> PointMapping | None:
        """Get mapping by HA entity name (e.g., 'abb_m103_w')."""
        return self._mappings.get(ha_entity_name)

    def get_all_mappings(self) -> dict[str, PointMapping]:
        """Get all mappings indexed by HA entity name."""
        return self._mappings.copy()

    def get_vsn300_to_vsn700_map(self) -> dict[str, str]:
        """Get VSN300 → VSN700 name mapping."""
        result = {}
        for vsn300_name, key in self._vsn300_index.items():
            mapping = self._mappings[key]
            if mapping.vsn700_name:
                result[vsn300_name] = mapping.vsn700_name
        return result

    def get_vsn700_to_vsn300_map(self) -> dict[str, str]:
        """Get VSN700 → VSN300 name mapping."""
        result = {}
        for vsn700_name, key in self._vsn700_index.items():
            mapping = self._mappings[key]
            if mapping.vsn300_name:
                result[vsn700_name] = mapping.vsn300_name
        return result
