"""VSN-SunSpec mapping loader.

Loads the vsn-sunspec-point-mapping.json file to provide lookups for:
- VSN300 → VSN700 cross-references
- VSN700 → SunSpec normalization
- VSN300 → SunSpec normalization
- HA entity metadata (name, label, description, units, device class, etc.)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import aiohttp

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
    ha_display_name: str  # What users see in HA (from enhanced descriptions)
    models: list[str]  # List of models this point belongs to (e.g., ["M103", "M160"])
    category: str
    units: str
    state_class: str
    device_class: str
    entity_category: str | None
    available_in_modbus: str
    icon: str = ""  # MDI icon for entity (e.g., "mdi:information-box-outline")
    suggested_display_precision: int | None = (
        None  # Suggested decimal precision for display
    )


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
        self._loaded = False

        if mapping_file_path is None:
            # Default location: data/vsn-sunspec-point-mapping.json (bundled with client library)
            module_dir = Path(__file__).parent
            mapping_file_path = module_dir / "data" / "vsn-sunspec-point-mapping.json"

        self._mapping_file_path = Path(mapping_file_path)

    async def async_load(self) -> None:
        """Load mappings asynchronously.

        This must be called before using any lookup methods.
        Safe to call multiple times - will only load once.

        Raises:
            FileNotFoundError: If mapping file not found and GitHub fetch fails

        """
        if self._loaded:
            return

        await self._async_load_mappings(self._mapping_file_path)
        self._loaded = True

    async def _fetch_from_github(self, file_path: Path) -> None:
        """Fetch mapping file from GitHub as fallback.

        Args:
            file_path: Local path where the file should be saved

        Raises:
            FileNotFoundError: If GitHub fetch fails

        """
        url = "https://raw.githubusercontent.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/master/docs/vsn-sunspec-point-mapping.json"

        _LOGGER.warning("Local mapping file not found at %s", file_path)
        _LOGGER.info("Attempting to fetch from GitHub: %s", url)

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response,
            ):
                if response.status == 200:
                    content = await response.text()
                    # Save to local cache using thread pool to avoid blocking
                    await asyncio.to_thread(self._write_file, file_path, content)
                    _LOGGER.info(
                        "Downloaded mapping file from GitHub and cached locally"
                    )
                else:
                    raise FileNotFoundError(
                        f"Failed to fetch from GitHub: HTTP {response.status}"
                    )
        except aiohttp.ClientError as err:
            raise FileNotFoundError(
                f"Failed to fetch mapping from GitHub: {err}"
            ) from err

    def _write_file(self, file_path: Path, content: str) -> None:
        """Write content to file (runs in thread pool)."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def _read_and_parse_json(self, file_path: Path) -> list[dict]:
        """Read and parse JSON file (runs in thread pool).

        Uses Path.read_text() as recommended by HA best practices.
        See: https://developers.home-assistant.io/docs/asyncio_blocking_operations/#open
        """
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)

    async def _async_load_mappings(self, file_path: Path) -> None:
        """Load mappings from JSON file with GitHub fallback."""
        # Check if file exists using thread pool to avoid blocking
        file_exists = await asyncio.to_thread(file_path.exists)

        if not file_exists:
            _LOGGER.warning("Bundled mapping file not found: %s", file_path)
            _LOGGER.info("Attempting to fetch from GitHub as fallback...")

            try:
                await self._fetch_from_github(file_path)
            except Exception as err:
                raise FileNotFoundError(
                    f"Mapping file not found locally and GitHub fetch failed: {err}"
                ) from err

        _LOGGER.debug("Loading VSN-SunSpec mappings from %s", file_path)

        # Load and parse JSON file in thread pool to avoid blocking
        mappings_data = await asyncio.to_thread(self._read_and_parse_json, file_path)

        # Expected fields (from v2 JSON structure):
        # - REST Name (VSN700)
        # - REST Name (VSN300)
        # - SunSpec Normalized Name
        # - HA Name
        # - In /livedata
        # - In /feeds
        # - Label
        # - Description
        # - HA Display Name
        # - models (array of model names)
        # - Category
        # - HA Unit of Measurement
        # - HA State Class
        # - HA Device Class
        # - Entity Category
        # - Available in Modbus
        # - Data Source

        for row in mappings_data:
            vsn700 = row.get("REST Name (VSN700)")
            vsn300 = row.get("REST Name (VSN300)")
            sunspec = row.get("SunSpec Normalized Name")
            ha_entity = row.get("HA Name")
            in_livedata = row.get("In /livedata") == "✓"
            in_feeds = row.get("In /feeds") == "✓"
            label = row.get("Label") or ""
            description = row.get("Description") or ""
            models = row.get("models") or []  # New: array of models
            category = row.get("Category") or ""
            units = row.get("HA Unit of Measurement") or ""
            state_class = row.get("HA State Class") or ""
            device_class = row.get("HA Device Class") or ""
            entity_category = row.get("Entity Category") or None
            available_in_modbus = row.get("Available in Modbus") or ""
            icon = row.get("HA Icon") or ""
            suggested_display_precision = row.get("Suggested Display Precision")

            # Get HA Display Name (fallback to description if not present for backward compat)
            ha_display_name = row.get("HA Display Name") or description or label

            # Normalize N/A values
            if vsn700 == "N/A":
                vsn700 = None
            if vsn300 == "N/A":
                vsn300 = None
            if sunspec == "N/A":
                sunspec = None

            # Normalize empty entity_category to None
            if entity_category == "":
                entity_category = None

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
                ha_display_name=ha_display_name,
                models=models,
                category=category,
                units=units,
                state_class=state_class,
                device_class=device_class,
                entity_category=entity_category,
                available_in_modbus=available_in_modbus,
                icon=icon,
                suggested_display_precision=suggested_display_precision,
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
