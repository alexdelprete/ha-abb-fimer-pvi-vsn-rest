# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.2] - 2025-11-15

### ✨ Features

**REACT2 Inverter Support**:

- Added support for REACT2 inverters (e.g., REACT2-5.0-TL)
- REACT2 devices use VSN700 dataloggers with preemptive Basic authentication
- No configuration changes needed - automatic detection
- Commit: [ae4d617](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/ae4d617)

**Authentication Debug Logging**:

- Added comprehensive debug logging throughout authentication flow
- VSN detection, VSN300 digest auth, and client request logging
- Helps users diagnose connection and authentication issues
- Enable with: `logger: custom_components.abb_fimer_pvi_vsn_rest: debug`
- Commit: [e2bd91c](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/e2bd91c)

### 🔧 Improvements

**Simplified Authentication Detection**:

- Refactored detection logic: check for VSN300 (x-digest), else try preemptive Basic auth
- VSN700 and REACT2 now use unified code path
- Removed 21 lines of redundant code while maintaining functionality
- Same request count, simpler logic, better maintainability
- Commit: [dd6661d](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/dd6661d)

**Translation Quality**:

- Fixed translation quality issues in all 9 non-English languages
- 2,259 sensor translations (251 × 9 languages) now complete and professional
- No more mixed English/native language text
- All technical terms properly translated
- Commit: [e3001df](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/e3001df)

### 📚 Documentation

**Updated README**:

- Added detailed "VSN Authentication" section
- Explained detection process step-by-step
- VSN300 digest authentication details
- VSN700 preemptive Basic authentication details

**Full release notes**: [v1.1.2](docs/releases/v1.1.2.md)

---

## [1.1.1] - 2025-11-15

### 🐛 Bug Fixes

**Fixed GitHub Actions CI Failure**:

- Ruff was checking vendor directory containing third-party code
- Added `extend-exclude` configuration to .ruff.toml
- Excluded: vendor/, .vscode/, .devcontainer/, .github/
- Applied automatic formatting fixes to 3 files
- Commit: [5d0e292](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/5d0e292)

**Fixed Home Assistant Runtime Error**:

- AttributeError: 'VSNSensor' object has no attribute '_attr_name'
- Removed references to undefined `_attr_name` in debug logs
- Replaced with `self._point_name` and added translation_key to debug output
- With `has_entity_name=True`, HA uses `_attr_translation_key`, not `_attr_name`
- Commit: [dafba7d](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/commit/dafba7d)

### 📝 Version Corrections

- Updated manifest.json version to 1.1.1 (was incorrectly 1.0.0 in v1.1.0)
- Updated const.py VERSION to 1.1.1 (was incorrectly 1.0.0 in v1.1.0)

**Full release notes**: [v1.1.1](docs/releases/v1.1.1.md)

---

## [1.1.0] - 2025-11-15

### 🌍 Multi-Language Support

**New Language Files (8 added)**:

- German (de), Spanish (es), Estonian (et), Finnish (fi)
- French (fr), Norwegian Bokmål (nb), Portuguese (pt), Swedish (sv)

**Translation Coverage**:

- 251 sensors per language with professional electrical/solar terminology
- Consistent naming patterns across all languages
- Complete file structure (config, options, entities)

**Updated Translations**:

- English (en.json): Updated with 251 sensor translations
- Italian (it.json): Updated with 251 sensor translations

### 🏗️ Architecture Improvements

**Mapping File Relocation**:

- Moved from: `data/vsn-sunspec-point-mapping.json`
- Moved to: `abb_fimer_vsn_rest_client/data/vsn-sunspec-point-mapping.json`
- Better organization with mapping file co-located with client library

**Translation System**:

- sensor.py: Added `_attr_translation_key = self._point_name` for native HA translation
- mapping_loader.py: Updated path to new location in client library

### 📚 Documentation

**New Documentation**:

- docs/TRANSLATION_REPORT.md: Comprehensive report on translation generation

**Markdown Linting Fixes**:

- Fixed MD032 violations (blank lines around lists) in 30+ markdown files
- All release notes, README, CHANGELOG, and documentation files

**Full release notes**: [v1.1.0](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases/tag/v1.1.0)

**Note**: v1.1.0 was released with incorrect version strings in manifest.json and const.py (still showing "1.0.0"). This has been corrected in v1.1.1.

---

## [1.0.0] - 2025-11-13

### 🎉 First Stable Release

This is the **first official stable release** of the ABB/FIMER PVI VSN REST integration!

After extensive testing through **29 beta releases**, the integration is now **production-ready** with:

- ✅ **Comprehensive Device Support**: VSN300, VSN700, single-phase and three-phase inverters, meters, batteries
- ✅ **258 Mapped Data Points**: Complete coverage of all VSN API endpoints with SunSpec normalization
- ✅ **Aurora Protocol Integration**: Accurate timestamp handling and state translations for 195 operational states
- ✅ **Stable Entity IDs**: Final entity naming pattern established (no more breaking changes)
- ✅ **Rich Metadata**: 14+ attributes per sensor for debugging and automation
- ✅ **Multi-Language Support**: English and Italian translations
- ✅ **Production-Ready**: All critical bugs resolved through beta testing

### Documentation

- **README**: Updated with donation badge and current entity naming scheme
- **Entity Naming**: Now documents the modern `has_entity_name=True` pattern with friendly device names
- **Examples**: Comprehensive examples for device names, entity IDs, and friendly names

### Technical Changes

- manifest.json: Version bump to 1.0.0 (from 1.0.0-beta.29)
- const.py: Version bump to 1.0.0
- README.md: Add "Buy Me a Coffee" donation badge
- README.md: Update Entity Naming section to reflect current implementation

**Full release notes**: [v1.0.0](docs/releases/v1.0.0.md)

### What's Next

This stable release marks the completion of the beta testing phase. Future releases will follow semantic versioning:

- **Patch releases** (1.0.x): Bug fixes and minor improvements
- **Minor releases** (1.x.0): New features and enhancements
- **Major releases** (x.0.0): Breaking changes (if needed)

Thank you to all beta testers who helped make this release possible! 🙏

---

## [1.0.0-beta.29] - 2025-11-13

### Fixed

- **device_type Still "unknown"**: Fixed beta.28 regression - datalogger entities still showing "unknown" device_type
  - Root cause: Discovery.py identified datalogger from livedata but didn't set `device_type = "datalogger"`
  - Line 355 gets device_type from livedata: `device_type = device_data.get("device_type", "unknown")`
  - Lines 359-361 check `if is_datalogger:` but only set device_model, not device_type
  - Beta.28 injection logic tried to inject but was injecting "unknown" from discovered_device
  - Solution: Add `device_type = "datalogger"` assignment in discovery.py line 362
  - Result: Datalogger entities now properly show `device_type: "datalogger"` in attributes
  - Location: discovery.py line 362

- **sys_time Relative Time Display**: Fixed beta.28 regression - sys_time showing "32 seconds ago" instead of actual date
  - Root cause: Home Assistant's timestamp device_class displays relative time BY DESIGN
  - Beta.28 added `device_class: "timestamp"` to enable conversion, but this triggers relative time formatting
  - Cannot have timestamp device_class AND formatted date display - it's a catch-22
  - Solution: Remove device_class, modify conversion to check `point_name == "sys_time"` instead
  - Return formatted string "2025-11-13 10:15:32" instead of datetime object
  - Result: Shows actual date/time string, not relative time
  - Locations: sensor.py lines 415-433; vsn-sunspec-point-mapping.json line 544

### Technical Changes

- abb_fimer_vsn_rest_client/discovery.py: Add device_type assignment for datalogger (line 362)
- sensor.py: Modified timestamp conversion to check point_name instead of device_class (lines 415-433)
- sensor.py: Return formatted string instead of datetime object (line 425)
- data/vsn-sunspec-point-mapping.json: Remove device_class timestamp (line 544)
- manifest.json: Version bump to 1.0.0-beta.29
- const.py: Version bump to 1.0.0-beta.29

**Full release notes**: [v1.0.0-beta.29](docs/releases/v1.0.0-beta.29.md)

## [1.0.0-beta.28] - 2025-11-13

### Fixed

- **sys_time Timestamp Display**: Fixed sys_time showing raw number instead of formatted date/time
  - Root cause: Mapping file had empty `device_class` field
  - Timestamp conversion code requires `device_class: "timestamp"` to execute
  - Solution: Set `"HA Device Class": "timestamp"` in mapping file
  - Result: Now displays as formatted date/time with proper timezone
  - Location: vsn-sunspec-point-mapping.json line 544

- **Datalogger device_type Still Unknown**: Fixed datalogger entities still showing "unknown" device_type after beta.27
  - Root cause: Synthetic datalogger device created in discovery but not propagated to normalized data
  - Discovery creates device with `device_type="datalogger"` but normalizer reads from livedata (which doesn't have device_type)
  - Solution: Inject device_type from discovered_devices into livedata before normalization
  - Modified client to accept and store discovered_devices list
  - In `get_normalized_data()`, inject device_type into raw data before normalization
  - Result: Datalogger entities now show `device_type: "datalogger"` in attributes
  - Locations: client.py lines 35, 56, 185-200; __init__.py line 116

### Technical Changes

- data/vsn-sunspec-point-mapping.json: Set device_class to "timestamp" for sys_time (line 544)
- abb_fimer_vsn_rest_client/client.py: Added discovered_devices parameter to __init__ (line 35)
- abb_fimer_vsn_rest_client/client.py: Store discovered_devices list (line 56)
- abb_fimer_vsn_rest_client/client.py: Inject device_type from discovery before normalization (lines 185-200)
- __init__.py: Pass discovered_devices to client initialization (line 116)
- manifest.json: Version bump to 1.0.0-beta.28
- const.py: Version bump to 1.0.0-beta.28

**Full release notes**: [v1.0.0-beta.28](docs/releases/v1.0.0-beta.28.md)

## [1.0.0-beta.27] - 2025-11-13

### Fixed

- **system_load Sensor Precision**: Fixed sensor showing too many decimals (e.g., 0.05419921875)
  - Root cause: `suggested_display_precision = 2` not working for sensors without units
  - Solution: Round value to 2 decimals in `native_value` property before returning
  - Result: Now displays `0.05` instead of `0.05419921875`
  - Location: sensor.py lines 446-448

- **isolation_ohm1 Sensor Icon**: Added omega icon for insulation resistance sensor
  - Changed from empty icon to `mdi:omega` (Ω symbol)
  - Appropriate icon for resistance measurement in megaohms (MΩ)
  - Location: vsn-sunspec-point-mapping.json line 1328

- **model Sensor Value Cleanup**: Strip leading/trailing dashes from model identifier
  - Issue: Model values showing with dashes like `-3G82-`
  - Solution: Added `C_Md` to `STRING_STRIP_POINTS` registry in normalizer
  - Result: Now displays `3G82` instead of `-3G82-`
  - Location: normalizer.py lines 38-41

- **serial_number Description**: Changed from "Device serial number" to "Serial number"
  - Cleaner, more concise description
  - Location: vsn-sunspec-point-mapping.json lines 217-218

- **Datalogger device_type**: Fixed datalogger showing "unknown" device type in entity attributes
  - Root cause: Datalogger doesn't appear in livedata.json (only in feeds.json)
  - Solution: Create synthetic datalogger device from status.json data during discovery
  - Result: Datalogger now properly identified with device_type "datalogger"
  - Location: discovery.py lines 291-322

- **VSN REST Name Attributes**: Changed "unknown" to "N/A" for non-applicable VSN REST API names
  - Issue: VSN300 devices showing "Vsn700 rest name: unknown" (and vice versa)
  - Solution: Use "N/A" for None/missing VSN REST names instead of empty string → "unknown"
  - Result: Cleaner attribute display (e.g., VSN300 shows "N/A" for vsn700_rest_name)
  - Location: sensor.py lines 482-483

- **VSN Model Case Consistency**: Changed VSN constants to uppercase
  - Changed `VSN_MODEL_300 = "vsn300"` to `VSN_MODEL_300 = "VSN300"`
  - Changed `VSN_MODEL_700 = "vsn700"` to `VSN_MODEL_700 = "VSN700"`
  - Consistent uppercase usage throughout codebase
  - Location: const.py lines 19-20

### Technical Changes

- sensor.py: Added value rounding for system_load (line 446-448)
- sensor.py: Changed VSN REST name attributes to use "N/A" (lines 482-483)
- data/vsn-sunspec-point-mapping.json: Set icon for isolation_ohm1 (line 1328)
- data/vsn-sunspec-point-mapping.json: Changed serial_number description (lines 217-218)
- abb_fimer_vsn_rest_client/normalizer.py: Added C_Md to STRING_STRIP_POINTS (line 40)
- abb_fimer_vsn_rest_client/discovery.py: Create synthetic datalogger device (lines 291-322)
- const.py: VSN constants uppercase (lines 19-20)
- manifest.json: Version bump to 1.0.0-beta.27
- const.py: Version bump to 1.0.0-beta.27

**Full release notes**: [v1.0.0-beta.27](docs/releases/v1.0.0-beta.27.md)

## [1.0.0-beta.26] - 2025-11-12

### Fixed

- **system_uptime Sensor ValueError**: Fixed sensor failing to load due to value type mismatch
  - Root cause: Sensor was configured with `device_class: duration`, `state_class: total_increasing`, and `unit: s` (numeric sensor)
  - But code was returning formatted string "10 hours 9 minutes" instead of numeric seconds
  - Home Assistant rejected the sensor: "ValueError: sensor has numeric indicators but non-numeric value"
  - **Solution**: Return raw numeric value (seconds) as `native_value`, add `formatted` attribute for beautiful display
  - Native value: `36600` (numeric seconds) → works with statistics and history
  - Formatted attribute: `"10 hours 9 minutes"` → available for Lovelace UI via `attribute: formatted`
  - Users can now display uptime beautifully in dashboards while preserving statistics

- **Device Names and Entity Friendly Names**: Switched from technical to friendly device names for beautiful UI
  - Beta.25 had ugly technical device names: `abb_fimer_pvi_vsn_rest_datalogger_1110333n161421`
  - Beta.25 had ugly entity friendly names: `abb_fimer_pvi_vsn_rest_datalogger_1110333n161421 Firmware Version`
  - Now uses friendly format: `ABB Datalogger VSN300 (111033-3N16-1421)`
  - Entity friendly names now beautiful: `ABB Datalogger VSN300 (111033-3N16-1421) Firmware Version`
  - Follows Home Assistant best practices for modern integrations

### Technical Changes

- sensor.py: Removed uptime formatting from `native_value` property (lines 446-449)
- sensor.py: Added `formatted` attribute to `extra_state_attributes` for system_uptime (lines 511-515)
- sensor.py: Changed device name generation to use `_format_device_name()` helper (line 552-557)
- sensor.py: Device names now friendly format instead of technical

### Breaking Changes

⚠️ **IMPORTANT**: This release contains breaking changes requiring manual migration:

1. **Entity IDs will change** (friendly device name is slugified by Home Assistant):
   - FROM: `sensor.abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_firmware_version`
   - TO: `sensor.abb_datalogger_vsn300_111033_3n16_1421_firmware_version`
   - FROM: `sensor.abb_fimer_pvi_vsn_rest_inverter_0779093g823112_power_peak_lifetime`
   - TO: `sensor.power_one_inverter_pvi_10_0_outd_077909_3g82_3112_power_peak_lifetime`

2. **Device names and friendly names now beautiful** in UI

3. **Migration**: Remove integration via UI (auto-deletes entities) → Use "Recreate Entity IDs" feature on device page OR reinstall

4. Update all dashboards and automations with new entity IDs

**Why the change from Beta.25**: Technical device names produced ugly UI everywhere. The new entity IDs are still technical (contain manufacturer, model, serial) but slightly friendlier format. The beautiful device names make the integration much more pleasant to use.

**This is the FINAL entity ID format.** We're now following HA best practices with `has_entity_name=True` + friendly device names.

**Full release notes**: [v1.0.0-beta.26](docs/releases/v1.0.0-beta.26.md)

## [1.0.0-beta.25] - 2025-11-12

### Fixed

- **Entity ID Generation - THE REAL FIX**: Properly fixed entity ID generation by using `has_entity_name=True` with technical device names
  - Beta.24's fix was incorrect: `suggested_object_id` is ONLY used when `has_entity_name=True`
  - When `has_entity_name=False`, Home Assistant completely ignores `suggested_object_id`
  - Implemented correct approach: `has_entity_name=True` + technical device names + simplified `suggested_object_id`
  - Entity IDs now: `sensor.abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_wlan0_essid` ✅
  - Entity names on device page: "WiFi SSID" ✅ (clean and friendly)
  - Device names: Technical format but acceptable trade-off for predictable entity IDs

### Technical Changes

- Set `has_entity_name = True` (required for `suggested_object_id` to work)
- Changed `suggested_object_id` to just point name (e.g., `"wlan0_essid"`)
- Use technical device names: `abb_fimer_pvi_vsn_rest_datalogger_1110333n161421`
- Home Assistant combines device_name + suggested_object_id for predictable entity IDs

### Breaking Changes

⚠️ **IMPORTANT**: This release contains breaking changes requiring manual migration:

1. All entity IDs will change (again - final format this time)
2. **Migration**: Remove integration via UI (auto-deletes entities) → Reinstall
3. Update all dashboards and automations with new entity IDs

**Why the change from Beta.24**: After deeper investigation, we discovered `has_entity_name=False` causes HA to ignore `suggested_object_id` entirely. This is the correct implementation based on HA core source code.

**This is the final entity ID format.** No more changes after this.

**Full release notes**: [v1.0.0-beta.25](docs/releases/v1.0.0-beta.25.md)

## [1.0.0-beta.24] - 2025-11-12

### Fixed

- **Entity ID Generation**: Fixed critical bug where `has_entity_name` was incorrectly set to `True` (introduced in beta.13)
  - Entity IDs were not following the intended format due to Home Assistant ignoring `suggested_object_id` when `has_entity_name=True`
  - Users were seeing: `sensor.abb_fimer_datalogger_vsn300_111033_3n16_1421_system_load_average`
  - Now correctly generates: `sensor.abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_system_load_average`
  - Reverted `has_entity_name` from `True` back to `False` (beta.12 behavior)
  - Corrected misleading comments about how `has_entity_name=True` interacts with `suggested_object_id`

### Breaking Changes

⚠️ **IMPORTANT**: This release contains breaking changes requiring manual entity registry cleanup:

1. All entity IDs will change to correct format with compacted serial numbers
2. Entity history will not be transferred to new entity IDs
3. **Manual cleanup required**: Delete integration → Clean `.storage/core.entity_registry` → Re-add integration
4. Update all dashboards and automations with new entity IDs

**Apology**: We apologize for this back-and-forth with entity ID changes. The bug was introduced in beta.13 and this fix restores correct behavior from beta.12.

**Full release notes**: [v1.0.0-beta.24](docs/releases/v1.0.0-beta.24.md)

## [1.0.0-beta.23] - 2025-11-12

### Developer Tools

- **Linting Compliance**: Fixed all 22 ruff linting errors in VSN mapping generator scripts
  - Package structure (INP001): Added `__init__.py` to scripts package
  - Performance issues (9 errors): PERF403, PERF102, B007, RUF005
  - Code style (5 errors): RET504, RET505
  - Data correctness (F601): Removed duplicate dictionary key
  - Dead code (F841): Removed unused variable
  - Code complexity (C901): Refactored complex function

- **Code Refactoring**: Reduced complexity of `generate_mapping_excel_complete()` function
  - Function length: 537 lines → 74 lines (86% reduction)
  - Cyclomatic complexity: 71 → <25 (below threshold)
  - Created 10 focused helper functions with single responsibilities
  - Improved testability, maintainability, and readability

- **Mapping Files**: Regenerated all VSN-SunSpec point mapping files (258 unique points)
  - Verified refactored code produces correct output
  - Added missing `docs/vsn-sunspec-point-mapping.json`
  - Updated all copies in docs/, output/, and integration data folders

### Technical

- All scripts now pass 100% of ruff linting checks
- Improved code quality without changing integration functionality
- No user-facing changes - developer tooling release only

**Full release notes**: [v1.0.0-beta.23](docs/releases/v1.0.0-beta.23.md)

## [1.0.0-beta.22] - 2025-11-11

### Changed

- **Entity ID Format**: Added domain prefix to all entity IDs for namespace isolation
  - Format changed from `sensor.{device_type}_{serial}_{point}` to `sensor.abb_fimer_pvi_vsn_rest_{device_type}_{serial}_{point}`
  - Prevents conflicts with other integrations and provides clear ownership indication
  - Domain dynamically sourced from manifest.json instead of hardcoded value

- **Unique ID Format**: Aligned unique IDs with entity ID format
  - Changed from `abb_vsn_rest_{device_type}_{serial}_{point}` to `abb_fimer_pvi_vsn_rest_{device_type}_{serial}_{point}`
  - Ensures consistency between unique_id and entity_id formats

- **Display Name Standardization**: Standardized 187 entity display names to TYPE-first pattern `[Type] [AC/DC] - [Details] - [Time Period]`
  - Energy entities (75): "Inverter AC energy produced - Lifetime" → "Energy AC - Produced Lifetime"
  - Power entities (24): "AC Power" → "Power AC", "House Power A" → "Power AC - House Phase A"
  - Voltage entities (27): "AC Voltage A-N" → "Voltage AC - Phase A-N"
  - Current entities (19): "AC Current" → "Current AC"
  - Temperature entities (9): "Cabinet Temperature" → "Temperature - Cabinet"
  - Frequency entities (6): "Grid Frequency" → "Frequency AC - Grid"
  - Reactive Power entities (5): "Reactive power at grid connection point" → "Reactive Power - Grid Connection"
  - Other entities (22): Various measurement types
  - Enables superior grouping in Home Assistant's entity lists and UI

### Technical

- Updated sensor.py to use DOMAIN constant for entity_id and unique_id generation
- Added DISPLAY_NAME_STANDARDIZATION dictionary (187 entries) in generate_mapping.py
- Updated apply_display_name_corrections() to apply both corrections and standardization
- Regenerated all mapping files (Excel and JSON) with standardized display names

### Breaking Changes

⚠️ **IMPORTANT**: This release contains breaking changes requiring manual entity registry cleanup:

1. All entity IDs will change due to domain prefix addition
2. All unique IDs will change from `abb_vsn_rest` to `abb_fimer_pvi_vsn_rest` prefix
3. Entity history will not be transferred to new entity IDs
4. Manual cleanup required: Delete integration → Clean `.storage/core.entity_registry` → Re-add integration

**Full release notes**: [v1.0.0-beta.22](docs/releases/v1.0.0-beta.22.md)

## [1.0.0-beta.21] - 2025-11-10

### Fixed

- **Diagnostic Entity Icons**: Fixed icons not displaying for diagnostic and VAh entities
  - Implemented complete icon support across data flow (mapping_loader.py, normalizer.py, sensor.py)
  - 51 diagnostic entities now display information icon (ℹ️ `mdi:information-box-outline`)
  - 3 VAh entities now display lightning bolt icon (⚡ `mdi:lightning-bolt`)

- **State Entity Mappings**: Fixed state entities showing numeric codes instead of descriptive text
  - Updated STATE_ENTITY_MAPPINGS dictionary keys to match actual SunSpec normalized names
  - `global_st` now shows "Run" instead of 6
  - `dc_st1` and `dc_st2` now show "MPPT" instead of 2
  - `inverter_st` now shows "Run" instead of 2

- **System Time Display**: Changed `sys_time` entity to show formatted date/time instead of relative time
  - Removed timestamp device_class to display "2025-11-05 12:04:30" instead of "1 minute ago"
  - Timestamp conversion (Aurora epoch → datetime) continues to work correctly

- **Unit Validation Errors**: Fixed Home Assistant validation error for `wlan0_link_quality`
  - Removed signal_strength device_class (percentage is not compatible with signal_strength)
  - Entity now correctly displays as percentage without inappropriate device_class

- **M1 Entity Names**: Removed redundant "Device" prefix from diagnostic entity display names
  - "Device manufacturer name" → "Manufacturer name"
  - "Device model identifier" → "Model identifier"
  - "Device firmware version" → "Firmware version"
  - "Device configuration options" → "Configuration options"

### Technical

- Added `icon` field to PointMapping dataclass with complete data flow support
- Fixed STATE_ENTITY_MAPPINGS keys: "GlobState"→"GlobalSt", "DC1State"→"DcSt1", "DC2State"→"DcSt2", "InvState"→"InverterSt"
- Updated DESCRIPTION_IMPROVEMENTS in generate_mapping.py for cleaner M1 entity names
- Regenerated mapping files with all fixes applied

**Full release notes**: [v1.0.0-beta.21](docs/releases/v1.0.0-beta.21.md)

## [1.0.0-beta.20] - 2025-11-05

### Fixed

- **Device Name Serial Number**: Fixed device names to show full serial number (e.g., `111033-3N16-1421`) instead of truncated 8-character version (e.g., `111033-3N`)
  - Updated `_format_device_name()` to use full original serial number with dashes preserved
  - Affects both hub device name and all device names in Home Assistant UI
  - Better device identification and consistency

### Documentation

- **Aurora Protocol References**: Added comprehensive Aurora Communication Protocol v4.2 documentation references
  - Added online PDF reference to AURORA_EPOCH_OFFSET constant comments
  - Added online PDF reference to State Mappings comments
  - Added local copy of Aurora protocol PDF to `docs/AuroraCommunicationProtocol_4_2.pdf`
  - Updated CLAUDE.md with protocol documentation references

### Technical

- Updated `_format_device_name()` function in sensor.py (parameter renamed: `device_sn_compact` → `device_sn_original`)
- Enhanced const.py with Aurora protocol documentation links

**Full release notes**: [v1.0.0-beta.20](docs/releases/v1.0.0-beta.20.md)

## [1.0.0-beta.19] - 2025-11-04

### Added

- **Aurora Protocol Integration**:
  - Fixed SysTime timestamp conversion using Aurora epoch (Jan 1, 2000 instead of Unix epoch)
  - Added `AURORA_EPOCH_OFFSET` constant (946684800 seconds) for correct timestamp handling
  - Implemented state mapping for 6 status entities with 195 total state descriptions:
    - GlobState: 42 operational states (e.g., "Run", "Wait Sun / Grid", "Ground Fault")
    - DC1State/DC2State: 20 DC converter states each (e.g., "MPPT", "Ramp Start", "DcDc OFF")
    - InvState: 38 inverter states (e.g., "Run", "Stand By", "Checking Grid")
    - AlarmState/AlarmSt: 65 alarm codes (e.g., "No Alarm", "Ground Fault", "Grid Fail")
  - Status entities now display human-readable text instead of raw integer codes
  - Raw state codes preserved in `raw_state_code` entity attribute for debugging
  - Unknown codes display as "Unknown (code)" for visibility

- **Icon Support** (27 columns total in mapping):
  - Energy icon (`mdi:lightning-bolt`) for 3 VAh apparent energy entities (E2_runtime, E2_7D, E2_30D)
  - Diagnostic icon (`mdi:information-box-outline`) for all 51 diagnostic entities

- **Device Class Improvements**:
  - Added device_class for 59 measurement entities (182 → 123 without device_class)
  - Fixed 39 energy entities (Wh) with proper energy device_class and state_class
  - Fixed 10 power entities (W) with correct power device_class
  - Added data_size device_class for bytes entities
  - Added duration device_class for uptime measurements
  - Added signal_strength device_class for wlan0_link_quality

### Fixed

- **Timestamp Display**: SysTime now shows correct dates (2023) instead of incorrect dates (1993)
- **Isolation Resistance Unit**: Changed from Ω to MΩ (verified from feeds data)
- **Battery Metrics**: Fixed capitalization (Soc, Soh)
- **House Metrics**: Fixed HousePgrid_L1/L2/L3, HouseIgrid_L1/L2/L3

### Technical

- Added Aurora protocol state mappings to const.py (GLOBAL_STATE_MAP, DCDC_STATE_MAP, INVERTER_STATE_MAP, ALARM_STATE_MAP)
- Added STATE_ENTITY_MAPPINGS configuration dictionary
- Implemented state translation logic in sensor.py native_value property
- Enhanced mapping generator with icon support and diagnostic entity auto-assignment
- Updated mapping to 258 unique data points

**Full Release Notes**: [v1.0.0-beta.19](docs/releases/v1.0.0-beta.19.md)

**Credits**: Special thanks to [xreef/ABB_Aurora_Solar_Inverter_Library](https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library) for Aurora protocol documentation.

## [1.0.0-beta.15] - 2025-11-03

### Fixed

- **Temperature Units**: Changed from "degC" to "°C" for all temperature sensors
- **Temperature Precision**: Changed from 2 decimals to 1 decimal for better readability
- **Timestamp Sensor**: Fixed sys_time sensor to convert Unix timestamp to datetime with HA timezone
  - Now uses `ZoneInfo(hass.config.time_zone)` instead of returning raw integer
  - Fixes `AttributeError: 'int' object has no attribute 'tzinfo'`

### Changed

- **Standardized Energy Point Time Periods** (90+ points):
  - Removed word "counter" from all energy descriptions for conciseness
  - Standardized time period suffixes:
    - "- Total" for cumulative totals
    - "- Lifetime" for lifetime/runtime values (was "Runtime", "lifetime total")
    - "- Week" for weekly periods (was "last week", "last 7 days", "7D")
    - "- Month" for monthly periods (was "last month", "last 30 days", "30D")
    - "- Year" for yearly periods (was "last year", "1Y")
    - "- Today" for daily periods (was "today", "day")
  - Examples:
    - "Export energy counter lifetime total" → "Export energy - Lifetime"
    - "Battery discharge energy last 7 days" → "Battery discharge energy - Week"
    - "Meter active power total" → "Meter active power - Total"

- **Improved Point Descriptions** (20+ points):
  - store_size: "Flash storage used" (improved capitalization)
  - PF: "Power factor" (simplified)
  - PowerPeakToday: "Peak power output today"
  - GlobState: "Global operational state"
  - sys_load: "System load average"
  - Fcc: "Central controller frequency"
  - FRT_state: "Fault Ride Through (FRT) status"
  - ECt/EDt: Added "(CT)"/"(DT)" acronyms
  - ETotalApparent: Removed "in kVAh" (unit shown separately)
  - cosPhi: Display "Power Factor" (removed "Cos φ")
  - mfg_week_year: "Manufacturing Week/Year" (restored prefix)

- **Standardized Phase Naming**: All phase-related points now use A/B/C/N notation (40+ points)
  - Phase voltages: "AC Voltage Phase A-N" (was "Grid voltage phase A (L1) to neutral")
  - Line-to-line: "AC Voltage Phase A-B" (was "AC line-to-line voltage phase A-B (L1-L2)")
  - Currents: "AC Current Phase A" (was "Phase A AC current")
  - Frequency: "AC Frequency Phase A" (was "AC frequency for phase A")
  - Meter: "Meter Power Phase A" (was "Meter active power phase L1")
  - House: "House Power Phase A" (was "House consumption phase L1 power")

- **Removed Redundant Words**: Cleaned up descriptions
  - Removed word "measurement" from descriptions (was "DC current measurement for string 1")
  - Standardized string references to "(String #)" format (was "from MPPT string 1")
  - Fixed "Combined DC input power from all strings" → "Total DC Input Power"

- **Fixed Specific Points**: Corrected inconsistencies
  - GlobalSt: "Global inverter status"
  - logger_loggerId: "Logger ID" (fixed repeated word)
  - InverterSt: Properly capitalized "Inverter Status"
  - free_ram/flash_free: Improved descriptions

**Summary**: 180+ point descriptions improved (70% of all 258 points), focusing on consistency, conciseness, and professional naming conventions.

[Full release notes](docs/releases/v1.0.0-beta.15.md)

## [1.0.0-beta.14] - 2025-10-31

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
