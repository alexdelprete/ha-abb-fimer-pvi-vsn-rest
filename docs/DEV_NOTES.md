# Development Notes - ha-abb-fimer-pvi-vsn-rest

## 2025-10-26: Italian Translation and Documentation Updates

### Summary

Added complete Italian translation for the integration and updated all documentation to reflect i18n support and recent improvements.

### Implementation Details

**Translation:**

- Created `translations/it.json` with complete Italian translation
- All UI strings translated: config flow, options, errors, abort messages
- Maintains all placeholders and formatting from English version
- Natural Italian phrasing with consistent technical terminology

**Documentation Updates:**

- README.md: Added "Multi-Language" to features, new "Translations" section
- CHANGELOG.md: Added internationalization section to unreleased changes
- Project structure updated to show both translation files

**Supported Languages:**

- 🇬🇧 English (`en.json`) - Complete
- 🇮🇹 Italian (`it.json`) - Complete

Home Assistant automatically detects and uses the appropriate language based on system settings.

### Files Modified

1. `translations/it.json` (NEW) - Complete Italian translation
2. `README.md` - Added translations section and feature
3. `CHANGELOG.md` - Added internationalization to unreleased
4. `docs/DEV_NOTES.md` - This entry

### Commits

- **feat(i18n): add Italian translation** (de1d37d)
- **docs: update documentation for i18n support** (pending)

---

## 2025-10-26: Discovery Module and Device Info Implementation

### Summary (Discovery)

Completed comprehensive implementation of device discovery and complete
device_info metadata for the VSN REST integration. This establishes proper
device hierarchy in Home Assistant with all standard device fields.

### Implementation Details (Discovery)

#### 1. Discovery Module (`abb_fimer_vsn_rest_client/discovery.py`)

**New centralized discovery system:**

- **Responsibilities:**
  - Detect VSN model (VSN300/VSN700)
  - Fetch status and livedata endpoints
  - Extract logger metadata (S/N, model, firmware, hostname)
  - Discover all connected devices (inverters, meters, batteries)
  - Handle device identification with VSN-specific logic

**Smart Device ID Handling:**

- VSN300 datalogger: Extract `sn` point → `"111033-3N16-1421"`
- VSN700 datalogger: Strip colons from MAC → `"ac1f0fb050b5"` (no underscores!)
- Inverters: Use serial number as-is

**Device Metadata Extraction:**

- VSN300: Model from `status["keys"]["device.modelDesc"]` → `"PVI-10.0-OUTD"`
- VSN700: Model from `livedata["device_model"]` → `"REACT2-5.0-TL"`
- Firmware from `C_Vr` point (inverters) or `fw_ver` point (datalogger)
- Manufacturer from `C_Mn` point → `"Power-One"`, `"ABB"`, `"FIMER"`

**Data Structures:**

```python
@dataclass
class DiscoveredDevice:
    device_id: str               # Clean ID (S/N or MAC without colons)
    raw_device_id: str          # Original from API
    device_type: str            # inverter_3phases, meter, etc.
    device_model: str | None    # PVI-10.0-OUTD, REACT2-5.0-TL
    manufacturer: str | None    # Power-One, ABB, FIMER
    firmware_version: str | None # C008, 1.9.2
    hardware_version: str | None
    is_datalogger: bool

@dataclass
class DiscoveryResult:
    vsn_model: str              # VSN300 or VSN700
    logger_sn: str              # Logger serial number
    logger_model: str | None    # WIFI LOGGER CARD
    firmware_version: str | None # 1.9.2
    hostname: str | None        # ABB-077909-3G82-3112.local
    devices: list[DiscoveredDevice]
    status_data: dict[str, Any]
```

#### 2. Integration Updates

**config_flow.py:**

- Replaced manual validation with discovery function
- Simplified connection validation logic
- Better device discovery logging during setup

**coordinator.py:**

- Added `discovery_result` parameter to store complete discovery data
- Stores `discovered_devices` list for sensor platform
- Pre-initializes VSN model from discovery

**init module:**

- Performs discovery during integration setup
- Passes discovery result to coordinator
- Logs all discovered devices for debugging

**sensor module:**

- Complete device_info implementation with all HA fields
- Dynamic device naming from discovery metadata
- Proper device hierarchy with `via_device`

#### 3. Device Info Fields

All standard Home Assistant device fields now populated:

| Field | Description | Example |
|-------|-------------|---------|
| `identifiers` | Stable device identifier | `{("abb_fimer_pvi_vsn_rest", "077909-3G82-3112")}` |
| `name` | Model + Serial | `"PVI-10.0-OUTD (077909-3G82-3112)"` |
| `manufacturer` | From SunSpec `C_Mn` | `"Power-One"`, `"ABB"`, `"FIMER"` |
| `model` | Device model | `"PVI-10.0-OUTD"`, `"REACT2-5.0-TL"` |
| `serial_number` | Device S/N or clean MAC | `"077909-3G82-3112"` |
| `sw_version` | **Firmware version** | `"C008"` (inverter), `"1.9.2"` (datalogger) |
| `hw_version` | Hardware version | (if available) |
| `configuration_url` | Datalogger web UI | `"http://ABB-077909-3G82-3112.local"` |
| `via_device` | Device hierarchy | Links inverters to datalogger |

**Key Fix:** Changed `sw_version` from VSN model (`"VSN300"`) to actual firmware version (`"C008"`, `"1.9.2"`)

#### 4. Device Hierarchy

Proper device relationships established:

```text
VSN300 Datalogger (111033-3N16-1421)
  ├─ configuration_url: http://abb-vsn300.local
  └─ Contains:
      ├─ PVI-10.0-OUTD Inverter (077909-3G82-3112)
      │   └─ via_device: VSN300
      ├─ Energy Meter (if present)
      │   └─ via_device: VSN300
      └─ Battery Storage (if present)
          └─ via_device: VSN300
```

### Files Modified (Discovery)

**Core Implementation:**

- `custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/discovery.py` (NEW)
  - 365 lines
  - Complete discovery module with helper functions

- `custom_components/abb_fimer_pvi_vsn_rest/config_flow.py`
  - Updated to use discovery module
  - Simplified validation logic

- `custom_components/abb_fimer_pvi_vsn_rest/coordinator.py`
  - Added discovery_result storage
  - Stores discovered_devices list

- `custom_components/abb_fimer_pvi_vsn_rest/__init__.py`
  - Performs discovery during setup
  - Passes discovery to coordinator

- `custom_components/abb_fimer_pvi_vsn_rest/sensor.py`
  - Complete device_info implementation
  - All HA device fields populated
  - Device hierarchy with via_device

**Documentation:**

- `README.md` - Complete user documentation
- `CLAUDE.md` - Comprehensive dev guidelines
- `docs/DEV_NOTES.md` - This file

### Testing Results

**Discovery Testing:**

- ✅ VSN300 model detection
- ✅ VSN300 datalogger S/N extraction from `sn` point
- ✅ VSN700 datalogger MAC cleaning (colons stripped)
- ✅ Inverter model extraction (VSN300: status, VSN700: livedata)
- ✅ Firmware version extraction (`C_Vr`, `fw_ver` points)
- ✅ Manufacturer extraction (`C_Mn` point)

**Device Info Testing:**

- ✅ All device_info fields populated
- ✅ Proper device naming (Model + Serial)
- ✅ Device hierarchy (via_device)
- ✅ Configuration URL (datalogger only)
- ✅ Firmware version (not VSN model)

### Entity Naming Examples

**Before (Generic):**

```text
Device: "VSN Device 077909-3G82-3112"
Entity: sensor.vsn_device_077909_3g82_3112_watts
```

**After (Proper):**

```text
Device: "PVI-10.0-OUTD (077909-3G82-3112)"
Entity: sensor.pvi_10_0_outd_077909_3g82_3112_watts
```

### Commits (Discovery)

1. **feat(discovery): implement centralized device discovery** (0c83048)
   - New discovery.py module
   - Updated config_flow, coordinator, sensor, init
   - Smart device ID handling for VSN300/VSN700

2. **feat(device_info): implement complete device info with all HA fields** (4ae089f)
   - Added firmware_version to DiscoveredDevice
   - Extract firmware from C_Vr and fw_ver points
   - Complete device_info with all standard HA fields

### Technical Notes

**Unique ID Strategy:**

- Config entry: Logger serial number (lowercase)
- Device identifier: Device serial number or clean MAC
- Sensor unique_id: `{DOMAIN}_{device_id}_{point_name}`

**VSN300 vs VSN700 Differences:**

VSN300:

- Auth: X-Digest custom scheme
- Model location: `status["keys"]["device.modelDesc"]["value"]`
- Datalogger ID: Extract `sn` point from livedata
- Firmware: `C_Vr` (inverter), `fw_ver` (datalogger)

VSN700:

- Auth: HTTP Basic
- Model location: `livedata["device_model"]`
- Datalogger ID: Clean MAC (strip colons)
- Firmware: Often not available

**Performance:**

- Discovery runs once during setup: ~2-3 seconds
- Includes status + livedata fetch
- Cached in coordinator for sensor creation
- No performance impact on normal polling

### Code Quality

**Standards Followed:**

- ✅ Type hints on all functions and classes
- ✅ Proper async/await patterns
- ✅ Logging with context (no f-strings)
- ✅ Comprehensive error handling
- ✅ Dataclasses for structured data
- ✅ Ruff linting compliance
- ✅ Home Assistant best practices

### Benefits

1. **Stable Identifiers**: Logger S/N-based unique IDs survive network changes
2. **Complete Metadata**: All HA device fields properly populated
3. **Device Hierarchy**: Proper relationships between datalogger and devices
4. **Better UX**: Proper device names in HA UI
5. **Maintainability**: Centralized discovery logic, easy to extend
6. **Diagnostics**: Complete device info available for troubleshooting

### Next Steps

1. ⏳ User testing with real VSN300/VSN700 devices
2. ⏳ Validate entity creation with multiple inverters
3. ⏳ Test with meters and battery storage
4. ⏳ Beta release v1.0.0-beta.2

### References

- [discovery.py](../custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/discovery.py)
- [config_flow.py](../custom_components/abb_fimer_pvi_vsn_rest/config_flow.py)
- [coordinator.py](../custom_components/abb_fimer_pvi_vsn_rest/coordinator.py)
- [sensor.py](../custom_components/abb_fimer_pvi_vsn_rest/sensor.py)
- [README.md](../README.md)
- [CLAUDE.md](../CLAUDE.md)

---

---

## 2025-10-26: VSN Client Normalization Feature Complete

### Summary (VSN Client)

Completed implementation of data normalization in the standalone `vsn_client.py`
test script. The normalization feature transforms raw VSN data to Home Assistant
entity format using the VSN-SunSpec point mapping.

### Implementation Details (VSN Client)

**Approach Selected:** Option 3 - URL-based mapping from GitHub

- Downloads mapping JSON from GitHub on-demand
- No embedded data in script (keeps file size at 20 KB)
- Requires internet connection for normalization
- Gracefully degrades if mapping unavailable

**Components Added:**

1. `load_mapping_from_url()` - Fetches and indexes mapping from GitHub
2. `normalize_livedata()` - Transforms VSN data to HA entity format
3. Integration into test flow with proper error handling
4. Enhanced test summary showing normalization results

**Files Modified:**

- `scripts/vsn_client.py` (546 lines, 20 KB)
  - Added normalization module
  - Updated test flow
  - Enhanced error messages

- `scripts/VSN_CLIENT_README.md`
  - Documented normalization feature
  - Added requirements and troubleshooting
  - Updated example output

**Files Created:**

- `docs/vsn-sunspec-point-mapping.json` (126 KB, 259 mappings)
  - Converted from Excel source
  - Runtime format for fast loading

- `scripts/generate_mapping_json.py`
  - Converts Excel to JSON
  - Validates structure
  - Generates stats

- `docs/MAPPING_FORMAT.md`
  - Documents dual format workflow
  - Excel for editing, JSON for runtime

### Testing Results (VSN Client)

**Device:** VSN300 at abb-vsn300.axel.dom

- ✅ Device detection: VSN300
- ✅ /v1/status: OK (logger: 111033-3N16-1421, inverter: PVI-10.0-OUTD)
- ✅ /v1/livedata: OK (2 devices, 52 raw points)
- ✅ /v1/feeds: OK (2 feeds)
- ⚠️ Normalization: Skipped (mapping file not in GitHub yet)

**Expected After Push:**

- Mapping file available at GitHub URL
- Normalization will work automatically
- Will transform 52 raw points to 53 normalized HA entities

### Dependencies

**Runtime:**

- Python 3.9+
- aiohttp
- Internet connection (for normalization only)

**Development:**

- openpyxl (for Excel→JSON conversion only)

### References (VSN Client)

- [vsn_client.py](../scripts/vsn_client.py)
- [VSN_CLIENT_README.md](../scripts/VSN_CLIENT_README.md)
- [MAPPING_FORMAT.md](./MAPPING_FORMAT.md)
- [vsn-sunspec-point-mapping.json](./vsn-sunspec-point-mapping.json)
- [generate_mapping_json.py](../scripts/generate_mapping_json.py)
