# VSN-SunSpec Point Mapping

## Overview

The VSN-SunSpec point mapping defines how data from VSN300/VSN700 dataloggers
is normalized to Home Assistant entities with proper metadata.

## Files

### Source (Excel)

- **Location**: `docs/vsn-sunspec-point-mapping.xlsx`
- **Purpose**: Human-readable/editable mapping maintained in Excel
- **Format**: Deduplicated structure with model flag columns
- **Points**: 210 unique mappings (deduplicated from original 277)

### Runtime (JSON)

- **Location**: `docs/vsn-sunspec-point-mapping.json`
- **Purpose**: Machine-readable format used by the integration
- **Size**: ~95 KB
- **Points**: 210 mappings
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

## Converting Excel to JSON

When the Excel file is updated, regenerate the JSON:

```bash
python scripts/convert_excel_to_json.py
```

This will:

1. Read `docs/vsn-sunspec-point-mapping.xlsx`
2. Convert to JSON format with models array structure
3. Write to `docs/vsn-sunspec-point-mapping.json`
4. Copy to `custom_components/abb_fimer_pvi_vsn_rest/data/vsn-sunspec-point-mapping.json`
5. Display model statistics

## Statistics (Deduplicated)

- **Total unique mappings**: 210 (deduplicated from original 277)
- **Model distribution**:
  - M1 (Common): 6 points
  - M103 (Inverter Single-Phase): 23 points
  - M160 (MPPT): 6 points
  - M203 (Meter Three-Phase): 17 points
  - M802 (Battery): 14 points
  - M64061 (ABB Proprietary): 74 points
  - VSN300-only: 73 points
  - VSN700-only: 10 points
  - ABB Proprietary: 47 points

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

1. **Edit** mapping in Excel (`vsn-sunspec-point-mapping.xlsx`)
2. **Convert** to JSON using `convert_excel_to_json.py`
3. **Commit** both files to git (Excel + both JSON copies)
4. **Integration** loads JSON at runtime (no openpyxl needed)

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

### Adding New Points

1. Open Excel file (`vsn-sunspec-point-mapping.xlsx`)
2. Add row with all columns filled
3. Set appropriate model flags (M1, M103, etc.)
4. Save Excel
5. Run `convert_excel_to_json.py`
6. Test with `test_vsn_client.py`
7. Commit all files (Excel + both JSON copies)

### Updating Metadata

1. Edit Excel file (labels, descriptions, HA units, device classes, etc.)
2. Run `convert_excel_to_json.py`
3. Test changes
4. Commit all files

### Removing Points

1. Delete row in Excel
2. Run `convert_excel_to_json.py`
3. Test to ensure no breakage
4. Commit all files

## Notes

- **N/A values**: Converted to `null` in JSON
- **Empty strings**: Preserved as-is
- **Checkmarks** (✓): Used for boolean flags in both formats
- **Case sensitivity**: Point names are case-sensitive
- **Duplicates**: HA entity names must be unique

## See Also

- `generate_mapping_excel.py` - Original script that created the Excel file
- `convert_excel_to_json.py` - Converts Excel (with model flags) to JSON
- `analyze_and_deduplicate_mapping.py` - Analyzes and deduplicates mapping entries
- `apply_mapping_fixes.py` - Applies automated description and category fixes
- `mapping_loader.py` - Loads JSON and provides lookup methods
- `normalizer.py` - Uses mappings to normalize VSN data
