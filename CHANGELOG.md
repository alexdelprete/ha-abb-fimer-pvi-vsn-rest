# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Removed v2 suffix from mapping files and scripts**
  - Renamed `convert_excel_to_json_v2.py` to `convert_excel_to_json.py`
  - Renamed `vsn-sunspec-point-mapping-v2.xlsx` to `vsn-sunspec-point-mapping.xlsx`
  - Updated all references in scripts and documentation
  - The v2 suffix was a temporary versioning that's no longer needed

## [1.0.0-beta.15] - 2025-01-31

### Fixed

- **Critical: Device Type Detection**: Fixed device_type being discarded by normalizer
  - Normalizer now preserves `device_type` and `timestamp` from VSN API responses
  - Devices correctly identified as "inverter", "datalogger", etc. (instead of "unknown")
  - Entity IDs now follow correct template: `sensor.abb_vsn_rest_inverter_{serial}_{point}`
  - Existing users: entity IDs stable (locked by unique_id), friendly names improve

### Changed

- **User-Friendly Device Names**: Implemented "Manufacturer Type Model (Serial)" format
  - Added `_format_device_name()` helper function
  - Examples: "Power-One Inverter PVI-3.0-TL-OUTD (077909-3G)", "ABB Datalogger VSN300 (111033-3N)"
  - Serial format: First 8 chars with hyphen for readability (e.g., "077909-3G")
  - Manufacturer from SunSpec M1 Common Model (per-device)

- **Modern HA Entity Naming**: Implemented `_attr_suggested_object_id` pattern
  - Decouples entity_id generation from display names
  - Entity IDs: Technical, stable (controlled by suggested_object_id)
  - Friendly names: User-friendly, readable (device name + entity name)
  - Follows modern Home Assistant best practices

### Code Quality

- **Fixed Pre-existing Ruff Error**: RET504 in sensor.py (unnecessary assignment before return)

[Full release notes](docs/releases/v1.0.0-beta.15.md)

## [1.0.0-beta.14] - 2025-01-31

### Changed

- **Mapping Column Cleanup**: Removed duplicate non-HA-prefixed columns
  - Removed: "Units", "State Class", "Device Class" (kept HA-prefixed versions)
  - Cleaner structure emphasizes these are Home Assistant concepts
  - Zero functional impact (duplicates were never used by code)
  - Excel now 26 columns (down from 29)

- **Updated All Code References**: All scripts and integration code now use HA-prefixed columns
  - `scripts/generate_mapping_excel.py`: Updated headers and data assignments
  - `scripts/analyze_and_deduplicate_mapping.py`: Removed duplicate column references
  - `scripts/vsn_client.py`: Changed .get() calls to HA-prefixed names
  - `mapping_loader.py`: Updated data extraction to use HA-prefixed columns
  - Consistent naming: "HA Unit of Measurement", "HA State Class", "HA Device Class"

- **Regenerated JSON Files**: Mapping JSON now only contains HA-prefixed fields
  - Removed duplicate keys from all 210 entries
  - Smaller file size and cleaner structure
  - Both copies updated (docs/ and custom_components/.../data/)

### Documentation

- **Updated MAPPING_FORMAT.md**: Comprehensive documentation refresh
  - Updated field table with HA-prefixed columns
  - Corrected statistics (210 unique mappings)
  - Updated script references (convert_excel_to_json_v2.py)
  - Added model distribution statistics
  - Updated workflow and maintenance sections

[Full release notes](docs/releases/v1.0.0-beta.14.md)

## [1.0.0-beta.13] - 2025-01-29

### ⚠️ BREAKING CHANGES

- **Complete Restructuring**: Major changes to mapping structure, entity naming, and attributes
  - ALL entity IDs will change again (simplified template without model)
  - Mapping file restructured from 277 to 210 unique points
  - Modern `has_entity_name=True` pattern implemented
  - Rich attributes added to all sensors

### Changed - Phase 1: Mapping File Restructuring

- **Deduplicated Mapping**: Reduced from 277 to 210 unique points (24.2% reduction)
  - Removed duplicate rows for same SunSpec points across multiple models
  - Added model flag columns: M1, M103, M160, M203, M802, M64061, VSN300_Only, VSN700_Only, ABB_Proprietary
  - Each point now has `models` array instead of single model field
  - Generated new Excel structure: `docs/vsn-sunspec-point-mapping-v2.xlsx`

- **Improved Descriptions**: Fixed 31 points with meaningless descriptions
  - Priority fixes: Tc Max/Min, E Ct/Dt, house grid sensors
  - Phase-specific descriptions for L1/L2/L3 variants
  - SunSpec-compliant descriptions for standard models

- **Fixed Categories**: Categorized 23 "Unknown" points
  - Energy counters properly categorized
  - House meters identified
  - System monitoring points grouped

- **Updated Mapping Loader**: Handle new JSON structure with models array
  - `PointMapping.models` now list[str] instead of single string
  - Backward compatible model display (comma-separated)

### Changed - Phase 2: Modern Entity Naming Pattern

- **Simplified Template**: Removed model from entity IDs for cleaner naming
  - Old: `sensor.abb_vsn_rest_inverter_0779093g823112_m103_watts`
  - New: `sensor.abb_vsn_rest_inverter_0779093g823112_ac_power`
  - Template: `sensor.abb_vsn_rest_{device_type}_{serial}_{entity_name}`

- **Modern Naming Pattern**: Implemented `has_entity_name=True`
  - Device name: `abb_vsn_rest_{device_type}_{serial}` (e.g., `abb_vsn_rest_inverter_0779093g823112`)
  - Entity name: Friendly display name (e.g., "AC Power", "DC Current #1")
  - Entity ID: Auto-generated by HA from device + entity name
  - Device card display: Just entity name (no redundant device prefix)

- **Unique ID Format**: Simplified without model
  - Format: `abb_vsn_rest_{device_type}_{serial}_{point_name}`
  - Example: `abb_vsn_rest_inverter_0779093g823112_ac_power`

### Added

- **Comprehensive Sensor Attributes**: Rich metadata for debugging and reference
  - Identity: device_id, device_type, point_name
  - Display names: friendly_name, label
  - VSN API names: vsn300_rest_name, vsn700_rest_name
  - SunSpec info: sunspec_model (comma-separated list), sunspec_name, description
  - Compatibility: vsn300_compatible, vsn700_compatible (boolean flags)
  - Category: inverter, meter, battery, energy counter, etc.
  - Timestamp: last_updated

### Removed

- **Obsolete Helper Functions**:
  - `_determine_model_for_entity_id()` - no longer needed
  - `_build_entity_id()` - replaced by inline construction

### Fixed

- **Beta.11 and Beta.12 Issues**: Both previous attempts at entity ID fixes were flawed
  - Beta.11: `self.entity_id` assignment doesn't work in modern HA
  - Beta.12: `_attr_name` set to template created ugly UI names
  - Beta.13: Correct approach using `has_entity_name=True` with device identifier

### Migration Notes

**From Beta.10, Beta.11, or Beta.12:**

1. **Entity IDs will change completely** - update dashboards/automations
2. **Entity friendly names** now clean and meaningful in device cards
3. **Model information** moved to attributes (`sunspec_model`)
4. **Clean up orphaned entities** after upgrade
5. **No backwards compatibility** - clean break for cleaner architecture

**Expected Results:**

```
Entity ID: sensor.abb_vsn_rest_inverter_0779093g823112_ac_power
Friendly Name: "abb_vsn_rest_inverter_0779093g823112 AC Power" (auto by HA)
Device Card Shows: "AC Power" (clean, no prefix)
Unique ID: abb_vsn_rest_inverter_0779093g823112_ac_power

Attributes:
  friendly_name: "AC Power"
  sunspec_model: "M103"
  vsn700_rest_name: "Pgrid"
  vsn300_rest_name: "m103_1_W"
  category: "Inverter"
  vsn300_compatible: true
  vsn700_compatible: true
```

### Technical Details

**Scripts Added:**
- `scripts/analyze_and_deduplicate_mapping.py` - Mapping analysis and deduplication
- `scripts/apply_mapping_fixes.py` - Automated description/category fixes
- `scripts/convert_excel_to_json_v2.py` - Excel→JSON converter for new structure

**Files Modified:**
- `sensor.py` - Complete rewrite of entity naming logic
- `mapping_loader.py` - Handle models array
- `normalizer.py` - Join models for display
- `docs/vsn-sunspec-point-mapping-v2.xlsx` - New mapping structure (210 rows)
- `docs/vsn-sunspec-point-mapping.json` - New JSON format with models arrays

## [1.0.0-beta.12] - 2025-01-29

### ⚠️ WARNING: Known Issue

**This release attempted a different fix but still has issues. Please upgrade to v1.0.0-beta.13.**

### Fixed

- **CRITICAL: Entity ID Generation Fix (Take 2)**: Corrected approach to setting custom entity IDs
  - **Issue:** Beta.11 fix didn't work - entity IDs still showed only point name (e.g., `sensor.dc_current_2`)
  - **Root Cause:** Setting `self.entity_id` directly doesn't work reliably in modern Home Assistant
  - **Correct Fix:** With `has_entity_name=False`, HA slugifies `_attr_name` to create entity_id
  - **Solution:** Set `_attr_name` to the full template string (e.g., `"abb_vsn_rest_inverter_0779093g823112_m160_dc_current_1"`)
  - **Result:** Entity ID now correctly displays as `sensor.abb_vsn_rest_inverter_0779093g823112_m160_dc_current_1`
  - **Friendly Name:** Moved to `extra_state_attributes["friendly_name"]` so users can still see "DC Current #1"

### Changed

- **Entity Display Name**: User-friendly names (e.g., "DC Current #1") now stored in `friendly_name` attribute instead of entity name
  - Entity name now shows full template format (what was intended all along)
  - Access friendly name via `extra_state_attributes["friendly_name"]`

## [1.0.0-beta.11] - 2025-01-29

### ⚠️ WARNING: Known Issue

**This release attempted to fix the entity_id bug but the fix didn't work. Please upgrade to v1.0.0-beta.12.**

### Fixed

- **CRITICAL: Entity ID Generation Bug**: Fixed entity IDs showing only point name instead of full template format
  - **Issue:** Entity IDs displayed as `sensor.dc_current_1` instead of `sensor.abb_vsn_rest_inverter_0779093g823112_m160_dc_current_1`
  - **Root Cause:** Template string was assigned to `_attr_unique_id` (internal registry ID) but not to `entity_id` property
  - **Fix:** Added explicit `self.entity_id = f"sensor.{entity_id}"` assignment in [sensor.py:243](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L243)
  - **Impact:** This hotfix corrects the beta.10 release which had non-functional entity IDs
  - **Note:** If you installed beta.10, all entities will be recreated with correct IDs after upgrading to beta.11

## [1.0.0-beta.10] - 2025-01-29

### ⚠️ WARNING: Known Issue

**This release has a critical bug where entity IDs only show the point name (e.g., `sensor.dc_current_1`) instead of the full template format. Please upgrade to v1.0.0-beta.11 immediately.**

### ⚠️ BREAKING CHANGES

- **Entity ID Template Redesign**: ALL entity IDs have changed to include full device context
  - **Old format:** `sensor.{serial}_{point}` (e.g., `sensor.0779093g823112_watts`)
  - **New format:** `sensor.abb_vsn_rest_{device_type}_{serial}_{model}_{point}`
  - **Examples:**
    - Inverter M103: `sensor.abb_vsn_rest_inverter_0779093g823112_m103_watts`
    - Inverter M160: `sensor.abb_vsn_rest_inverter_0779093g823112_m160_dc_current_1`
    - Datalogger: `sensor.abb_vsn_rest_datalogger_1110333n161421_vsn300_uptime`
  - **Reason:** Prevents entity ID collisions in multi-device systems, provides clear device identification
  - **Impact:** All existing entities will be recreated with new IDs
  - **Action Required:**
    - Update dashboards, automations, and scripts with new entity IDs
    - Entity history will not be preserved (fresh start)
  - **Note:** Entity friendly names (display names) remain unchanged

### Changed

- **Entity ID Generation**: Implemented dynamic entity ID generation with full device context
  - Added helper functions: `_compact_serial_number()`, `_simplify_device_type()`, `_determine_model_for_entity_id()`, `_build_entity_id()`
  - Serial numbers compacted (dashes/colons removed) and lowercased
  - Device types simplified: `inverter_3phases` → `inverter`, etc.
  - Model determination: SunSpec models (m103, m160) or VSN models (vsn300, vsn700) for VSN-only points
  - Template: `abb_vsn_rest_(device)_(sn)_(model)_(point)`

- **Mapping File Point Names**: Simplified point names to exclude device-specific prefixes
  - Old: `abb_m103_watts`, `abb_m160_dca_1`, `abb_vsn_uptime`
  - New: `watts`, `dc_current_1`, `uptime`
  - Point names now combined with device context at runtime

- **Unique ID Format**: Changed to match new entity ID template for consistency
  - Old: `abb_fimer_pvi_vsn_rest_{device_id}_{old_point_name}`
  - New: `abb_vsn_rest_{device_type}_{device_sn}_{model}_{simplified_point_name}`

### Added

- **Excel to JSON Conversion Script**: Created `scripts/convert_excel_to_json.py`
  - Automated conversion from Excel mapping to JSON format
  - Copies JSON to integration data folder automatically

### Technical Details

- **Files Modified:**
  - `sensor.py` - Added 4 helper functions, updated VSNSensor.__init__() with new entity ID logic
  - `generate_mapping_excel.py` - Updated to generate simplified point names
  - `convert_excel_to_json.py` - New conversion utility
  - All mapping files regenerated with simplified names

- **Code Changes:**
  - +150 lines in sensor.py (helper functions + entity ID logic)
  - ~100 lines modified in generate_mapping_excel.py
  - +70 lines in new convert_excel_to_json.py

- **Ruff Checks:** All passed ✓

## [1.0.0-beta.9] - 2025-01-29

### Fixed

- **STARTUP_MESSAGE Version String**: Fixed hardcoded version string in STARTUP_MESSAGE to use VERSION constant
  - Changed from regular string to f-string with {VERSION} interpolation
  - Startup message now dynamically shows current version instead of hardcoded "1.0.0-beta.8"
  - Commit: [c30e929](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/c30e929)

- **STARTUP_MESSAGE Log Pollution**: Fixed startup message logging on every coordinator poll
  - Added conditional check to log only once per Home Assistant session using hass.data
  - Prevents log pollution during normal operation
  - Uses STARTUP_LOGGED_KEY to track if message has been logged
  - Commit: [c30e929](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/c30e929)

- **Unit Conversion for Leakage Current**: Fixed microampere (uA) unit incompatibility with Home Assistant
  - Converted uA → mA for 4 leakage current sensors
  - Added value conversion in normalizer.py (divide by 1000)
  - Updated mapping files with correct mA units
  - Points fixed: m64061_1_ILeakDcAc, m64061_1_ILeakDcDc, Ileak 1, Ileak 2
  - Commit: [85ae392](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/85ae392)

- **Temperature Scale Factor Correction**: Fixed cabinet temperature showing 244°C instead of ~24°C
  - Added temperature correction for sensors with incorrect scale factor
  - Applies additional ÷10 correction when temp > 70°C
  - Points fixed: m103_1_TmpCab, Temp1
  - Commit: [bac10d1](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/bac10d1)

### Changed

- **Improved Entity Display Names**: Enhanced 19 entity names from cryptic abbreviations to descriptive labels
  - Removed unnecessary model prefixes (M 103, M 64061)
  - Examples: "M 103 1 Hz A" → "Frequency Phase A", "M 103 1 PF A" → "Power Factor Phase A"
  - Prefers user-friendly labels over cryptic abbreviations
  - Commit: [188ac76](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/188ac76)

- **Smart Cross-Reference System**: Added intelligent cross-referencing for VSN300-only points
  - VSN300-only points now borrow descriptions from VSN700 equivalents
  - Improved 7 points including Pin1 → "DC Power #1", Pin2 → "DC Power #2"
  - Build lookup table of VSN700 points with good descriptions
  - Priority 0 cross-reference in description system
  - Commit: [209e2b7](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/209e2b7)

- **Comprehensive Display Precision**: Added appropriate decimal precision for all sensor units
  - 0 decimals: W, Wh, kWh, var, VAR, VAh, s, B, Ω
  - 1 decimal: V, A, mA, %, Ah
  - 2 decimals: Hz, °C, °F, MOhm, MΩ, kΩ
  - Examples: 5.234567890 MOhm → 5.23 MΩ, 1234.567 var → 1235 var
  - Commit: [beb41b5](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/beb41b5)

- **Title Case Consistency**: Applied consistent Title Case to all labels and descriptions
  - Fixed lowercase descriptions starting with lowercase letters
  - Improved 11 VSN300-only and system monitoring point descriptions
  - Examples: "flash free space" → "Flash Free Space", "product number" → "Product Number"
  - Added system monitoring label map with proper casing
  - Commit: [3269a74](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/3269a74)

### Technical Details

- **New Registries**: UA_TO_MA_POINTS, TEMP_CORRECTION_POINTS in normalizer.py
- **New Functions**: build_vsn700_lookup() in generate_mapping_excel.py
- **New Features**: Cross-reference Priority 0, Title Case conversion, STARTUP_LOGGED_KEY
- **Files Modified**: 8 files (const.py, __init__.py, mapping_loader.py, normalizer.py, sensor.py, generate_mapping_excel.py, mapping files)
- **Code Metrics**: +210 lines added, -35 lines removed, net +175 lines
- **Ruff Checks**: All passed ✓

**Full Release Notes:** [docs/releases/v1.0.0-beta.9.md](docs/releases/v1.0.0-beta.9.md)

## [1.0.0-beta.8] - 2025-01-28

### Fixed

- **Mapping Loader Field Name Mismatch**: Fixed critical bug where mapping_loader.py was looking for "HA Entity Name" field but new mapping JSON has "HA Name" field
  - Caused 554 "Row missing HA entity name, skipping" warnings on startup
  - No mapping rows were being loaded, breaking the integration
  - Fixed by updating `mapping_loader.py` to use correct field name "HA Name"
  - Also updated expected fields comment to match new 20-column format
  - Commit: [d156ecc](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/d156ecc)

**⚠️ CRITICAL HOTFIX for v1.0.0-beta.7**

v1.0.0-beta.7 had a critical bug that prevented mapping rows from loading. All users on beta.7 should upgrade to beta.8 immediately.

**Full Release Notes:** Same as [v1.0.0-beta.7](docs/releases/v1.0.0-beta.7.md) with this critical fix applied.

## [1.0.0-beta.7] - 2025-01-28

### Added

- **Enhanced Entity Display Names**: Comprehensive mapping system with HA-specific metadata
  - Added 5 new columns to mapping (15→20 total): HA Display Name, HA Unit of Measurement, HA State Class, HA Device Class, Data Source
  - Implemented 4-tier description priority system (SunSpec Description → VSN Feeds → Enhanced Generation → SunSpec Label)
  - Entity names now human-readable instead of cryptic abbreviations
  - Examples: "Hz" → "Line Frequency", "PF" → "Power Factor", "Mn" → "Manufacturer"
  - Data source tracking for debugging and traceability
  - Commit: [77172a1](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/77172a1)

- **Fast Offline Detection**: Socket connectivity check before HTTP requests
  - Created `abb_fimer_vsn_rest_client/utils.py` with `check_socket_connection()` helper
  - Added socket check to 5 HTTP connection points (auth, discovery, client)
  - Fails fast (milliseconds) when device offline instead of waiting for HTTP timeout (10+ seconds)
  - Reduced network overhead during nighttime operation
  - Improved entity unavailability detection speed (100x faster!)
  - Commit: [eb57fd7](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/eb57fd7)

### Fixed

- **M1 Common Model User-Friendly Names**: M1 diagnostic entities now show user-friendly labels instead of generic SunSpec boilerplate
  - "Mn" → "Manufacturer" (was: "Well known value registered with SunSpec for compliance")
  - "Md" → "Model" (was: "Manufacturer specific value (32 chars)")
  - "SN" → "Serial Number" (was: "Manufacturer specific value (32 chars)")
  - Special handling in `get_description_with_priority()` to detect generic descriptions
  - Commit: [2babbe7](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/2babbe7)

- **Unit Detection Issues**: Fixed multiple sensors missing units of measurement
  - Fixed entity IDs and missing units for sensors
  - Added comprehensive unit detection for all VSN points
  - Properly preserve kW/kWh units from VSN feeds (no conversion - HA supports natively)
  - Fixed `HousePInverter` and `PacStandAlone` ABB Proprietary points to show proper units (W)
  - Commits: [e459ade](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/e459ade), [cb84183](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/cb84183), [1b66995](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/1b66995), [3427585](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/3427585)

### Changed

- **Mapping File Format**: Expanded from 15 to 20 columns
  - Added HA-specific columns for better entity metadata
  - Added data source tracking for debugging
  - Updated mapping files: 277 rows with complete metadata
  - Excel file: `docs/vsn-sunspec-point-mapping.xlsx`
  - JSON file: `docs/vsn-sunspec-point-mapping.json` (195.7 KB)

- **Code Refactoring**: Improved code organization and reusability
  - Refactored `config_flow.py` to use `check_socket_connection()` helper (removed 22 lines of duplicate code)
  - Added `ha_display_name` field to `PointMapping` dataclass
  - Updated sensor platform to use `ha_display_name` instead of `label`

### Development

- **Dependency Update**: Updated pip requirement from <25.3,>=21.0 to >=21.0,<25.4
  - Commit: [7a66c45](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/7a66c45)

- **Code Quality**: Added backup files to .gitignore (*.backup, *.bak, *~)
  - Commit: [dfd459e](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/dfd459e)

**Full Release Notes:** [docs/releases/v1.0.0-beta.7.md](docs/releases/v1.0.0-beta.7.md)

## [1.0.0-beta.6] - 2025-01-27

### Fixed

- **AttributeError in Sensor Initialization**: Fixed AttributeError when accessing `_attr_native_unit_of_measurement` in debug log ([sensor.py:182](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L182))
  - Error: `'VSNSensor' object has no attribute '__attr_native_unit_of_measurement'`
  - Root cause: Direct attribute access instead of using `getattr()` with default value
  - Fixed by using `getattr(self, "_attr_native_unit_of_measurement", None)` for consistent handling
  - Integration now loads properly without AttributeError
  - Commit: [51f9286](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/51f9286)

- **Ruff Linting (RET505)**: Removed unnecessary `else` after `return` statement ([generate_mapping_excel.py:917](scripts/generate_mapping_excel.py#L917))
  - Simplified code by removing redundant `else` clause
  - GitHub Actions Ruff check now passes
  - Commit: [20a24fd](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/20a24fd)

**Full Release Notes:** [docs/releases/v1.0.0-beta.6.md](docs/releases/v1.0.0-beta.6.md)

## [1.0.0-beta.5] - 2025-01-27

### Added

- **M1 Common Model Points as Diagnostic Entities**: Added SunSpec Common Model (M1) device identification points as diagnostic entities
  - `C_Mn` (Manufacturer) - Device manufacturer name
  - `C_Md` (Model) - Device model identifier
  - `C_Opt` (Options) - Device options/features
  - `C_SN` (Serial Number) - Device serial number
  - `C_Vr` (Version) - Firmware version
  - `C_DA` (Device Address) - Modbus device address
  - These are static metadata fields, excluded from HA Recorder history by default
  - Visible in advanced entity view for troubleshooting

- **VSN System Monitoring Points as Diagnostic Entities**: Added VSN datalogger system diagnostics as diagnostic entities
  - `fw_ver` - VSN firmware version
  - `uptime` - VSN datalogger uptime (seconds)
  - `sys_load` - System load percentage
  - `free_ram` - Available RAM (KB)
  - `flash_free` - Available flash storage (KB)
  - `store_size` - Data store size (KB)
  - Useful for monitoring VSN datalogger health
  - Excluded from HA Recorder history by default

- **Entity Category Support**: Added `entity_category` field to mapping system
  - New "Entity Category" column in Excel mapping file
  - Supports `diagnostic` category for M1 and system monitoring points
  - Integrated throughout mapping pipeline: Excel → JSON → normalizer → sensor platform
  - Diagnostic entities automatically hidden from standard entity lists

### Changed

- **Mapping File Updates**: Updated VSN-SunSpec mapping files with diagnostic points
  - Excel file: 260 → 277 rows (17 new diagnostic points)
  - JSON file: Added `entity_category` field
  - Updated `PointMapping` dataclass with `entity_category: str | None`
  - Updated normalizer to include `entity_category` in normalized points
  - Updated sensor platform to set `EntityCategory.DIAGNOSTIC` when specified

- **Removed Point Filters**: Removed filters that excluded M1 and system monitoring points
  - Previously skipped in `generate_mapping_excel.py` (lines 1311-1323)
  - Now included with `entity_category="diagnostic"`

- **Improved Sensor Labels and Entity IDs**: Enhanced label and entity ID generation for all sensors ([generate_mapping_excel.py:766-918](scripts/generate_mapping_excel.py#L766))
  - **BREAKING CHANGE**: ALL entity IDs updated for consistency and better readability
  - Labels: Replaced poorly formatted "(M103) PhVphBC" format with human-readable names
  - Entity IDs: Generated from human-readable labels with consistent prefixes
  - **Points WITH Model Number** → `abb_{model}_{label_id}`:
    - M103 phase voltages: `abb_m103_phase_voltage_bc` (was `abb_m103_phvphbc`)
    - M103 frequencies: `abb_m103_frequency_phase_a` (was `abb_m103_hza`)
    - M103 peak power: `abb_m103_peak_power_absolute` (was `abb_m103_powerpeakabs`)
    - M64061 states: `abb_m64061_alarm_state` (was `abb_m64061_alarmstate`)
    - M64061 energy: `abb_m64061_daily_energy` (was `abb_m64061_daywh`)
    - M1 Common Model: `abb_m1_mn` (was `abb_mn`)
  - **Points WITHOUT Model Number** → `abb_vsn_{label_id}`:
    - Energy counters: `abb_vsn_e0_energy_yearly` (was `abb_e0_energy_yearly`)
    - System monitoring: `abb_vsn_flash_free` (was `abb_flash_free`)
    - VSN totals: `abb_vsn_e_tot_charge` (was `abb_e_tot_charge`)
  - Enhanced `generate_label_from_name()` function with VSN300-specific patterns
  - Added `generate_entity_id_from_label()` function with `abb_vsn_` prefix for non-model points
  - Fixed M1 Common Model points missing `m1` prefix (early detection at line 1418-1422)
  - Fixed M64061 points using technical names instead of labels (line 1233, 1289)

- **Integration Title Format**: Changed hub/integration title to use parentheses for consistency with device names ([discovery.py:54](custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/discovery.py#L54))
  - Changed from: `VSN300 - 111033-3N16-1421` (hyphen separator)
  - Changed to: `VSN300 (111033-3N16-1421)` (parentheses)
  - Now matches device naming format: `VSN300 (111033-3N16-1421)`, `PVI-10.0-OUTD (077909-3G82-3112)`
  - Provides consistent naming across integration title, datalogger device, and inverter devices

### Fixed

- **VSN Datalogger Device Model**: Fixed datalogger device showing "Model: unknown" in Home Assistant Device Info ([discovery.py:317-319](custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/discovery.py#L317))
  - Root cause: `device_model` was never set for datalogger devices during discovery
  - VSN700: Only checked `device_data.get("device_model")` which returned None
  - VSN300: Explicitly skipped dataloggers with `and not is_datalogger` condition
  - Fix: Set `device_model = vsn_model` for dataloggers ("VSN300" or "VSN700")
  - Device Info now shows proper model: "VSN300" or "VSN700" instead of "unknown"

- **"No mapping found" Warnings Eliminated**: Fixed 12 unmapped point warnings in logs
  - M1 Common Model points no longer generate warnings
  - VSN system monitoring points no longer generate warnings
  - All previously unmapped diagnostic points now properly mapped

- **String Sensor Attributes**: Fixed string sensors being treated as numeric by explicitly setting all attributes to None ([sensor.py:122-168](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L122))
  - Explicitly set `_attr_device_class = None` for string sensors
  - Explicitly set `_attr_state_class = None` for string sensors
  - Explicitly set `_attr_native_unit_of_measurement = None` for string sensors
  - Refactored to check `is_numeric` once at initialization
  - Numeric sensors: set device_class, state_class, units, precision as available
  - String sensors: ALL numeric attributes explicitly None
  - Prevents HA from inferring numeric type from any attribute
  - Fixes: "Sensor has device class 'None', state class 'None' unit '' ... thus indicating numeric value; however, it has non-numeric value"

## [1.0.0-beta.4] - 2025-10-27

### Fixed

- **Options Flow Crash**: Fixed TypeError when opening integration configuration ([config_flow.py:295](custom_components/abb_fimer_pvi_vsn_rest/config_flow.py#L295))
  - Removed config_entry argument from ABBFimerPVIVSNRestOptionsFlowHandler() instantiation
  - Framework provides config_entry via property, no need to pass as argument
  - Fixes: "TypeError: ABBFimerPVIVSNRestOptionsFlowHandler() takes no arguments"
  - Regression from commit 47c8ead (beta.3) where __init__ was removed but caller wasn't updated
  - Commit: [580b63d](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/580b63d)
- **State Class for String Sensors**: Fixed crash when sensors with string values have state_class set ([sensor.py:132-154](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L132))
  - Only sets state_class if initial value is numeric (int or float)
  - Prevents ValueError: "sensor has state class 'measurement' thus indicating numeric value; however, it has non-numeric value"
  - Affects sensors like `type`, `sn`, `pn`, `wlan_0_essid`, `wlan_0_ipaddr_local`
  - Logs debug message when skipping state_class for non-numeric values
  - Commit: [6d4588d](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/6d4588d)
- **Device Registration Order**: Fixed device hierarchy registration to ensure datalogger device is created before inverter devices ([sensor.py:38-85](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L38))
  - Separates datalogger sensors from inverter sensors during creation
  - Adds datalogger sensors first, then inverter sensors
  - Prevents "via_device referencing non-existing device" warning (HA 2025.12)
  - Ensures proper device hierarchy: inverters → datalogger
  - Commit: [306541a](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/306541a)

**Full Release Notes:** [docs/releases/v1.0.0-beta.4.md](docs/releases/v1.0.0-beta.4.md)

**Note:** v1.0.0-beta.3 contained incorrect version strings (showed "1.0.0-beta.2"). This is corrected in v1.0.0-beta.4.

## [1.0.0-beta.3] - 2025-10-27

### Fixed

- **Blocking I/O Operations**: Converted synchronous file I/O to async using `asyncio.to_thread()` to prevent blocking event loop ([mapping_loader.py:127](custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/mapping_loader.py#L127))
  - Added `async_load()` method to `VSNMappingLoader` for deferred async loading
  - Added `async_load()` method to `VSNDataNormalizer` for deferred async loading
  - File operations now run in thread pool using `Path.read_text()` (HA recommended approach)
  - Follows HA best practices: https://developers.home-assistant.io/docs/asyncio_blocking_operations/#open
  - Commit: [ab9dc38](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/ab9dc38)
- **OptionsFlow Deprecation**: Removed manual `self.config_entry` assignment in `config_flow.py` to fix HA 2025.12 deprecation warning
  - Removed `__init__` method from OptionsFlowHandler (lines 301-303)
  - Framework now provides `self.config_entry` property automatically
  - Commit: [47c8ead](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/47c8ead)
- **Sensor AttributeError**: Fixed `AttributeError` in sensor debug logging when `device_class` or `state_class` not set
  - Uses `getattr()` with default value instead of direct attribute access
  - Safely handles sensors without device_class or state_class
  - Location: [sensor.py:132-133](custom_components/abb_fimer_pvi_vsn_rest/sensor.py#L132)
  - Commit: [47c8ead](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/47c8ead)

**Full Release Notes:** [docs/releases/v1.0.0-beta.3.md](docs/releases/v1.0.0-beta.3.md)

### Added

**Discovery Module:**

- Centralized device discovery system (`abb_fimer_vsn_rest_client/discovery.py`)
- Automatic VSN model detection (VSN300/VSN700)
- Complete device metadata extraction (model, manufacturer, firmware, S/N)
- Smart device ID handling:
  - VSN300 datalogger: Extract S/N from `sn` point
  - VSN700 datalogger: Strip colons from MAC address
  - Inverters: Use serial number directly
- `DiscoveredDevice` and `DiscoveryResult` dataclasses

**Device Info Enhancements:**

- Complete Home Assistant device_info implementation with all standard fields
- Device hierarchy using `via_device` (inverters linked to datalogger)
- Proper device naming: "Model (Serial)" format
- Configuration URL for datalogger web interface
- Firmware version extraction from `C_Vr` (inverters) and `fw_ver` (datalogger)
- Hardware version support (when available)

**Mapping and Normalization:**

- VSN-SunSpec point mapping (259 mappings) in JSON format
- Mapping conversion script (`scripts/generate_mapping_json.py`)
- Data normalization in `vsn_client.py` standalone test script
- Normalization loads mapping from GitHub URL on-demand
- Comprehensive documentation for mapping format and normalization
- `docs/DEV_NOTES.md` - Development progress tracking
- `docs/MAPPING_FORMAT.md` - Mapping workflow documentation

**Documentation:**

- Complete README.md with installation, configuration, troubleshooting
- Comprehensive CLAUDE.md developer guidelines
- Architecture documentation with data flow diagrams
- VSN300 vs VSN700 differences documented

**Internationalization:**

- Italian translation (it.json) - Complete translation of all UI strings
- Multi-language support infrastructure
- Automatic language detection based on Home Assistant settings

### Changed

**Integration Architecture:**

- Config flow now uses discovery module for validation
- Coordinator stores discovery result and discovered devices
- Integration setup performs discovery during initialization
- Sensor platform builds device_info from discovery data

**Device Identification:**

- Config entry unique_id based on logger serial number (stable)
- Device identifiers based on serial number or clean MAC
- Entity unique_ids: `{DOMAIN}_{device_id}_{point_name}`

**Device Info Fields:**

- Fixed `sw_version`: Now shows firmware version (was incorrectly showing VSN model)
- Added `serial_number`: Device S/N or clean MAC
- Added `configuration_url`: Datalogger web interface (datalogger only)
- Added `via_device`: Links devices to datalogger

**Testing:**

- `vsn_client.py` now performs 5 tests (added normalization)
- `vsn_client.py` creates up to 4 output files (added normalized JSON)
- Updated `VSN_CLIENT_README.md` with normalization documentation

### Technical Details

**Discovery Implementation:**

- VSN300: Model from `status["keys"]["device.modelDesc"]["value"]`
- VSN700: Model from `livedata["device_model"]`
- Firmware from SunSpec `C_Vr` point (inverters) or `fw_ver` point (datalogger)
- Manufacturer from SunSpec `C_Mn` point

**Normalization Implementation:**

- Mapping format: Dual Excel/JSON workflow (Excel for editing, JSON for runtime)
- Normalization adds HA entity metadata (units, labels, device_class, state_class)
- Graceful degradation when mapping unavailable (requires internet)

**Code Quality Improvements:**

- Type hints on all functions and dataclasses
- Proper async/await patterns throughout
- Comprehensive error handling
- Ruff linting compliance
- Home Assistant best practices

### Fixed

- Device naming now includes proper model names instead of generic "VSN Device"
- Entity IDs now use device model in name (e.g., `sensor.pvi_10_0_outd_...`)
- Firmware version in device info (was showing VSN model)
- VSN700 datalogger ID: Strips colons from MAC without underscores
- VSN300 datalogger ID: Uses serial number from `sn` point

## [1.0.0-beta.2] - 2025-10-27

### Fixed (Critical Bug Fixes)

**Authentication Failure (VSN300):**

- Fixed critical parameter order bug in `discovery.py` when calling `get_vsn300_digest_header()`
- Parameters were passed as `(session, base_url, uri, username, password)` instead of correct order
- This caused URI to be used as username, making requests to wrong endpoint (root `/` instead of `/v1/status`)
- Error manifested as "Expected 401 challenge, got 200"
- Fixed in `_fetch_status()` and `_fetch_livedata()` functions
- **Impact:** VSN300 authentication was completely broken in v1.0.0-beta.1

**Mapping File Not Found:**

- Fixed "Mapping file not found: /config/docs/vsn-sunspec-point-mapping.json" error
- Root cause: Mapping file was in repository `docs/` directory, not bundled with integration
- **Solution:** Bundled mapping file in `custom_components/abb_fimer_pvi_vsn_rest/data/`
- Updated `mapping_loader.py` to look in bundled location
- **Impact:** Integration couldn't load at all in v1.0.0-beta.1

### Added

**GitHub Fallback for Mapping File:**

- Added automatic fallback to fetch mapping file from GitHub if local file not found
- Fetches from: `https://raw.githubusercontent.com/.../master/docs/vsn-sunspec-point-mapping.json`
- Caches downloaded file locally for future use
- Provides robustness against missing or corrupted bundled file

**CI/CD Improvements:**

- Fixed release workflow to dynamically discover integration directory name
- No longer hardcoded to legacy repository name
- Added `scripts/test_output_*.json` to `.gitignore`

### Changed

**Documentation:**

- Created comprehensive release notes in `docs/releases/v1.0.0-beta.1.md`
- Updated `docs/releases/README.md` for VSN REST integration

### Migration Notes

**⚠️ CRITICAL UPDATE REQUIRED:**

Users running v1.0.0-beta.1 MUST update to v1.0.0-beta.2. The previous version had critical bugs that prevented:

1. VSN300 authentication from working at all
2. Integration from loading due to missing mapping file

After updating:

1. Restart Home Assistant to load the new code
2. Reconfigure the integration if needed
3. Verify devices are discovered and data is being collected

## [1.0.0-beta.1] - 2025-10-26

### Added (v1.0.0-beta.1)

- Initial beta release
- VSN300/VSN700 REST API client implementation
- HTTP Digest authentication for VSN300 (X-Digest scheme)
- HTTP Basic authentication for VSN700
- Automatic device detection
- Support for `/v1/status`, `/v1/livedata`, and `/v1/feeds` endpoints
- Standalone `vsn_client.py` test script
- Comprehensive test coverage on real VSN300 device
- Config flow with setup, reconfigure, and options
- Coordinator for periodic data polling
- Sensor platform with dynamic entity creation
- Data normalizer with VSN→SunSpec mapping

### Technical (v1.0.0-beta.1)

- REST client with authentication handling
- Exception hierarchy (VSNConnectionError, VSNAuthenticationError, VSNClientError)
- Async/await throughout
- Type hints on all components
- Home Assistant integration framework

---

## Release Notes

### v1.0.0-beta.2 (Unreleased)

**Major Features:**

- Complete device discovery with metadata extraction
- Full Home Assistant device_info implementation
- Proper device hierarchy (via_device)
- Smart device identification for VSN300/VSN700

**Improvements:**

- Better device naming in HA UI
- Firmware version tracking
- Configuration URLs for datalogger
- Centralized discovery logic

**For Users:**

- Devices now show proper names: "PVI-10.0-OUTD (077909-3G82-3112)"
- Device hierarchy shows inverters connected through datalogger
- Firmware versions visible in device info
- Click datalogger device to access web interface

**For Developers:**

- New discovery module for device detection
- Complete device_info implementation example
- Comprehensive documentation updates
- VSN300/VSN700 differences documented

### v1.0.0-beta.1

**Initial Release:**

- Working VSN300/VSN700 REST API integration
- Automatic authentication and device detection
- Basic sensor platform with entity creation
- Standalone test script for debugging

---

[Unreleased]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.10...HEAD
[1.0.0-beta.10]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.9...v1.0.0-beta.10
[1.0.0-beta.9]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.8...v1.0.0-beta.9
[1.0.0-beta.8]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.7...v1.0.0-beta.8
[1.0.0-beta.7]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.6...v1.0.0-beta.7
[1.0.0-beta.6]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.5...v1.0.0-beta.6
[1.0.0-beta.5]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.4...v1.0.0-beta.5
[1.0.0-beta.4]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.3...v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.2...v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.1...v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases/tag/v1.0.0-beta.1
