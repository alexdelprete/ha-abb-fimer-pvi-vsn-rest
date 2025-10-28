"""Data normalizer for VSN300/VSN700 to SunSpec schema.

This normalizer converts VSN REST API data to a normalized SunSpec-like schema
using the vsn-sunspec-point-mapping.xlsx as the source of truth.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from .mapping_loader import PointMapping, VSNMappingLoader
except ImportError:
    from mapping_loader import PointMapping, VSNMappingLoader

_LOGGER = logging.getLogger(__name__)


class VSNDataNormalizer:
    """Normalize VSN300/VSN700 data to SunSpec schema."""

    def __init__(self, vsn_model: str, mapping_loader: VSNMappingLoader | None = None):
        """Initialize normalizer.

        Args:
            vsn_model: VSN model type ('VSN300' or 'VSN700')
            mapping_loader: Optional pre-loaded mapping loader.
                           If None, will create a new one.

        """
        if vsn_model not in ("VSN300", "VSN700"):
            raise ValueError(f"Invalid VSN model: {vsn_model}")

        self.vsn_model = vsn_model
        self._mapping_loader = mapping_loader or VSNMappingLoader()
        self._loaded = False

        _LOGGER.debug("Initialized normalizer for %s", vsn_model)

    async def async_load(self) -> None:
        """Load mappings asynchronously.

        This must be called after __init__ before using normalize().
        Safe to call multiple times - will only load once.

        Raises:
            FileNotFoundError: If mapping file not found and GitHub fetch fails

        """
        if self._loaded:
            return

        await self._mapping_loader.async_load()
        self._loaded = True

    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize VSN livedata to SunSpec schema.

        Args:
            raw_data: Raw VSN livedata response. Expected structure:
                      {device_id: {'points': [{'name': str, 'value': Any}, ...]}}

        Returns:
            Normalized data structure:
            {
                'devices': {
                    device_id: {
                        'points': {
                            ha_entity_name: {
                                'value': Any,
                                'label': str,
                                'description': str,
                                'units': str,
                                'device_class': str,
                                'state_class': str,
                                'entity_category': str | None,
                                'category': str,
                                'model': str,
                                'sunspec_name': str | None,
                                'vsn300_name': str | None,
                                'vsn700_name': str | None,
                            }
                        }
                    }
                }
            }

        """
        normalized = {"devices": {}}

        for device_id, device_data in raw_data.items():
            if "points" not in device_data:
                _LOGGER.warning("Device %s has no points, skipping", device_id)
                continue

            # Determine the actual device identifier to use
            # For datalogger devices (identified by MAC address pattern),
            # use the logger serial number instead
            actual_device_id = device_id

            # Check if this is a datalogger (MAC address pattern: xx:xx:xx:xx:xx:xx)
            if ":" in device_id:
                # Look for "sn" point in the data to get logger serial number
                for point in device_data["points"]:
                    if point.get("name") == "sn":
                        actual_device_id = point.get("value", device_id)
                        _LOGGER.debug(
                            "Using logger S/N '%s' instead of MAC '%s' for device ID",
                            actual_device_id,
                            device_id,
                        )
                        break

            normalized_points = {}

            for point in device_data["points"]:
                point_name = point.get("name")
                point_value = point.get("value")

                if not point_name:
                    continue

                # Look up mapping based on VSN model
                if self.vsn_model == "VSN300":
                    mapping = self._mapping_loader.get_by_vsn300(point_name)
                else:  # VSN700
                    mapping = self._mapping_loader.get_by_vsn700(point_name)

                if not mapping:
                    _LOGGER.debug(
                        "No mapping found for %s point: %s",
                        self.vsn_model,
                        point_name,
                    )
                    continue

                # Create normalized point entry
                normalized_point = {
                    "value": point_value,
                    "label": mapping.label,
                    "description": mapping.description,
                    "ha_display_name": mapping.ha_display_name,  # What users see in HA
                    "units": mapping.units,
                    "device_class": mapping.device_class,
                    "state_class": mapping.state_class,
                    "entity_category": mapping.entity_category,
                    "category": mapping.category,
                    "model": mapping.model,
                    "sunspec_name": mapping.sunspec_name,
                    "vsn300_name": mapping.vsn300_name,
                    "vsn700_name": mapping.vsn700_name,
                }

                # Use HA entity name as the key for normalized data
                normalized_points[mapping.ha_entity_name] = normalized_point

            if normalized_points:
                # Use actual_device_id (logger S/N for datalogger, inverter S/N for inverter)
                normalized["devices"][actual_device_id] = {"points": normalized_points}

        _LOGGER.debug(
            "Normalized %d devices with %d total points",
            len(normalized["devices"]),
            sum(len(d["points"]) for d in normalized["devices"].values()),
        )

        return normalized

    def get_point_metadata(self, point_name: str) -> PointMapping | None:
        """Get metadata for a point by its VSN name.

        Args:
            point_name: VSN300 or VSN700 point name

        Returns:
            PointMapping if found, None otherwise

        """
        if self.vsn_model == "VSN300":
            return self._mapping_loader.get_by_vsn300(point_name)
        return self._mapping_loader.get_by_vsn700(point_name)

    def get_all_expected_points(self) -> list[PointMapping]:
        """Get all expected points for this VSN model.

        Returns:
            List of PointMapping objects that are available for this VSN model

        """
        all_mappings = self._mapping_loader.get_all_mappings()

        # Include points that are available for this VSN model
        return [
            mapping
            for mapping in all_mappings.values()
            if (self.vsn_model == "VSN300" and mapping.vsn300_name)
            or (self.vsn_model == "VSN700" and mapping.vsn700_name)
        ]

    def get_vsn_cross_reference(self, point_name: str) -> str | None:
        """Get the equivalent point name in the other VSN model.

        Args:
            point_name: VSN300 or VSN700 point name

        Returns:
            Equivalent point name in the other VSN model, or None if not found

        """
        mapping = self.get_point_metadata(point_name)
        if not mapping:
            return None

        if self.vsn_model == "VSN300":
            return mapping.vsn700_name
        return mapping.vsn300_name
