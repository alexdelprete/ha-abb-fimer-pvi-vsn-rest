# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

- **Improved Sensor Labels and Entity IDs**: Enhanced label and entity ID generation for 21 VSN300-specific SunSpec points ([generate_mapping_excel.py:766-884](scripts/generate_mapping_excel.py#L766), [generate_mapping_excel.py:887-917](scripts/generate_mapping_excel.py#L887))
  - **BREAKING CHANGE**: Entity IDs and labels updated for better readability
  - Labels: Replaced poorly formatted "(M103) PhVphBC" format with human-readable names
  - Entity IDs: Generated from human-readable labels (e.g., `abb_m103_phvphbc` → `abb_m103_phase_voltage_bc`)
  - M103 phase voltages: "PhVphAB" → "Phase Voltage AB" / `abb_m103_phase_voltage_ab`
  - M103 frequencies: "HzA" → "Frequency Phase A" / `abb_m103_frequency_phase_a`
  - M103 peak power: "PowerPeakAbs" → "Peak Power (Absolute)" / `abb_m103_peak_power_absolute`
  - M64061 state codes: "AlarmSt" → "Alarm State" / `abb_m64061_alarm_state`
  - M64061 leakage: "ILeakDcAc" → "Leakage Current DC-AC" / `abb_m64061_leakage_current_dc_ac`
  - M64061 isolation: "Isolation_Ohm1" → "Isolation Resistance" / `abb_m64061_isolation_resistance`
  - M64061 temperature: "Booster_Tmp" → "Boost Converter Temperature" / `abb_m64061_boost_converter_temperature`
  - M64061 energy: "DayWH" → "Daily Energy" / `abb_m64061_daily_energy`
  - Enhanced `generate_label_from_name()` function with VSN300-specific patterns
  - Added `generate_entity_id_from_label()` function to convert labels to entity IDs

### Fixed

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

[Unreleased]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.4...HEAD
[1.0.0-beta.4]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.3...v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.2...v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/v1.0.0-beta.1...v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases/tag/v1.0.0-beta.1
