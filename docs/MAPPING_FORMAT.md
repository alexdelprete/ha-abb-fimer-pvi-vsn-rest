# VSN-SunSpec Point Mapping

## Overview

The VSN-SunSpec point mapping defines how data from VSN300/VSN700 dataloggers
is normalized to Home Assistant entities with proper metadata.

## Files

### Source (Generator Script)

- **Location**: `scripts/vsn-mapping-generator/generate_mapping.py`
- **Purpose**: Single source of truth for all sensor mappings
- **Points**: 253 unique mappings (v1.2.0)

### Output (Excel)

- **Location**: `scripts/vsn-mapping-generator/output/vsn-sunspec-point-mapping.xlsx`
- **Purpose**: Human-readable review format
- **Format**: Deduplicated structure with model flag columns

### Runtime (JSON)

- **Location**: `custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/data/vsn-sunspec-point-mapping.json`
- **Purpose**: Machine-readable format used by the integration at runtime
- **Points**: 253 mappings
- **Format**: Each point includes `models` array for multi-model support

## JSON Structure

Each mapping entry contains:

```json
{
  "REST Name (VSN700)": "Pgrid",
  "REST Name (VSN300)": "m103_1_W",
  "SunSpec Normalized Name": "W",
  "HA Name": "watts",
  "In /livedata": "✓",
  "In /feeds": "✓",
  "Label": "Watts",
  "Description": "AC Power",
  "HA Display Name": "AC Power",
  "Category": "Inverter",
  "HA Unit of Measurement": "W",
  "HA State Class": "measurement",
  "HA Device Class": "power",
  "Entity Category": "",
  "Available in Modbus": true,
  "Data Source": "SunSpec Description (M103)",
  "Model_Notes": "",
  "models": ["M103", "M802"]
}
```

## Fields

| Field | Description | Example |
|-------|-------------|---------|
| REST Name (VSN700) | Point name in VSN700 API | `Pgrid` |
| REST Name (VSN300) | Point name in VSN300 API | `m103_1_W` |
| SunSpec Normalized Name | Standard SunSpec point name | `W` |
| HA Name | Home Assistant entity name (internal) | `watts` |
| In /livedata | Available in livedata endpoint | `✓` or empty |
| In /feeds | Available in feeds endpoint | `✓` or empty |
| Label | Short human-readable name | `Watts` |
| Description | Detailed technical description | `AC Power` |
| HA Display Name | User-facing display name | `AC Power` |
| Category | Point category | `Inverter` |
| HA Unit of Measurement | Home Assistant unit (SensorDeviceClass) | `W` |
| HA State Class | Home Assistant state class (SensorStateClass) | `measurement` |
| HA Device Class | Home Assistant device class | `power` |
| Entity Category | HA entity category (diagnostic, config, etc.) | `` or `diagnostic` |
| Available in Modbus | In Modbus protocol | `true`/`false` |
| Data Source | Origin of mapping metadata | `SunSpec Description (M103)` |
| Model_Notes | Additional notes about model compatibility | `` |
| models | Array of applicable SunSpec/VSN models | `["M103", "M802"]` |

## Regenerating Mapping Files

**Important**: Never edit JSON or Excel files directly. Always use the generator script.

### Step 1: Edit Generator Script

```bash
# Edit the source of truth
scripts/vsn-mapping-generator/generate_mapping.py
```

### Step 2: Regenerate Excel and JSON

```bash
python scripts/vsn-mapping-generator/generate_mapping.py
python scripts/vsn-mapping-generator/convert_to_json.py
```

This will:

1. Generate Excel from source data and metadata dictionaries
2. Convert Excel to JSON format with models array structure
3. Copy JSON to `custom_components/.../data/vsn-sunspec-point-mapping.json`
4. Display model statistics

## Statistics (v1.2.0)

- **Total unique mappings**: 253
- **Translation entities**: 246
- **Model distribution**:
  - M1 (Common): ~6 points
  - M103 (Inverter): ~23 points
  - M160 (MPPT): ~6 points
  - M203 (Meter Three-Phase): ~17 points
  - M802 (Battery): ~14 points
  - M64061 (ABB Proprietary): ~74 points
  - VSN300-only: ~73 points
  - VSN700-only: ~10 points

## Point Categories

- **Inverter**: Core inverter measurements (power, voltage, current, frequency)
- **MPPT**: Maximum Power Point Tracker data (DC input from solar panels)
- **Storage**: Battery/storage system data (if available)
- **Meter**: Energy meter readings
- **System**: Device and system information

## Why Both Excel and JSON?

### Excel (.xlsx)

- ✅ Easy to edit in Excel/LibreOffice
- ✅ Good for bulk updates and reviews
- ✅ Human-readable columns and formatting
- ✅ Version control in git (though diffs are difficult)

### JSON (.json)

- ✅ No external library dependency (openpyxl)
- ✅ Faster loading (native Python JSON parser)
- ✅ Can be embedded in self-contained scripts
- ✅ Better for version control (clear diffs)
- ✅ Portable and lightweight

## Workflow

1. **Edit** generator script (`scripts/vsn-mapping-generator/generate_mapping.py`)
2. **Regenerate** Excel: `python scripts/vsn-mapping-generator/generate_mapping.py`
3. **Convert** to JSON: `python scripts/vsn-mapping-generator/convert_to_json.py`
4. **Commit** generator + all generated files to git
5. **Integration** loads JSON at runtime (no openpyxl needed)

## Usage in Code

```python
from mapping_loader import VSNMappingLoader

# Load mappings
loader = VSNMappingLoader()

# Lookup by VSN300 name
mapping = loader.get_by_vsn300("m103_1_W")
print(mapping.ha_entity_name)  # abb_m103_w

# Lookup by VSN700 name
mapping = loader.get_by_vsn700("Pgrid")
print(mapping.label)  # Watts

# Lookup by HA entity name
mapping = loader.get_by_ha_entity("abb_m103_w")
print(mapping.units)  # W
```

## Self-Contained Scripts

For `vsn_client.py` (self-contained testing script), the JSON can be embedded
directly or loaded from a URL, eliminating the need for the docs folder.

## Maintenance

### Adding New Sensors

1. Edit `scripts/vsn-mapping-generator/generate_mapping.py`
2. Add entry to `SUNSPEC_TO_HA_METADATA` dictionary
3. Add display name to `DISPLAY_NAME_STANDARDIZATION` if needed
4. Run: `python scripts/vsn-mapping-generator/generate_mapping.py`
5. Run: `python scripts/vsn-mapping-generator/convert_to_json.py`
6. Test changes
7. Commit generator + all generated files

### Updating Sensor Metadata

1. Edit appropriate dictionary in `generate_mapping.py`:
   - `SUNSPEC_TO_HA_METADATA` for device_class, state_class, units
   - `DISPLAY_NAME_STANDARDIZATION` for display names
   - `DESCRIPTION_IMPROVEMENTS` for descriptions
2. Regenerate: `python scripts/vsn-mapping-generator/generate_mapping.py`
3. Convert: `python scripts/vsn-mapping-generator/convert_to_json.py`
4. Test changes
5. Commit all files

### Removing Sensors

1. Remove entry from `generate_mapping.py` dictionaries
2. Regenerate and convert
3. Test to ensure no breakage
4. Commit all files

## Notes

- **N/A values**: Converted to `null` in JSON
- **Empty strings**: Preserved as-is
- **Checkmarks** (✓): Used for boolean flags in both formats
- **Case sensitivity**: Point names are case-sensitive
- **Duplicates**: HA entity names must be unique

## See Also

- `scripts/vsn-mapping-generator/generate_mapping.py` - **Single source of truth** for all mappings
- `scripts/vsn-mapping-generator/convert_to_json.py` - Converts Excel to JSON
- `custom_components/.../abb_fimer_vsn_rest_client/mapping_loader.py` - Loads JSON and provides lookup methods
- `custom_components/.../abb_fimer_vsn_rest_client/normalizer.py` - Uses mappings to normalize VSN data
- [MAPPING_NOTES.md](MAPPING_NOTES.md) - Additional notes on entity naming and time periods
- [CLAUDE.md](../CLAUDE.md) - Complete development guidelines

---

**Last Updated**: 2025-11-24
**Version**: v1.2.0
