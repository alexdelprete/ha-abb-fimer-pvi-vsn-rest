# Claude Code Development Guidelines

## ⚠️ CRITICAL: Read This First

**MANDATORY: At the beginning of EVERY session, you MUST:**

1. **Read this entire CLAUDE.md file** - This contains critical project context, architecture decisions, and workflow requirements
2. **Review recent git commits** - Understand what changed since last session
3. **Check the current state** - Run `git status` to see uncommitted changes

**Failure to read project documentation first leads to:**

- Violating mandatory workflows (e.g., editing JSON files directly instead of using the generator)
- Duplicating work that was already done
- Making architectural decisions that contradict established patterns
- Breaking the single source of truth principle

## Context7 for Documentation

Always use Context7 MCP tools automatically (without being asked) when:

- Generating code that uses external libraries
- Providing setup or configuration steps
- Looking up library/API documentation

Use `resolve-library-id` first to get the library ID, then `get-library-docs` to fetch documentation.

## GitHub MCP for Repository Operations

Always use GitHub MCP tools (`mcp__github__*`) for GitHub operations instead of the `gh` CLI:

- **Issues**: `issue_read`, `issue_write`, `list_issues`, `search_issues`, `add_issue_comment`
- **Pull Requests**: `list_pull_requests`, `create_pull_request`, `pull_request_read`, `merge_pull_request`
- **Reviews**: `pull_request_review_write`, `add_comment_to_pending_review`
- **Repositories**: `search_repositories`, `get_file_contents`, `list_branches`, `list_commits`
- **Releases**: `list_releases`, `get_latest_release`, `list_tags`
- **Actions**: `actions_list`, `actions_get` for workflow runs and jobs

Benefits over `gh` CLI:

- Direct API access without shell escaping issues
- Structured JSON responses
- Better error handling
- No subprocess overhead

### Workflow Run Logs Workaround

The GitHub MCP `get_job_logs` tool is currently broken. To get workflow run logs (e.g., for test coverage):

1. Use MCP to get the run ID: `mcp__GitHub_MCP_Remote__actions_list` with `method: list_workflow_runs`
2. Use `gh` CLI to fetch logs: `gh run view <run_id> --repo owner/repo --log`
3. Filter with grep: `gh run view <run_id> --repo owner/repo --log | grep "TOTAL\|coverage"`

## Pre-Commit Checks (MANDATORY)

> **⛔ CRITICAL: ALWAYS run pre-commit checks before ANY git commit.**
> This is a hard rule - no exceptions. Never commit without passing all checks.

```bash
uvx pre-commit run --all-files
```

All checks must pass before committing. This applies to ALL commits, not just releases.

### Pre-Commit Configuration

Linting tools and settings are defined in `.pre-commit-config.yaml`:

| Hook | Tool | Purpose |
| ---- | ---- | ------- |
| ruff | `ruff check --no-fix` | Python linting |
| ruff-format | `ruff format --check` | Python formatting |
| jsonlint | `uvx --from demjson3 jsonlint` | JSON validation |
| yamllint | `uvx yamllint -d "{...}"` | YAML linting (inline config) |
| pymarkdown | `pymarkdown scan` | Markdown linting |

All hooks use `language: system` (local tools) with `verbose: true` for visibility.

### Windows Shell Notes

When running shell commands on Windows, stray `nul` files may be created (Windows null device artifact). Check for and delete them after command execution:

```bash
rm nul  # if it exists
```

## Quality Scale Tracking

This integration tracks [Home Assistant Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/) rules in `quality_scale.yaml`.

**When implementing new features or fixing bugs:**

1. Check if the change affects any quality scale rules
2. Update `quality_scale.yaml` status accordingly:
   - `done` - Rule is fully implemented
   - `todo` - Rule needs implementation
   - `exempt` with `comment` - Rule doesn't apply (explain why)
3. Aim to complete all Bronze tier rules first, then Silver, Gold, Platinum

## Testing Approach

> **⛔ CRITICAL: NEVER modify production code to make tests pass. Always fix the tests instead.**
> Production code is the source of truth. If tests fail, the tests are wrong - not the production code.
> The only exception is when production code has an actual bug that tests correctly identified.
>
> **📋 RECOMMENDED: Run tests via CI only.**
> Push commits and let GitHub Actions run the test suite. This ensures consistent test environment
> and avoids local environment issues. Only run tests locally when debugging specific failures.

## Project Overview

This is the **ha-abb-fimer-pvi-vsn-rest** integration for Home Assistant.
It provides monitoring of ABB/FIMER/Power-One PVI inverters through VSN300
or VSN700 dataloggers via their REST API.

**Current Status**: v1.1.7 - Active development

**Key Features**:

- Automatic VSN300/VSN700 detection
- Multi-device support (inverters, meters, batteries)
- SunSpec-normalized data schema with Aurora protocol integration
- Modern Home Assistant entity naming pattern
- Comprehensive sensor attributes with 258 unique mapped data points
- Human-readable state translations for status entities
- Custom icon support (energy icons, diagnostic icons)
- Correct timestamp handling with Aurora epoch offset

## Architecture

### Data Flow

```text
VSN300/VSN700 Datalogger (REST API)
    ↓
Discovery Module (detect model, find devices)
    ↓
REST Client (authentication + fetch)
    ↓
Normalizer (VSN → SunSpec format)
    ↓
Coordinator (periodic updates)
    ↓
Sensor Platform (HA entities)
```

### Key Components

#### 1. Discovery Module (`abb_fimer_vsn_rest_client/discovery.py`)

Centralized device discovery that runs during setup and configuration.

**Responsibilities:**

- Detect VSN model (VSN300 or VSN700)
- Fetch status and livedata endpoints
- Extract logger metadata (S/N, model, firmware, hostname)
- Discover all connected devices (inverters, meters, batteries)
- Handle device identification:
  - VSN300 datalogger: Extract `sn` point → `"111033-3N16-1421"`
  - VSN700 datalogger: Strip colons from MAC → `"ac1f0fb050b5"`
  - Inverters: Use serial number as-is
- Extract device metadata:
  - VSN300: Model from `status["keys"]["device.modelDesc"]`
  - VSN700: Model from `livedata["device_model"]`
  - Firmware from `C_Vr` point (inverters) or `fw_ver` point (datalogger)
  - Manufacturer from `C_Mn` point

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

#### 2. REST Client (`abb_fimer_vsn_rest_client/client.py`)

Handles communication with VSN datalogger REST API.

**Responsibilities:**

- Authenticate with VSN300 (X-Digest) or VSN700 (Basic Auth)
- Fetch `/v1/status`, `/v1/livedata`, `/v1/feeds` endpoints
- Merge livedata + feeds data
- Pass raw data to normalizer
- Return normalized data

**Key Methods:**

- `connect()`: Detect VSN model and authenticate
- `get_normalized_data()`: Fetch and normalize data
- `close()`: Clean up resources

#### 3. Authentication (`abb_fimer_vsn_rest_client/auth.py`)

VSN-specific authentication schemes.

**VSN300:**

- Custom HTTP Digest with `X-Digest` header
- Process:
  1. Fetch challenge from `/v1/dgst`
  2. Compute SHA-256 digest: `user:realm:password`
  3. Compute final: `method:uri:digest`
  4. Add header: `Authorization: X-Digest {final_digest}`

**VSN700:**

- Standard HTTP Basic Authentication
- Base64-encoded `username:password`
- Header: `Authorization: Basic {base64}`

#### 4. Normalizer (`abb_fimer_vsn_rest_client/normalizer.py`)

Transforms VSN proprietary format to SunSpec-compatible schema.

**Responsibilities:**

- Load mapping definitions from JSON file
- Map VSN point names to SunSpec normalized names
- Apply Home Assistant metadata (device_class, state_class, units, labels)
- Populate comprehensive point attributes
- Handle device ID normalization (MAC → S/N for datalogger)

**Mapping Structure (Deduplicated):**

- **Source**: `docs/vsn-sunspec-point-mapping.xlsx` (Excel with model flags)
- **Runtime**: `custom_components/.../data/vsn-sunspec-point-mapping.json`
- **Format**: 210 unique points with `models` array for multi-model support

**Point Mapping Example:**

```json
{
  "REST Name (VSN700)": "Pgrid",
  "REST Name (VSN300)": "m103_1_W",
  "SunSpec Normalized Name": "W",
  "HA Name": "watts",
  "Label": "Watts",
  "Description": "AC Power",
  "HA Display Name": "AC Power",
  "Category": "Inverter",
  "HA Unit of Measurement": "W",
  "HA State Class": "measurement",
  "HA Device Class": "power",
  "models": ["M103", "M802"]
}
```

**Key Mapping Columns (HA-Prefixed):**

- `HA Unit of Measurement`: Home Assistant unit (SensorDeviceClass)
- `HA State Class`: Home Assistant state class (SensorStateClass)
- `HA Device Class`: Home Assistant device class
- `HA Display Name`: User-facing display name

**Mapping Workflow:**

1. Edit Excel: `docs/vsn-sunspec-point-mapping.xlsx`
2. Convert to JSON: `python scripts/convert_excel_to_json.py`
3. Commit both files (Excel + both JSON copies)

See [docs/MAPPING_FORMAT.md](docs/MAPPING_FORMAT.md) for full documentation.

#### 5. Coordinator (`coordinator.py`)

Home Assistant DataUpdateCoordinator for managing polling.

**Responsibilities:**

- Periodic data fetching (default: 60s)
- Error handling and retries
- Store discovery result
- Distribute data to sensors

**Key Attributes:**

- `client`: VSN REST client instance
- `vsn_model`: VSN300 or VSN700
- `discovery_result`: Full discovery data
- `discovered_devices`: List of DiscoveredDevice

#### 6. Config Flow (`config_flow.py`)

UI for integration setup and configuration.

**Features:**

- User flow: Initial setup with host/credentials
- Reconfigure flow: Change host or credentials
- Options flow: Adjust scan interval
- Connection validation using discovery module
- Socket check on port 80 before REST API calls

**Validation Process:**

1. Check socket connectivity (port 80)
2. Run discovery (detect model, find devices)
3. Set unique_id to logger serial number
4. Store VSN model in config_entry

#### 7. Sensor Platform (`sensor.py`)

Creates Home Assistant sensor entities using modern naming pattern.

**Entity Naming Pattern (has_entity_name=True):**

- **Device Name**: Technical format for predictable entity IDs (v1.0.0-beta.25+)
  - Format: `{DOMAIN}_{device_type}_{serial_compact}`
  - Uses DOMAIN constant from manifest.json: `abb_fimer_pvi_vsn_rest`
  - Example: `abb_fimer_pvi_vsn_rest_inverter_0779093g823112`
  - Device type simplified: `inverter`, `datalogger`, `meter`, `battery`
  - Serial compacted: remove `-`, `:`, `_` and lowercase

- **Entity Name**: Standardized display name from mapping (v1.0.0-beta.22+)
  - Pattern: [Type] [AC/DC] - [Details] - [Time Period]
  - Examples: "Power AC", "Energy AC - Produced Lifetime", "Temperature - Cabinet"
  - From `HA Display Name` field in mapping
  - Displayed as entity name on device page

- **suggested_object_id**: Just the point name (v1.0.0-beta.25+)
  - Example: `wlan0_essid`, `ac_power`
  - HA combines with device name to create entity_id

- **Entity ID** (auto-generated by HA):
  - Format: `sensor.{slugify(device_name)}_{suggested_object_id}`
  - Example: `sensor.abb_fimer_pvi_vsn_rest_inverter_0779093g823112_wlan0_essid`
  - **Changed in v1.0.0-beta.25**: Correct implementation using has_entity_name=True

- **Unique ID**: Stable identifier (v1.0.0-beta.22+)
  - Format: `{domain}_{device_type}_{serial_compact}_{point_name}`
  - Example: `abb_fimer_pvi_vsn_rest_inverter_0779093g823112_wlan0_essid`
  - Never changes once set

**Sensor Attributes (Comprehensive):**

All sensors include rich metadata attributes:

```python
{
    # Identity
    "device_id": "077909-3G82-3112",
    "device_type": "inverter_3phases",
    "point_name": "watts",

    # Display Names
    "friendly_name": "AC Power",
    "label": "Watts",

    # VSN REST API Names
    "vsn300_rest_name": "m103_1_W",
    "vsn700_rest_name": "Pgrid",

    # SunSpec Information
    "sunspec_model": "M103, M802",  # Comma-separated models
    "sunspec_name": "W",
    "description": "AC Power",

    # Compatibility Flags
    "vsn300_compatible": True,
    "vsn700_compatible": True,

    # Category
    "category": "Inverter"
}
```

**Device Info:**

All HA device info fields populated from discovery:

- `identifiers`: `(DOMAIN, device_id)`
- `name`: Device identifier (e.g., `"abb_vsn_rest_inverter_0779093g823112"`)
- `manufacturer`: From `C_Mn` point
- `model`: Device model
- `serial_number`: Device S/N or clean MAC
- `sw_version`: Firmware version from `C_Vr` or `fw_ver`
- `hw_version`: Hardware version (if available)
- `configuration_url`: Datalogger hostname (datalogger only)
- `via_device`: Link to datalogger (for inverters/meters)

## Key Architectural Decisions

### Mapping Structure (v2 - Deduplicated)

**Decision**: Use deduplicated Excel mapping with model flags instead of duplicate rows.

**Rationale**:

- Original 277 rows contained 67 duplicates (same point across multiple models)
- Reduced to 210 unique points using model flag columns (M1, M103, M160, etc.)
- Each point has `models` array in JSON: `["M103", "M802"]`
- Cleaner structure, easier maintenance, no data loss

**Implementation**:

- Excel: Model flag columns with YES/NO values
- JSON: `models` array with applicable model names
- Loader: Handles both formats (backward compatible)

### VSN Name Normalization for Duplicate Detection (v1.1.12)

**Decision**: Prioritize VSN300 (SunSpec-based) names as canonical when merging duplicate sensors that exist in both VSN300 and VSN700 models.

**Rationale**:

- VSN300 REST API names are based on the SunSpec international standard (e.g., `Isolation_Ohm1`, `ILeakDcAc`)
- VSN700 REST API names are ABB/FIMER proprietary (e.g., `Riso`, `IleakInv`)
- SunSpec names provide consistent, standardized naming across all solar inverter systems
- Merging duplicates eliminates redundant sensors with inconsistent metadata

**Problem Solved**:

Before normalization, duplicate entries existed for 5 sensor pairs:

1. Insulation Resistance: `Isolation_Ohm1` (VSN300) vs `Riso` (VSN700) - different units (MΩ vs MOhm), missing icon
2. Leakage Current Inverter: `ILeakDcAc` (VSN300, mA) vs `IleakInv` (VSN700, A) - **CRITICAL 1000x unit mismatch**
3. Leakage Current DC: `ILeakDcDc` (VSN300, mA) vs `IleakDC` (VSN700, A) - **CRITICAL 1000x unit mismatch**
4. Ground Voltage: `VGnd` (VSN300) vs `Vgnd` (VSN700) - capitalization only
5. Battery SoC: `Soc` (VSN300) vs `TSoc` (VSN700) - naming convention

**Implementation**:

```python
# scripts/vsn-mapping-generator/generate_mapping.py
VSN_NAME_NORMALIZATION = {
    # VSN700 proprietary → VSN300 SunSpec (canonical)
    "Riso": "Isolation_Ohm1",
    "IleakInv": "ILeakDcAc",
    "IleakDC": "ILeakDcDc",
    "Vgnd": "VGnd",
    "TSoc": "Soc",
}

# Applied during VSN700 point processing
normalized_name = normalize_vsn700_name(point_name)
row = create_row_with_model_flags(
    vsn700_name=point_name,
    vsn300_name="N/A",
    sunspec_name=normalized_name,  # Uses canonical VSN300 name
    ...
)
```

**Runtime Value Conversion** (normalizer.py):

```python
# VSN700 leakage current sensors report in A, standardize to mA
A_TO_MA_POINTS = {"IleakInv", "IleakDC"}

if vsn_model == "VSN700" and point_name in A_TO_MA_POINTS:
    point_value = point_value * 1000  # A → mA
```

**Result**:

- Reduced from 265 to 253 unique points (5 duplicates merged)
- Single `isolation_ohm1` sensor with both REST names, unit=MOhm, icon=mdi:omega ✅
- Single `ileakdcac` and `ileakdcdc` sensors with unit=mA, A→mA conversion for VSN700 ✅
- Consistent metadata across both VSN models

### HA-Prefixed Column Names

**Decision**: Use "HA Unit of Measurement", "HA State Class", "HA Device Class" in mapping.

**Rationale**:

- These are Home Assistant concepts (SensorDeviceClass, SensorStateClass, unit_of_measurement)
- HA prefix makes it explicit that values are for Home Assistant
- Removes confusion about whether SunSpec values need transformation
- Cleaner, more accurate naming

**Implementation**:

- Removed duplicate columns: "Units", "State Class", "Device Class"
- All code references updated to use HA-prefixed names
- Excel: 29 columns → 26 columns
- JSON: No duplicate keys

### Modern Entity Naming Pattern

**Decision**: Use `has_entity_name=True` pattern with technical device names (v1.0.0-beta.25+).

**Rationale**:

- `suggested_object_id` ONLY works when `has_entity_name=True` (verified in HA core source code)
- When `has_entity_name=False`, HA completely ignores `suggested_object_id`
- Technical device names provide predictable entity ID prefix
- Entity names on device pages remain friendly ("AC Power", "WiFi SSID")
- Trade-off: Device names are technical, but this is acceptable for predictable entity IDs

**Implementation**:

- `has_entity_name = True` ✅ (required for `suggested_object_id` to work)
- Device name: Technical format `{domain}_{device_type}_{serial_compact}`
  - Example: "abb_fimer_pvi_vsn_rest_datalogger_1110333n161421"
- Entity name (`_attr_name`): Friendly display name from mapping (e.g., "AC Power")
- `suggested_object_id`: Just the point name (e.g., "wlan0_essid")
- Entity ID: HA combines them → `sensor.abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_wlan0_essid` ✅
- Result: Predictable IDs, friendly entity names, acceptable device names

**Critical Note**: `has_entity_name=False` does NOT work with `suggested_object_id` - HA ignores it completely. This was the bug in beta.24.

### Simplified Entity IDs (No Model)

**Decision**: Remove model from entity IDs.

**Rationale**:

- Model information still available in attributes
- Shorter, cleaner entity IDs
- One device rarely has multiple models for same point
- Model info: `sunspec_model` attribute

**Implementation**:

- Old: `abb_vsn_rest_inverter_0779093g823112_m103_watts`
- New: `abb_vsn_rest_inverter_0779093g823112_watts`
- Unique ID: `abb_vsn_rest_inverter_0779093g823112_watts`

### Entity ID Standardization with Domain Prefix (v1.0.0-beta.22)

**Decision**: Add domain prefix to all entity IDs and align unique_id format.

**Rationale**:

- **Namespace Isolation**: Prevents conflicts with other integrations that might use similar entity naming patterns
- **Clear Ownership**: Immediately obvious which integration owns each entity
- **Consistency**: Aligns unique_id and entity_id formats for better maintainability
- **Dynamic Source**: Uses DOMAIN constant from manifest.json instead of hardcoded values

**Implementation**:

**Before (beta.21)**:

- Entity ID: `sensor.inverter_0779093g823112_ac_power`
- Unique ID: `abb_vsn_rest_inverter_0779093g823112_ac_power`
- Issue: No domain prefix in entity_id, inconsistent formats

**After (beta.22)**:

- Entity ID: `sensor.abb_fimer_pvi_vsn_rest_inverter_0779093g823112_ac_power`
- Unique ID: `abb_fimer_pvi_vsn_rest_inverter_0779093g823112_ac_power`
- Both use DOMAIN constant: `abb_fimer_pvi_vsn_rest`

**Code Changes**:

```python
# sensor.py - Entity naming configuration (v1.0.0-beta.26+)
self._attr_has_entity_name = True  # Required for suggested_object_id to work

# Device identifier (for unique_id)
device_identifier = f"{DOMAIN}_{device_type_simple}_{device_sn_compact}"

# Unique ID (stable identifier)
unique_id = f"{device_identifier}_{point_name}"
self._attr_unique_id = unique_id

# Suggested object ID (just the point name - HA combines with device_name)
self._attr_suggested_object_id = point_name

# Entity name (friendly display on device page)
self._attr_name = point_data.get("ha_display_name", point_data.get("label", point_name))

# Device name (friendly format for beautiful UI - beta.26+)
device_name = _format_device_name(
    manufacturer=manufacturer,
    device_type_simple=self._device_type_simple,
    device_model=device_model,
    device_sn_original=self._device_id,
)
# Result: "ABB Datalogger VSN300 (111033-3N16-1421)"
# Entity ID: sensor.abb_datalogger_vsn300_111033_3n16_1421_firmware_version
# Friendly Name: "ABB Datalogger VSN300 (111033-3N16-1421) Firmware Version"
```

**Breaking Change (beta.26)**: Switched to friendly device names for beautiful UI. Entity IDs changed to slugified friendly format.

**Breaking Change (beta.25)**: All entity IDs changed, requires manual entity registry cleanup for existing users.

### Display Name Standardization (v1.0.0-beta.22)

**Decision**: Standardize all display names to TYPE-first pattern for optimal grouping in Home Assistant UI.

**Pattern**: `[Type] [AC/DC] - [Details] - [Time Period]`

**Rationale**:

- **Better Grouping**: TYPE-first naming enables perfect grouping in HA entity lists (all "Energy" entities together, all "Power" entities together, etc.)
- **Consistent Structure**: Uniform pattern across all 187 standardized entities
- **Clear Hierarchy**: AC/DC designation follows type, details are separated by dashes
- **Time Period Clarity**: Standardized terminology (Lifetime, Since Restart, Last 7 Days, Last 30 Days, Last Year, Today)
- **Shorter Names**: Removed verbose prefixes like "Inverter AC energy produced" → "Energy AC - Produced"

**Implementation**:

187 entities standardized across categories:

- **Energy**: 75 entities (e.g., "Inverter AC energy produced - Lifetime" → "Energy AC - Produced Lifetime")
- **Power**: 24 entities (e.g., "AC Power" → "Power AC")
- **Voltage**: 27 entities (e.g., "AC Voltage A-N" → "Voltage AC - Phase A-N")
- **Current**: 19 entities (e.g., "AC Current" → "Current AC")
- **Temperature**: 9 entities (e.g., "Cabinet Temperature" → "Temperature - Cabinet")
- **Frequency**: 6 entities (e.g., "Grid Frequency" → "Frequency AC - Grid")
- **Reactive Power**: 5 entities (e.g., "Reactive power at grid connection point" → "Reactive Power - Grid Connection")
- **Other**: 22 entities (Power Factor, Resistance, Speed, Count, etc.)

**Code Changes**:

Added `DISPLAY_NAME_STANDARDIZATION` dictionary in `generate_mapping.py`:

```python
DISPLAY_NAME_STANDARDIZATION = {
    # Power entities
    "AC Power": "Power AC",
    "DC Power": "Power DC",
    "House Power A": "Power AC - House Phase A",

    # Energy entities
    "AC Energy": "Energy AC - Lifetime",
    "Inverter AC energy produced - Since Restart": "Energy AC - Produced Since Restart",

    # Voltage entities
    "AC Voltage A-N": "Voltage AC - Phase A-N",

    # Temperature entities
    "Cabinet Temperature": "Temperature - Cabinet",

    # ... 187 total entries
}
```

Updated `apply_display_name_corrections()` to apply both corrections and standardization in sequence.

**Non-Breaking Change**: Only user-facing display names changed, entity IDs remain based on internal point names.

### Comprehensive Sensor Attributes

**Decision**: Add 14+ metadata attributes to all sensors.

**Rationale**:

- Users can see all metadata without checking docs
- Automation can use compatibility flags
- Debugging easier with full context
- No performance impact (attributes are lightweight)

**Implementation**:

- Identity: device_id, device_type, point_name
- Display: friendly_name, label
- VSN Names: vsn300_rest_name, vsn700_rest_name
- SunSpec: sunspec_model, sunspec_name, description
- Compatibility: vsn300_compatible, vsn700_compatible
- Category: category

### Aurora Protocol Integration

The integration uses the Aurora protocol specifications for accurate data interpretation.

**Key References:**

- [ABB Aurora Solar Inverter Library](https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library)
- Timestamp utils: [utils.h](https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library/blob/master/include/utils.h#L8)
- State mappings: [statesNaming.h](https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library/blob/master/include/statesNaming.h)
- Official Protocol Documentation: [Aurora Communication Protocol v4.2](https://mischianti.org/wp-content/uploads/2022/01/AuroraCommunicationProtocol_4_2.pdf)
  - Also available locally in `docs/AuroraCommunicationProtocol_4_2.pdf`

**1. Timestamp Handling (const.py):**

Aurora protocol uses a custom epoch (Jan 1, 2000) instead of Unix epoch (Jan 1, 1970).

```python
# Aurora protocol epoch offset (Jan 1, 2000 00:00:00 UTC)
AURORA_EPOCH_OFFSET = 946684800  # seconds between Unix and Aurora epochs
```

**Implementation (sensor.py):**

- SysTime entity uses `device_class="timestamp"`
- Raw value from API is in Aurora epoch (seconds since Jan 1, 2000)
- Conversion: `datetime.fromtimestamp(value + AURORA_EPOCH_OFFSET, tz=tz)`
- Result: Correct datetime display in Home Assistant

**2. State Mapping (const.py):**

Status entities with integer state codes are translated to human-readable text:

| State Map | Description | States | Entities |
|-----------|-------------|--------|----------|
| `GLOBAL_STATE_MAP` | System-wide operational states | 42 | GlobState |
| `DCDC_STATE_MAP` | DC-DC converter states | 20 | DC1State, DC2State |
| `INVERTER_STATE_MAP` | Inverter operational states | 38 | InvState |
| `ALARM_STATE_MAP` | Alarm and error codes | 65 | AlarmState, AlarmSt |

**Entity Configuration:**

```python
STATE_ENTITY_MAPPINGS = {
    "GlobState": GLOBAL_STATE_MAP,
    "DC1State": DCDC_STATE_MAP,
    "DC2State": DCDC_STATE_MAP,
    "InvState": INVERTER_STATE_MAP,
    "AlarmState": ALARM_STATE_MAP,
    "AlarmSt": ALARM_STATE_MAP,  # VSN300 alarm
}
```

**Implementation (sensor.py):**

- State mapping applied in `native_value` property
- Integer codes automatically translated to descriptive text
- Unknown codes display as "Unknown (code)" for visibility
- Raw state code preserved in `raw_state_code` attribute

**Example Translations:**

- `6` → "Run" (Global State)
- `2` → "MPPT" (DC-DC State)
- `0` → "No Alarm" (Alarm State)
- `18` → "Ground Fault" (Alarm State)

### Custom Icons

The integration supports custom icons for special entity types:

**Icon Support (generate_mapping.py):**

1. **Energy Icons** (VAh entities):
   - 3 VAh apparent energy entities get `mdi:lightning-bolt`
   - Applied via `SUNSPEC_TO_HA_METADATA` dictionary
   - Entities: E2_runtime, E2_7D, E2_30D

2. **Diagnostic Icons** (diagnostic entities):
   - All 51 diagnostic entities get `mdi:information-box-outline`
   - Auto-applied when `entity_category == "diagnostic"`
   - Includes: device info, configuration, status entities

**Implementation:**

- Icons stored in mapping JSON with "HA Icon" field (27th column)
- Integration sets `_attr_icon` from mapping data
- Falls back to HA default icons when not specified

## Important Patterns

### Error Handling

Use VSN client exceptions:

```python
from .abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNConnectionError,
    VSNClientError,
)
```

### Logging

Never use f-strings in logging calls:

```python
# Good
_LOGGER.debug("Device %s has %d points", device_id, len(points))

# Bad
_LOGGER.debug(f"Device {device_id} has {len(points)} points")
```

Always include context in log messages.

### Logging Best Practices (HA Integration Quality Scale)

Follow [HA Integration Quality Scale: log-when-unavailable](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/log-when-unavailable/):

**DataUpdateCoordinator** - Just raise `UpdateFailed`, don't manually log:

```python
# CORRECT - coordinator handles logging automatically
except VSNConnectionError as err:
    raise UpdateFailed(f"Connection error: {err}") from err

# WRONG - causes double logging and log spam
except VSNConnectionError as err:
    _LOGGER.warning("Connection error: %s", err)  # ← Don't do this!
    raise UpdateFailed(f"Connection error: {err}") from err
```

**ConfigEntryNotReady** - HA handles logging automatically:

```python
# CORRECT - HA logs at DEBUG level and shows in UI
except Exception as err:
    raise ConfigEntryNotReady(f"Discovery failed: {err}") from err

# WRONG - redundant logging
except Exception as err:
    _LOGGER.error("Discovery failed: %s", err)  # ← Don't do this!
    raise ConfigEntryNotReady(f"Discovery failed: {err}") from err
```

**Why this matters:**

- DataUpdateCoordinator has built-in spam prevention (only logs state changes)
- Manual logging runs on EVERY failure → 800+ log entries overnight when device is offline
- HA already logs appropriately when exceptions are raised
- Follows [HA Integration Setup Failures](https://developers.home-assistant.io/docs/integration_setup_failures) guidance

### Async/Await

All I/O must be async:

```python
# Discovery is async
discovery = await discover_vsn_device(session, base_url, username, password)

# Client methods are async
data = await client.get_normalized_data()
await client.close()
```

### Runtime Data

Use `config_entry.runtime_data` (typed):

```python
@dataclass
class RuntimeData:
    coordinator: ABBFimerPVIVSNRestCoordinator

type ABBFimerPVIVSNRestConfigEntry = ConfigEntry[RuntimeData]
```

Never use `hass.data[DOMAIN]`.

## Code Quality Standards

### Ruff Configuration

Follow `.ruff.toml` strictly. Key rules:

- No f-strings in logging (G004)
- Proper exception handling (TRY300, TRY301)
- No shadowing built-ins (A001)
- Simple if conditions (SIM222)

### Type Hints

Add type hints to all functions and class attributes:

```python
def discover_vsn_device(
    session: aiohttp.ClientSession,
    base_url: str,
    username: str = "guest",
    password: str = "",
    timeout: int = 10,
) -> DiscoveryResult:
    """Discover VSN device."""
```

## Testing

### Manual Testing

Use test scripts in `scripts/`:

- `test_vsn_client.py`: Test REST client with real VSN device
- `vsn-rest-client/vsn_rest_client.py`: Standalone client for user testing

### Test Data

Sample data in `docs/vsn-data/`:

- `vsn300-data/`: VSN300 status, livedata, feeds
- `vsn700-data/`: VSN700 status, livedata, feeds

Use this data to verify mapping and normalization.

## VSN Differences

### VSN300

**Authentication:**

- X-Digest custom scheme
- Challenge-response flow

**Data Structure:**

- Inverter model in `status["keys"]["device.modelDesc"]["value"]`
- Datalogger has `sn` point in livedata
- Firmware in `C_Vr` point for inverter
- Firmware in `fw_ver` point for datalogger

**Example Device IDs:**

- Inverter: `"077909-3G82-3112"`
- Datalogger MAC: `"a4:06:e9:7f:42:49"` → S/N: `"111033-3N16-1421"`

### VSN700

**Authentication:**

- HTTP Basic Authentication

**Data Structure:**

- Inverter model in `livedata["device_model"]`
- Datalogger has no `sn` point (empty points array)
- Firmware often not available

**Example Device IDs:**

- Inverter: `"123668-3P81-3821"`
- Datalogger MAC: `"ac:1f:0f:b0:50:b5"` → Clean: `"ac1f0fb050b5"`

## Common Tasks

## ⚠️ MANDATORY: Sensor Mapping Workflow

**🚨 CRITICAL DIRECTIVE - READ CAREFULLY:**

### The ONLY Way to Modify Sensor Attributes

**You MUST use the generator script for ALL sensor attribute changes. Period.**

There is **ONE AND ONLY ONE** source of truth for sensor mappings:

```
scripts/vsn-mapping-generator/generate_mapping.py
```

**NEVER, EVER:**
- ❌ Edit JSON mapping files directly (docs/ or custom_components/ folders)
- ❌ Edit Excel files directly
- ❌ Add sensor attribute logic to runtime code (normalizer.py, sensor.py)
- ❌ Create temporary fixes in the codebase

**Why This Rule Exists:**

1. **Single Source of Truth**: The generator script (`generate_mapping.py`) contains ALL sensor metadata in the `SUNSPEC_TO_HA_METADATA` dictionary
2. **Regeneration Safety**: When files are regenerated, manual edits to JSON/Excel are LOST
3. **Consistency**: All 258 sensors follow the same rules and patterns
4. **Version Control**: Changes to `generate_mapping.py` are tracked, reviewed, and documented

### The CORRECT Workflow for Sensor Changes

**Adding New Sensor or Modifying Existing Sensor:**

1. **Update the generator script ONLY:**
   ```bash
   # Edit: scripts/vsn-mapping-generator/generate_mapping.py
   # Add/modify entry in SUNSPEC_TO_HA_METADATA dictionary
   ```

2. **Regenerate ALL files:**
   ```bash
   # Step 1: Generate Excel from source data
   python scripts/vsn-mapping-generator/generate_mapping.py

   # Step 2: Convert Excel to JSON (creates all 3 JSON copies)
   python scripts/vsn-mapping-generator/convert_to_json.py
   ```

3. **Verify changes:**
   ```bash
   # Check that the sensor has correct attributes
   # Test with real VSN device or test data
   ```

4. **Commit generator + generated files:**
   ```bash
   git add scripts/vsn-mapping-generator/generate_mapping.py
   git add scripts/vsn-mapping-generator/output/
   git add docs/vsn-sunspec-point-mapping.*
   git add custom_components/.../data/vsn-sunspec-point-mapping.json
   git commit -m "feat: add/update sensor X with attributes Y"
   ```

### Example: Adding Precision to a Sensor

**❌ WRONG (manual edit):**
```json
// Editing custom_components/.../data/vsn-sunspec-point-mapping.json
{
  "SunSpec Normalized Name": "MyNewSensor",
  "Suggested Display Precision": 2  // ← This will be LOST on next regeneration!
}
```

**✅ CORRECT (update generator):**
```python
# Edit: scripts/vsn-mapping-generator/generate_mapping.py
# Add to SUNSPEC_TO_HA_METADATA dictionary:

SUNSPEC_TO_HA_METADATA = {
    # ... existing entries ...

    "MyNewSensor": {
        "device_class": "current",
        "state_class": "measurement",
        "unit": "A",
        "precision": 2,  # ← Source of truth!
    },
}
```

Then regenerate files.

### Where Sensor Attributes Are Defined

All sensor attributes live in `generate_mapping.py`:

| Attribute Type | Location in Generator |
|----------------|----------------------|
| Units, device_class, state_class | `SUNSPEC_TO_HA_METADATA` dictionary |
| Precision values | `SUNSPEC_TO_HA_METADATA` or auto-calculated by `_get_suggested_precision()` |
| Icons | `SUNSPEC_TO_HA_METADATA` (custom icons like `mdi:omega`) |
| Entity categories | `SUNSPEC_TO_HA_METADATA` or `DEVICE_CLASS_FIXES` |
| Display names | `DISPLAY_NAME_STANDARDIZATION` dictionary |
| Descriptions | `DESCRIPTION_IMPROVEMENTS` dictionary |

### Runtime Code Guidelines

**Runtime code (normalizer.py, sensor.py) should ONLY:**
- ✅ Apply transformations based on mapping metadata (e.g., state maps, timestamp conversion)
- ✅ Handle defensive edge cases (e.g., Wh→kWh conversion as safety net)
- ✅ Apply runtime rounding for specific sensors (documented exceptions only)

**Runtime code should NEVER:**
- ❌ Define sensor attributes (units, device_class, state_class, precision)
- ❌ Override mapping file metadata
- ❌ Contain hardcoded sensor lists for attribute assignment

**Exception**: Manual rounding in `sensor.py` is allowed for sensors that require `int()` conversion due to Home Assistant limitations, but this should be documented as a workaround, not the primary solution.

### Adding New Mapping Points (DEPRECATED - Use Generator Instead)

**⚠️ This workflow is DEPRECATED as of v1.1.7+**

The old workflow of manually editing Excel files is NO LONGER SUPPORTED. All changes must go through the generator script.

If you need to add raw data sources:
1. Add VSN API data to `scripts/vsn-mapping-generator/data/`
2. Update the generator script to process the new data
3. Regenerate all files

### Updating Existing Mappings

**Use the generator script ONLY:**

1. Edit `scripts/vsn-mapping-generator/generate_mapping.py`
2. Add/modify entry in appropriate dictionary (`SUNSPEC_TO_HA_METADATA`, `DISPLAY_NAME_STANDARDIZATION`, etc.)
3. Regenerate: `python scripts/vsn-mapping-generator/generate_mapping.py`
4. Convert: `python scripts/vsn-mapping-generator/convert_to_json.py`
5. Test changes
6. Commit generator + all generated files

### Mapping Quality Standards

- **Descriptions**: Use SunSpec specifications for standard models
- **Categories**: Proper categorization (Inverter, MPPT, Battery, Meter, System Monitoring, etc.)
- **HA Device Classes**: Use correct SensorDeviceClass (power, energy, current, voltage, etc.)
- **HA State Classes**: Use correct SensorStateClass (measurement, total, total_increasing)
- **Display Names**: User-friendly, concise, descriptive

### Release Management

**⚠️ CRITICAL PRINCIPLES:**

> **⛔ STOP: NEVER create git tags or GitHub releases without explicit user command.**
> This is a hard rule. Always stop after commit/push and wait for user instruction.

1. **Published releases are FROZEN** - Once a release is published (tagged and on GitHub), its documentation is immutable:
   - Never modify `docs/releases/vX.Y.Z.md` for a published version
   - Never change CHANGELOG.md entries for published versions

2. **Master branch = Next Release** - The master branch always represents the NEXT release:
   - All new commits go toward the next version
   - All documentation changes go to the next version's release notes
   - Version in `manifest.json` and `const.py` reflects the version being developed

3. **Version Progression** - After publishing vX.Y.Z:
   - Immediately bump to vX.Y.(Z+1) or v(X+1).0.0 or vX.(Y+1).0
   - Create new `docs/releases/vX.Y.(Z+1).md` for ongoing work
   - All changes from that point forward go to the new version's documentation

### Version Bumping Rules

> **⚠️ IMPORTANT: Do NOT bump version during a session. All changes go into the CURRENT unreleased version.**

- The version in `manifest.json` and `const.py` represents the NEXT release being prepared
- **NEVER bump version until user commands "tag and release"**
- Multiple features/fixes can be added to the same unreleased version
- Only bump to a NEW version number AFTER the current version is released

**Example workflow:**

1. Current version is 1.3.1 (unreleased, after v1.3.0 was released)
2. User asks for fix A → Add fix A to v1.3.1, commit, push
3. User asks for fix B → Add fix B to v1.3.1 (same version!), commit, push
4. User says "tag and release" → Create v1.3.1 tag and release
5. After release: Bump version to 1.3.2 for next development cycle

**Complete Release Workflow:**

See [docs/releases/README.md](docs/releases/README.md) for the detailed process.

| Step | Tool | Action |
| ---- | ---- | ------ |
| 0 | Verify | **VERIFY TRANSLATIONS**: Ensure translation files match the mapping |
| 1 | Edit/Write | Create/update release notes in `docs/releases/vX.Y.Z.md` |
| 2 | Edit | Update `CHANGELOG.md` with version summary |
| 3 | Edit | Ensure `manifest.json` and `const.py` have correct version |
| 4 | Bash | Run linting: `uvx pre-commit run --all-files` |
| 5 | `commit-commands:commit` skill | Stage and commit with proper format |
| 6 | git CLI | `git push` |
| 7 | **⏸️ STOP** | Wait for user "tag and release" command |
| 8 | **Checklist** | Display Release Readiness Checklist (see below) |
| 9 | git CLI | `git tag -a vX.Y.Z -m "Release vX.Y.Z"` |
| 10 | git CLI | `git push --tags` |
| 11 | gh CLI | `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file docs/releases/vX.Y.Z.md` |
| 12 | GitHub Actions | Validates versions match, then auto-uploads ZIP asset |
| 13 | Edit | Bump versions in `manifest.json` and `const.py` to next version |

### Release Readiness Checklist (MANDATORY)

> **⛔ When user commands "tag and release", ALWAYS display this checklist BEFORE proceeding.**

```markdown
## Release Readiness Checklist

| Item | Status |
|------|--------|
| Version in `manifest.json` | ✅ X.Y.Z |
| Version in `const.py` | ✅ X.Y.Z |
| Release notes (`docs/releases/vX.Y.Z.md`) | ✅ Created |
| CHANGELOG.md updated | ✅ Updated |
| GitHub Actions (lint/test/validate) | ✅ **PASSING** (check latest runs) |
| Working tree clean | ✅ Clean |
| Git tag | ✅ vX.Y.Z created/pushed |
| Commits since last tag | N commits since vX.Y.Z-1 |
```

Verify ALL items show ✅ before proceeding with tag creation. If any item fails, fix it first.

**Release notes content:**

- **Download badge** (MANDATORY) - Add at top of every release note file:

  ```markdown
  [![GitHub Downloads](https://img.shields.io/github/downloads/alexdelprete/ha-abb-fimer-pvi-vsn-rest/vX.Y.Z/total?style=for-the-badge)](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases/tag/vX.Y.Z)
  ```

- Include ALL changes since last stable release
- Review commits: `git log vX.Y.Z..HEAD`
- Include sections: What's Changed, Bug Fixes, Features, Breaking Changes

### Issue References in Release Notes

When a release fixes a specific GitHub issue:

- Reference the issue number in release notes (e.g., "Fixes #19")
- Thank the user who opened the issue by name and GitHub handle
- **NEVER close the issue** - the user will do it manually

### Release Documentation Structure

The project follows industry best practices for release documentation:

**Stable/Official Release Notes (e.g., v1.3.0):**

- **Scope**: ALL changes since previous stable release
- **Example**: v1.3.0 includes everything since v1.2.0
- **Purpose**: Complete picture for users upgrading from last stable
- **Sections**: Comprehensive - all fixes, features, breaking changes, dependencies

**Beta Release Notes (e.g., v1.3.0-beta.1):**

- **Scope**: Only incremental changes in this beta
- **Example**: v1.3.0-beta.2 shows only what's new since beta.1
- **Purpose**: Help beta testers focus on what to test
- **Sections**: Incremental - new fixes, new features, testing focus

### Documentation Files

- **`CHANGELOG.md`** (root) - Quick overview of all releases based on Keep a Changelog format
- **`docs/releases/`** - Detailed release notes (one file per version)
- **`docs/releases/README.md`** - Release directory guide and templates

**⚠️ IMPORTANT - Release Policy:**

**NEVER create git tags or GitHub releases automatically without explicit user instruction.**

- Tags and releases are permanent and public
- Only create them when explicitly asked by the user
- Always confirm before creating tags or releases
- Present the plan first, wait for approval
- This includes:
  - `git tag` commands
  - `gh release create` commands
  - Any automation that creates tags/releases

**Exception:** You may prepare all release materials (bump versions, update CHANGELOG, create release notes), commit changes, and push commits - but STOP before creating tags or releases unless explicitly instructed.

**After Publishing a Release:**

1. The released version's documentation is now FROZEN
2. Immediately bump version to next version (e.g., v1.0.0-beta.2 → v1.0.0-beta.3)
3. Create `docs/releases/v(next-version).md` as a stub for ongoing work
4. All subsequent changes go to CHANGELOG.md under [Unreleased] or [next-version] heading
5. All bug fixes, features, improvements documented in next version's release notes only

### Git Workflow

**Commit Messages:**

Use conventional commits:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

Always include Claude attribution:

```text
feat(discovery): implement device discovery

[Description]

🤖 Generated with Claude Code
https://claude.com/claude-code

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Branches:**

- `master`: Main development branch
- Feature branches for major work

## Configuration Parameters

From config_entry:

- `host`: IP/hostname (e.g., `"192.168.1.100"`, `"abb-vsn300.local"`)
- `username`: Auth username (default: `"guest"`)
- `password`: Auth password (default: `""`)
- `vsn_model`: Detected VSN model (`"VSN300"` or `"VSN700"`)
- `scan_interval`: Polling interval in seconds (default: 60, range: 30-600)

## Entity Unique IDs

**Config Entry:**

- Based on logger serial number: `logger_sn.lower()`
- Example: `"111033-3n16-1421"`

**Devices:**

- Identifier: `(DOMAIN, device_id)`
- Device Name: `abb_vsn_rest_{device_type}_{serial_compact}`
- Example: `abb_vsn_rest_inverter_0779093g823112`

**Sensors:**

- **Unique ID** (internal): `{device_identifier}_{point_name}`
  - Example: `abb_vsn_rest_inverter_0779093g823112_watts`
  - Format: Simplified without model

- **Entity ID** (visible): Auto-generated by HA from device + entity name
  - Example: `sensor.abb_vsn_rest_inverter_0779093g823112_ac_power`
  - Pattern: `sensor.{device_name}_{slugified_entity_name}`

**Serial Number Compacting:**

- Remove separators: `-`, `:`, `_`
- Convert to lowercase
- Examples:
  - `077909-3G82-3112` → `0779093g823112`
  - `ac:1f:0f:b0:50:b5` → `ac1f0fb050b5`
  - `111033-3N16-1421` → `1110333n161421`

## Dependencies

From `manifest.json`:

- Home Assistant core
- `aiohttp`: Async HTTP client

No external libraries for Modbus or SunSpec - we implement what we need.

### Dependency Update Checklist

**Before updating any dependency version in `manifest.json`:**

1. Verify the new version exists on PyPI: `https://pypi.org/project/PACKAGE_NAME/`
2. Check release notes for breaking changes
3. Test locally if possible

> **⚠️ IMPORTANT**: Always verify PyPI availability before committing dependency updates. We've had issues where
> upstream maintainers created GitHub releases but forgot to publish to PyPI, breaking our integration for users.

## Key Files

**Integration:**

- `__init__.py`: Entry point, setup/unload
- `config_flow.py`: UI configuration
- `coordinator.py`: Data polling
- `sensor.py`: Sensor platform
- `const.py`: Constants

**Client Library:**

- `client.py`: REST client
- `auth.py`: Authentication
- `discovery.py`: Device discovery
- `normalizer.py`: Data normalization
- `mapping_loader.py`: Loads JSON mapping and provides lookup methods
- `exceptions.py`: Custom exceptions

**Mapping Files:**

- `docs/vsn-sunspec-point-mapping.xlsx`: Source mapping (Excel with model flags)
- `docs/vsn-sunspec-point-mapping.json`: Generated mapping (docs copy)
- `custom_components/.../data/vsn-sunspec-point-mapping.json`: Runtime mapping

**Scripts:**

- `scripts/generate_mapping_excel.py`: Original script to create Excel mapping
- `scripts/convert_excel_to_json.py`: Convert Excel to JSON (current)
- `scripts/analyze_and_deduplicate_mapping.py`: Analyze and deduplicate mappings
- `scripts/apply_mapping_fixes.py`: Apply automated fixes to mappings
- `scripts/vsn-rest-client/vsn_rest_client.py`: Standalone test client
- `scripts/test_vsn_client.py`: Integration test script
- `scripts/generate-translations/generate_translations.py`: Unified translation file generator
- `scripts/generate-translations/translation_dictionaries/*.py`: Language-specific translation dictionaries

**Documentation:**

- `README.md`: User documentation
- `CLAUDE.md`: This file (dev guidelines)
- `CHANGELOG.md`: Version history
- `docs/MAPPING_FORMAT.md`: Mapping file format and workflow
- `docs/releases/`: Per-version release notes

## Don't Do

**🚨 CRITICAL - SENSOR MAPPING:**
- ❌ **NEVER edit JSON mapping files directly** (docs/ or custom_components/ folders)
- ❌ **NEVER edit Excel mapping files directly**
- ❌ **NEVER add sensor attributes to runtime code** (normalizer.py, sensor.py)
- ❌ **NEVER create temporary fixes for sensor metadata**
- ❌ **ALWAYS use the generator script** for ALL sensor changes

**Code Quality:**

- ❌ Commit without running `uvx pre-commit run --all-files` first
- ❌ Modify production code to make tests pass - fix the tests instead
- ❌ Use `hass.data[DOMAIN]` - Use `config_entry.runtime_data`
- ❌ Use f-strings in logging - Use `%s` formatting
- ❌ Shadow built-ins - Check with ruff
- ❌ Mix sync/async - All I/O must be async
- ❌ Forget to await async methods
- ❌ Use blocking calls in async context
- ❌ Create documentation files without explicit request
- ❌ Use emojis unless user requests

**GitHub Issues:**

- ❌ **NEVER close GitHub issues unless explicitly commanded by the user**
- ❌ Do not assume an issue should be closed just because a fix was committed/released
- ❌ Do not close issues automatically after creating a release that addresses them

## Do

**🚨 CRITICAL - SENSOR MAPPING:**
- ✅ **READ CLAUDE.md at the start of EVERY session**
- ✅ **ALWAYS use generator script** for sensor attribute changes
- ✅ **Edit `scripts/vsn-mapping-generator/generate_mapping.py`** to modify sensors
- ✅ **Regenerate files** after generator changes: `generate_mapping.py` then `convert_to_json.py`
- ✅ **Commit generator + generated files together**
- ✅ **Add sensor metadata to `SUNSPEC_TO_HA_METADATA` dictionary** in generator

**Best Practices:**

- ✅ Run `uvx pre-commit run --all-files` before EVERY commit
- ✅ Use discovery module for device information
- ✅ Include firmware version in device_info (not VSN model!)
- ✅ Link devices with `via_device` to create hierarchy
- ✅ Use logger serial number for stable unique IDs
- ✅ Strip colons from MAC addresses (no underscores)
- ✅ Extract model from correct location (VSN300: status, VSN700: livedata)
- ✅ Handle missing data gracefully
- ✅ Log extensively with proper context
- ✅ Test with both VSN300 and VSN700 data
- ✅ Follow Home Assistant best practices
- ✅ Get approval before creating tags/releases
- ✅ Update documentation when changing architecture
- ✅ Use `has_entity_name=True` with technical device names and `suggested_object_id` for predictable entity IDs
- ✅ Populate comprehensive sensor attributes (14+ fields)
- ✅ Follow mapping quality standards (descriptions, categories, device classes)

## Markdown Documentation Standards

All `.md` files must adhere to markdownlint rules for consistency and readability.

### Key Markdownlint Rules

**MD032 - Lists surrounded by blank lines:**

- Always add a blank line before and after lists
- Applies to both unordered (`-`) and ordered (`1.`) lists

**MD031 - Fenced code blocks surrounded by blank lines:**

- Add blank line before and after code blocks

**MD040 - Fenced code blocks should have a language:**

- Always specify language: ` ```python`, ` ```json`, ` ```yaml`, ` ```bash`, ` ```text`
- Use `text` for diagrams, plain output, or non-code content

**MD022/MD024 - Heading formatting:**

- MD022: Headings should be surrounded by blank lines
- MD024: Avoid multiple headings with same content (make them unique)

**Bold text formatting:**

- Add blank line after bold section headers (e.g., `**Responsibilities:**`)

### Example - Correct Formatting

```markdown
### Feature Description

This feature provides data normalization.

**Key Benefits:**

- Benefit 1
- Benefit 2

**Implementation:**

The implementation includes:

    ```python
    def example():
        pass
    ```

More details here.
```text
# End of markdown example
```

### Example - Incorrect Formatting

```markdown
### Feature Description
This feature provides data normalization.
**Key Benefits:**

- Benefit 1
- Benefit 2
**Implementation:**
The implementation includes:
(missing code block language)
def example():
    pass
More details here.
```

### When Creating/Updating Markdown Files

1. Always add blank lines around lists
2. Always add blank lines around code blocks
3. Always specify language for code blocks (use `text` if no language)
4. Always add blank line after bold headers
5. Make heading names unique within the file
6. Run markdownlint before committing (if available)

### Markdownlint Configuration

The project includes `.markdownlint.json` configuration:

- Line length: 120 characters (relaxed from default 80)
- Duplicate headings: Only siblings checked (allows same heading in different sections)
- HTML allowed (MD033 disabled)
- First line heading not required (MD041 disabled)

Run linting: `npx markdownlint-cli2 *.md docs/*.md`

## Related Projects

- **ha-abb-fimer-pvi-sunspec**: Direct Modbus/TCP (no datalogger)
- **ha-abb-powerone-pvi-sunspec**: Legacy v4.x (Modbus only)

This integration is the REST API variant that works through VSN dataloggers.

---

## Release History

### v1.3.0 - CI/CD Alignment & Code Quality

**Date:** January 2026

- Aligned CI/CD workflows with ha-sinapsi-alfa (lint.yml, test.yml, validate.yml, release.yml)
- Added ty type checker for faster type checking
- Removed fallback imports from client library for cleaner code
- Added comprehensive test infrastructure
- Updated Python requirement to >=3.13.2

### v1.2.0 - Sensor Mapping Overhaul

**Date:** December 2025

- Unified sensor mapping generator script
- VSN name normalization for duplicate detection
- Display name standardization (TYPE-first pattern)
- 253 unique sensor points with comprehensive metadata

### v1.1.0 - Modern Entity Naming

**Date:** November 2025

- Modern `has_entity_name=True` pattern
- Domain prefix for entity IDs
- Comprehensive sensor attributes (14+ fields)
- Aurora protocol integration for timestamps and state mapping

### v1.0.0 - First Stable Release

**Date:** October 2025

- Automatic VSN300/VSN700 detection
- Multi-device support (inverters, meters, batteries)
- SunSpec-normalized data schema
- Custom icon support
- Human-readable state translations
