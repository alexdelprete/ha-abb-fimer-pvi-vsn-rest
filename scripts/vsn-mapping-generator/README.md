# VSN-SunSpec Point Mapping Generator

A self-contained tool for generating comprehensive point mappings between VSN300/VSN700 dataloggers and SunSpec models for the ABB FIMER PVI VSN REST Home Assistant integration.

## Overview

This generator creates a complete mapping file that:
- Maps VSN300/VSN700 REST API points to SunSpec normalized names
- Includes metadata like labels, descriptions, units, and Home Assistant device classes
- Tracks which SunSpec models each point belongs to (M1, M103, M160, M203, M802, M64061)
- Identifies VSN-only and ABB proprietary points
- Processes data from `/livedata`, `/feeds`, and `/status` endpoints

## Directory Structure

```
vsn-mapping-generator/
├── generate_mapping.py           # Main mapping generator script
├── convert_to_json.py            # Excel to JSON converter
├── extract_manual_changes.py    # Backport tool for manual Excel edits
├── README.md                     # This file
├── data/                         # Input data files
│   ├── vsn300/
│   │   ├── livedata.json        # VSN300 livedata endpoint data
│   │   ├── feeds.json           # VSN300 feeds metadata
│   │   └── status.json          # VSN300 status endpoint data
│   ├── vsn700/
│   │   ├── livedata.json        # VSN700 livedata endpoint data
│   │   ├── feeds.json           # VSN700 feeds metadata
│   │   └── status.json          # VSN700 status endpoint data
│   └── sunspec/
│       ├── models_workbook.xlsx # Official SunSpec model definitions
│       └── ABB_SunSpec_Modbus.xlsx # ABB proprietary M64061 definitions
└── output/
    ├── vsn-sunspec-point-mapping.xlsx  # Generated Excel mapping
    └── vsn-sunspec-point-mapping.json  # Generated JSON for integration
```

## Usage

### Quick Start

```bash
# Generate mapping files in one command
python generate_mapping.py && python convert_to_json.py
```

### 1. Generate the Mapping Excel File

```bash
python generate_mapping.py
```

This will:
- Load all VSN data from the `data/` directory
- Load SunSpec model definitions
- Process status endpoint data
- Generate a comprehensive Excel file with 26 columns
- Create three sheets: All Points, Summary, Changelog

### 2. Convert Excel to JSON

```bash
python convert_to_json.py
```

This will:
- Read the generated Excel file
- Convert it to JSON format
- Save to `output/vsn-sunspec-point-mapping.json`
- **Automatically copy to the integration's data folder**

**IMPORTANT**: Always run both scripts together. The JSON file must be regenerated after any Excel changes.

## Output Format

### Excel Columns (26 total)

1. **Model Flags** (9 columns): M1, M103, M160, M203, M802, M64061, VSN300_Only, VSN700_Only, ABB_Proprietary
2. **Point Names** (3 columns): REST Name (VSN700), REST Name (VSN300), SunSpec Normalized Name
3. **HA Integration** (4 columns): HA Name, HA Display Name, HA Unit of Measurement, HA State Class, HA Device Class
4. **Metadata** (5 columns): Label, Description, Category, Entity Category, Available in Modbus
5. **Tracking** (3 columns): In /livedata, In /feeds, Data Source
6. **Notes** (1 column): Model_Notes

### JSON Structure

```json
[
  {
    "models": ["M103"],
    "REST Name (VSN700)": "Pgrid",
    "REST Name (VSN300)": "m103_1_W",
    "SunSpec Normalized Name": "W",
    "HA Name": "watts",
    "Label": "Active Power",
    "Description": "Total active power",
    "HA Display Name": "Grid Power",
    "Category": "Inverter",
    "HA Unit of Measurement": "W",
    "HA State Class": "measurement",
    "HA Device Class": "power",
    ...
  }
]
```

## Data Sources

### VSN Data Files
- **livedata.json**: Real-time measurement points from inverters, meters, and batteries
- **feeds.json**: Metadata including titles, units, and descriptions
- **status.json**: Device information, firmware versions, network configuration

### SunSpec Models
- **models_workbook.xlsx**: Official SunSpec Alliance model definitions (M1, M103, M160, etc.)
- **ABB_SunSpec_Modbus.xlsx**: ABB/FIMER proprietary M64061 model points

## Features

### Status Endpoint Processing (v2.0.0+)
The generator now processes `/status` endpoint data, extracting:
- Device information (model, serial number, firmware versions)
- Network configuration (IP addresses, WLAN status)
- Logger information (board model, hostname)

### Automatic Categorization
Points are automatically categorized into:
- Inverter
- Energy Counter
- Battery
- Meter
- Device Info
- Network
- Status
- System Monitoring
- Datalogger

### Data Source Priority
Descriptions are selected using a 4-tier priority system:
1. SunSpec official descriptions
2. VSN feeds titles (if descriptive)
3. Enhanced generated descriptions
4. Label fallback

### Deduplication
Points with the same SunSpec normalized name are merged, preserving the best available metadata from all sources.

## Updating Data

### To Update VSN Data
1. Export new data from VSN300/VSN700 devices
2. Place JSON files in appropriate `data/vsn300/` or `data/vsn700/` directories
3. Run `generate_mapping.py`

### To Update SunSpec Models
1. Download latest model workbook from SunSpec Alliance
2. Replace `data/sunspec/models_workbook.xlsx`
3. Run `generate_mapping.py`

## Modifying Point Metadata

### CRITICAL: Understanding the Generator Pipeline

The generator applies corrections in a specific order. **Order matters!** Changes in the wrong order will fail silently.

```python
# Correct order in create_row_with_model_flags():
1. apply_display_name_corrections(row)
2. apply_label_corrections(row)         # MUST run before device_class_fixes!
3. apply_device_class_fixes(row)        # Uses corrected label names
4. clean_energy_prefix()
5. standardize_time_periods()
6. Apply UNIT_CORRECTIONS
7. Apply SUNSPEC_TO_HA_METADATA
```

**WHY THIS MATTERS**: `DEVICE_CLASS_FIXES` is keyed by **label names** (e.g., "Serial Number"), not SunSpec names (e.g., "SN" or "sn"). If you apply device class fixes before label corrections, the fixes won't match and will fail silently.

### Common Metadata Dictionaries

When modifying point metadata in `generate_mapping.py`, use these dictionaries:

| Dictionary | Purpose | Key Type | Line # | Example |
|------------|---------|----------|--------|---------|
| `VSN_TO_SUNSPEC_MAP` | Map VSN REST names to SunSpec | VSN REST name | ~78 | `"PF": {"sunspec": "PF", "units": "", ...}` |
| `SUNSPEC_TO_HA_METADATA` | HA device class, state class, units | SunSpec name | ~444 | `"PF": {"device_class": "power_factor", ...}` |
| `DESCRIPTION_IMPROVEMENTS` | Override/improve descriptions | SunSpec name | ~579 | `"PF": "Power factor at grid connection"` |
| `DISPLAY_NAME_CORRECTIONS` | Fix display names | Display name | ~324 | `"Pf": "Power Factor"` |
| `LABEL_CORRECTIONS` | Fix label text (spacing, capitalization) | Label text | ~396 | `"Sn": "Serial Number"` |
| `DEVICE_CLASS_FIXES` | Override device class/unit/category | **Label name** | ~378 | `"Serial Number": {"entity_category": "diagnostic"}` |
| `UNIT_CORRECTIONS` | Fix incorrect units | SunSpec name | ~409 | `"ILeakDcAc": "mA"` |

### Adding Diagnostic Categories

Device info and configuration entities should be marked as `diagnostic`:

```python
# In DEVICE_CLASS_FIXES (keyed by LABEL, not SunSpec name!)
DEVICE_CLASS_FIXES = {
    "Serial Number": {"entity_category": "diagnostic"},
    "Manufacturer": {"entity_category": "diagnostic"},
    "Model": {"entity_category": "diagnostic"},
    "Firmware Version": {"entity_category": "diagnostic"},
}
```

**Common mistake**: Using SunSpec names like "SN" instead of the corrected label "Serial Number".

### Fixing Display Names or Labels

**Problem**: Point shows wrong text (e.g., "sn" shows as "Nominal Apparent Power")

**Solution**: The point was incorrectly classified. Fix in multiple places:

1. Remove from wrong dictionary:
   ```python
   # In SUNSPEC_TO_HA_METADATA, remove:
   # "sn": {"device_class": "apparent_power", ...}  # WRONG - sn is serial number!
   ```

2. Add correct description:
   ```python
   # In DESCRIPTION_IMPROVEMENTS:
   "sn": "Datalogger serial number",
   ```

3. Add correct label:
   ```python
   # In LABEL_CORRECTIONS:
   "Sn": "Serial Number",
   ```

4. Add metadata fixes:
   ```python
   # In DEVICE_CLASS_FIXES (use corrected label!):
   "Serial Number": {"entity_category": "diagnostic"},
   ```

### Fixing Units

**Problem**: Unit shows incorrectly (e.g., "1.0%" instead of "100%")

**Solution**: Fix in TWO places:

1. In `VSN_TO_SUNSPEC_MAP`:
   ```python
   "PF": {"sunspec": "PF", "units": "", ...}  # Empty for power_factor
   ```

2. In `SUNSPEC_TO_HA_METADATA`:
   ```python
   "PF": {"device_class": "power_factor", "unit": ""},  # HA handles formatting
   ```

**Note**: Some device classes (like `power_factor`) handle their own formatting. Use empty string `""`, not `None`.

## Manual Editing Workflow (v2.0.9+)

You can now manually edit the generated Excel file and backport your changes to the generator:

### 1. Save a Backup
```bash
copy output\vsn-sunspec-point-mapping.xlsx output\vsn-sunspec-point-mapping-original.xlsx
```

### 2. Edit the Excel File
Open `output/vsn-sunspec-point-mapping.xlsx` and edit:
- **Label**: Human-readable label for the point
- **Description**: Detailed description of what the point measures
- **HA Display Name**: User-friendly name shown in Home Assistant

### 3. Extract Changes
```bash
python extract_manual_changes.py
```

This will:
- Compare original vs edited files
- Extract all differences
- Generate Python code in `output/manual_changes_backport.txt`

### 4. Apply Changes to Generator
1. Open `output/manual_changes_backport.txt`
2. Copy the generated code sections
3. Paste into the appropriate dictionaries in `generate_mapping.py`:
   - `DESCRIPTION_IMPROVEMENTS` (around line 579)
   - `DISPLAY_NAME_CORRECTIONS` (around line 139)
   - `LABEL_CORRECTIONS` (around line 422)

### 5. Regenerate
```bash
python generate_mapping.py && python convert_to_json.py
```

Your manual improvements are now permanent and will be applied on every regeneration!

## Testing and Verification

After regenerating mapping files, always verify critical fixes:

```bash
# Check specific point metadata
cd ../.. && grep -i '"Label": "Serial Number"' custom_components/abb_fimer_pvi_vsn_rest/data/vsn-sunspec-point-mapping.json -A 10

# Check power factor unit (should be empty "")
grep '"HA Device Class": "power_factor"' custom_components/abb_fimer_pvi_vsn_rest/data/vsn-sunspec-point-mapping.json -B 3 -A 3

# Verify diagnostic categories
grep '"Entity Category": "diagnostic"' custom_components/abb_fimer_pvi_vsn_rest/data/vsn-sunspec-point-mapping.json | wc -l
```

## Common Pitfalls

### 1. Silent Fix Failures
**Problem**: You add a fix to `DEVICE_CLASS_FIXES` but it doesn't apply.
**Cause**: The dictionary is keyed by **corrected label names**, but you used the SunSpec name.
**Solution**: Use the label that appears AFTER `apply_label_corrections()` runs.

### 2. Execution Order Issues
**Problem**: Fixes work in isolation but not together.
**Cause**: Corrections applied in wrong order in `create_row_with_model_flags()`.
**Solution**: Ensure `apply_label_corrections()` runs BEFORE `apply_device_class_fixes()`.

### 3. Conflicting Metadata
**Problem**: Point has metadata in multiple dictionaries.
**Cause**: Point was misclassified (e.g., "sn" as apparent power instead of serial number).
**Solution**: Remove from wrong dictionary, add to correct dictionaries.

### 4. Unit Display Issues
**Problem**: Power factor shows "1.0%" instead of expected format.
**Cause**: HA device classes with built-in formatting don't need explicit units.
**Solution**: Use empty string `""` for units, not `None` or `"%"`.

### 5. Forgetting to Regenerate JSON
**Problem**: Changes in Python don't appear in integration.
**Cause**: Forgot to run `convert_to_json.py` after `generate_mapping.py`.
**Solution**: Always run both: `python generate_mapping.py && python convert_to_json.py`

## Version History

- **v2.0.9** (2024-11-03): Comprehensive data quality improvements
  - Fixed label spacing (DC1/DC2 states)
  - Fixed sn/pn misclassification (were in power dictionaries, should be device info)
  - Fixed power factor unit (empty string for proper HA formatting)
  - Added diagnostic categories for device info fields
  - Fixed execution order: apply_label_corrections before apply_device_class_fixes
  - Removed energy prefixes (E#/Ein)
  - Standardized time periods (30 days→month, 7 days→week)
  - Corrected Wh/kWh units
  - Added comprehensive HA metadata (device_class, state_class, units)
  - Created `extract_manual_changes.py` for backporting manual edits
- **v2.0.8** (2024-11-02): Fixed acronym spacing in labels (FRT, MPPT, QAC, SAC, PAC, DI, WH)
- **v2.0.7** (2024-11-02): Massive systematic improvements (58 points)
- **v2.0.6** (2024-11-02): Corrected SunSpec normalized names
- **v2.0.0** (2024-11-02): Self-contained generator with status.json processing
- **v1.0.0** (2024-11-02): Initial comprehensive generator replacing multi-script workflow

## Integration

The generated `vsn-sunspec-point-mapping.json` file is used by the Home Assistant integration to:
- Map VSN REST API responses to standardized entities
- Apply proper units and device classes
- Normalize point names across VSN300 and VSN700

## Contributing

When adding new points or models:
1. Update the appropriate data files
2. Run both generator scripts
3. Verify the output in the Excel file
4. Test with the Home Assistant integration