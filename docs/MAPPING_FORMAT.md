# VSN-SunSpec Point Mapping

## Overview

The VSN-SunSpec point mapping defines how data from VSN300/VSN700 dataloggers is normalized to Home Assistant entities with proper metadata.

## Files

### Source (Excel)
- **Location**: `docs/vsn-sunspec-point-mapping.xlsx`
- **Purpose**: Human-readable/editable mapping maintained in Excel
- **Sheets**:
  - `All Points`: Complete 259-point mapping
  - `Summary`: Statistics and overview

### Runtime (JSON)
- **Location**: `docs/vsn-sunspec-point-mapping.json`
- **Purpose**: Machine-readable format used by the integration
- **Size**: ~124 KB
- **Points**: 259 mappings

## JSON Structure

Each mapping entry contains:

```json
{
  "REST Name (VSN700)": "Pgrid",
  "REST Name (VSN300)": "m103_1_W",
  "SunSpec Normalized Name": "W",
  "HA Entity Name": "abb_m103_w",
  "In /livedata": "✓",
  "In /feeds": "✓",
  "Label": "Watts",
  "Description": "AC Power",
  "SunSpec Model": "M103",
  "Category": "Inverter",
  "Units": "W",
  "State Class": "measurement",
  "Device Class": "power",
  "Available in Modbus": "YES"
}
```

## Fields

| Field | Description | Example |
|-------|-------------|---------|
| REST Name (VSN700) | Point name in VSN700 API | `Pgrid` |
| REST Name (VSN300) | Point name in VSN300 API | `m103_1_W` |
| SunSpec Normalized Name | Standard SunSpec point name | `W` |
| HA Entity Name | Home Assistant entity ID | `abb_m103_w` |
| In /livedata | Available in livedata endpoint | `✓` or empty |
| In /feeds | Available in feeds endpoint | `✓` or empty |
| Label | Short human-readable name | `Watts` |
| Description | Detailed description | `AC Power` |
| SunSpec Model | SunSpec model number | `M103` |
| Category | Point category | `Inverter` |
| Units | Unit of measurement | `W` |
| State Class | HA state class | `measurement` |
| Device Class | HA device class | `power` |
| Available in Modbus | In Modbus protocol | `YES`/`NO` |

## Converting Excel to JSON

When the Excel file is updated, regenerate the JSON:

```bash
python scripts/generate_mapping_json.py
```

This will:
1. Read `docs/vsn-sunspec-point-mapping.xlsx`
2. Convert to JSON format
3. Write to `docs/vsn-sunspec-point-mapping.json`
4. Display statistics

## Statistics

- **Total mappings**: 259
- **VSN300 points**: 112
- **VSN700 points**: 177
- **Shared points**: 32 (available on both)
- **VSN300-only**: 80
- **VSN700-only**: 145

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
2. **Convert** to JSON using `generate_mapping_json.py`
3. **Commit** both files to git
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

For `vsn_client.py` (self-contained testing script), the JSON can be embedded directly or loaded from a URL, eliminating the need for the docs folder.

## Maintenance

### Adding New Points

1. Open Excel file
2. Add row with all columns filled
3. Save Excel
4. Run `generate_mapping_json.py`
5. Test with `test_vsn_client.py`
6. Commit both files

### Updating Metadata

1. Edit Excel file (labels, descriptions, units, etc.)
2. Run `generate_mapping_json.py`
3. Test changes
4. Commit both files

### Removing Points

1. Delete row in Excel
2. Run `generate_mapping_json.py`
3. Test to ensure no breakage
4. Commit both files

## Notes

- **N/A values**: Converted to `null` in JSON
- **Empty strings**: Preserved as-is
- **Checkmarks** (✓): Used for boolean flags in both formats
- **Case sensitivity**: Point names are case-sensitive
- **Duplicates**: HA entity names must be unique

## See Also

- `generate_mapping_excel.py` - Original script that created the Excel file
- `generate_mapping_json.py` - Converts Excel to JSON
- `mapping_loader.py` - Loads JSON and provides lookup methods
- `normalizer.py` - Uses mappings to normalize VSN data
