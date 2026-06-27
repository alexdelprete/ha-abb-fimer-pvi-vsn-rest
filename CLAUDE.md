# Claude Code Development Guidelines

## ⚠️ CRITICAL: Read This First

**MANDATORY: At the beginning of EVERY session, you MUST:**

1. **Read this entire CLAUDE.md file** - This contains critical project context, architecture decisions, and workflow requirements
1. **Review recent git commits** - Understand what changed since last session
1. **Check the current state** - Run `git status` to see uncommitted changes

**Failure to read project documentation first leads to:**

- Violating mandatory workflows (e.g., editing JSON files directly instead of using the generator)
- Duplicating work that was already done
- Making architectural decisions that contradict established patterns
- Breaking the single source of truth principle

### Workflow Run Logs Workaround

The GitHub MCP `get_job_logs` tool is currently broken. To get workflow run logs (e.g., for test coverage):

1. Use MCP to get the run ID: `mcp__GitHub_MCP_Remote__actions_list` with `method: list_workflow_runs`
1. Use `gh` CLI to fetch logs: `gh run view <run_id> --repo owner/repo --log`
1. Filter with grep: `gh run view <run_id> --repo owner/repo --log | grep "TOTAL\|coverage"`

## ⚠️ Editing rules for this file

This CLAUDE.md has two zones:

- **Outside** the `<!-- BEGIN SHARED:repo-sync -->` / `<!-- END SHARED:repo-sync -->`
  markers: integration-specific. Edit freely.
- **Inside** the SHARED markers: auto-generated from `ha-integration-template`
  via `repo-sync.py`. Edits there get overwritten on the next sync. To change
  shared guidance, edit `templates/markers/CLAUDE_SHARED.md.j2` upstream and
  re-sync downstream.

**Before adding generic workflow guidance to this file** (lint commands, release
process, pre-commit invocations, anything that would apply to every integration):

1. Check the SHARED block first.
1. If similar guidance already lives there, do not duplicate it here — refer to
   the SHARED block instead.
1. If it doesn't yet, promote it to `CLAUDE_SHARED.md.j2` in the template repo
   and re-sync. Do not write it as a one-off in this file.

This rule prevents drift between integration-specific copies and the template
source of truth (the kind of drift that, for example, caused `uvx pre-commit`
mentions to survive a template-side change to plain `pre-commit`).

## Project Overview

This is the **ha-abb-fimer-pvi-vsn-rest** integration for Home Assistant. It provides monitoring of ABB/FIMER/Power-One
PVI inverters through VSN300 or VSN700 dataloggers via their
REST API.

**Key Features**:

- Automatic VSN300/VSN700 detection
- Multi-device support (inverters, meters, batteries)
- SunSpec-normalized data schema with Aurora protocol integration
- Modern Home Assistant entity naming pattern
- Comprehensive sensor attributes with 253 unique mapped data points
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
```text

### Key Components

#### 1. Discovery Module (`abb_fimer_vsn_rest_client/discovery.py`)

Centralized device discovery that runs during setup and configuration.

**Responsibilities:**

- Detect VSN model (VSN300 or VSN700)
- Fetch status and livedata endpoints
- Extract logger metadata (S/N, model, firmware, hostname)
- Discover all connected devices (inverters, meters, batteries)
- Handle device identification:
  - VSN300 datalogger: Extract `sn` point → `"110033-3A16-1234"`
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
    hostname: str | None        # ABB-076543-3F71-2345.local
    devices: list[DiscoveredDevice]
    status_data: dict[str, Any]
```text

#### 2. REST Client (`abb_fimer_vsn_rest_client/client.py`)

Handles communication with VSN datalogger REST API.

**Responsibilities:**

- Authenticate with VSN300 (X-Digest) or VSN700 (Basic Auth)
- Fetch `/v1/status`, `/v1/livedata`, `/v1/feeds` endpoints
- Inject `device_type` from discovery into raw livedata before normalization
- Pass raw data to normalizer
- Return normalized data

**Key Methods:**

- `connect()`: Detect VSN model and authenticate
- `get_normalized_data()`: Fetch, inject device types, and normalize data
- `update_discovered_devices()`: Sync device list and invalidate cached maps (called by coordinator after re-discovery)
- `close()`: Clean up resources

**Device Type Injection:**

The API may not include `device_type` for all devices (e.g., datalogger). The client maintains
a `_device_type_map` (dict of livedata key → device_type) built lazily from `_discovered_devices`
on first poll. This map is invalidated when `update_discovered_devices()` is called after
re-discovery, ensuring the client stays in sync with the coordinator.

#### 3. Authentication (`abb_fimer_vsn_rest_client/auth.py`)

VSN-specific authentication schemes.

**VSN300:**

- Custom HTTP Digest with `X-Digest` header
- Process:
  1. Fetch challenge from `/v1/dgst`
  1. Compute SHA-256 digest: `user:realm:password`
  1. Compute final: `method:uri:digest`
  1. Add header: `Authorization: X-Digest {final_digest}`

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
```text

**Key Mapping Columns (HA-Prefixed):**

- `HA Unit of Measurement`: Home Assistant unit (SensorDeviceClass)
- `HA State Class`: Home Assistant state class (SensorStateClass)
- `HA Device Class`: Home Assistant device class
- `HA Display Name`: User-facing display name

**Mapping Workflow:**

See the [Full Regeneration Pipeline](#full-regeneration-pipeline) and [docs/MAPPING_FORMAT.md](docs/MAPPING_FORMAT.md) for details.

#### 5. Coordinator (`coordinator.py`)

Home Assistant DataUpdateCoordinator for managing polling.

**Responsibilities:**

- Periodic data fetching (default: 60s)
- Error handling and retries
- Store discovery result
- Distribute data to sensors
- Periodic re-discovery of missing known devices
- Idempotency check: detect unknown devices in data and trigger reload

**Key Attributes:**

- `client`: VSN REST client instance
- `vsn_model`: VSN300 or VSN700
- `discovery_result`: Full discovery data
- `discovered_devices`: List of DiscoveredDevice
- `_missing_devices`: Set of known device IDs not found during last discovery
- `_reload_scheduled`: Flag to prevent multiple concurrent reloads

**Re-discovery Flow (in `_async_update_data`):**

After each successful data fetch, two checks run:

1. **Missing known devices**: If `_missing_devices` is non-empty, call `discover_vsn_device()` to check if they're back. On full recovery, schedule `config_entry.async_reload()`.
2. **Unknown devices in data**: Compare data device IDs against `known_devices` in `config_entry.data`. If unknown devices found, schedule reload for idempotent device creation.

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
1. Run discovery (detect model, find devices)
1. Set unique_id to logger serial number
1. Store VSN model in config_entry

#### 7. Sensor Platform (`sensor.py`)

Creates Home Assistant sensor entities using modern naming pattern.

**Entity Naming Pattern (has_entity_name=True):**

- **Device Name**: Technical format for predictable entity IDs (v1.0.0-beta.25+)

  - Format: `{DOMAIN}_{device_type}_{serial_compact}`
  - Uses DOMAIN constant from manifest.json: `abb_fimer_pvi_vsn_rest`
  - Example: `abb_fimer_pvi_vsn_rest_inverter_0765433f712345`
  - Device type simplified: `inverter`, `datalogger`, `meter`, `battery`
  - Serial compacted: remove `-`, `:`, `_` and lowercase

- **Entity Name**: Standardized display name from mapping (v1.0.0-beta.22+)

  - Pattern: [Type] [AC/DC] - [Details] - [Time Period]
  - Examples: "Power AC", "Energy AC - Produced Lifetime", "Temperature - Cabinet"
  - From `HA Display Name` field in mapping
  - Displayed as entity name on device page

- **translation_key**: Maps to translated display name (v1.4.1+)

  - Set to `point_name` (e.g., "watts", "wlan0_essid")
  - HA looks up `translations/{lang}.json` → `entity.sensor.{translation_key}.name`
  - The translated name drives entity ID generation

- **Entity ID** (auto-generated by HA from translated display name):

  - Format: `sensor.{slugify(device_name)}_{slugify(translated_display_name)}`
  - Example: `sensor.abb_fimer_inverter_power_ac` (device "ABB FIMER Inverter" + translation "Power AC")
  - **Changed in v1.4.1**: Entity IDs now derived from translated names, not point names

- **Unique ID**: Stable identifier (v1.0.0-beta.22+)

  - Format: `{domain}_{device_type}_{serial_compact}_{point_name}`
  - Example: `abb_fimer_pvi_vsn_rest_inverter_0765433f712345_wlan0_essid`
  - Never changes once set

**Sensor Attributes (Comprehensive):**

All sensors include rich metadata attributes:

```python
{
    # Identity
    "device_id": "076543-3F71-2345",
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
```text

**Device Info:**

All HA device info fields populated from discovery:

- `identifiers`: `(DOMAIN, device_id)`
- `name`: Device identifier (e.g., `"abb_vsn_rest_inverter_0765433f712345"`)
- `manufacturer`: From `C_Mn` point
- `model`: Device model
- `serial_number`: Device S/N or clean MAC
- `sw_version`: Firmware version from `C_Vr` or `fw_ver`
- `hw_version`: Hardware version (if available)
- `configuration_url`: Datalogger hostname (datalogger only)
- `via_device`: Link to datalogger (for inverters/meters)

## Key Architectural Decisions

### Known Devices Persistence & Partial Discovery (v1.4.6)

**Decision**: Persist expected devices in `config_entry.data["known_devices"]` and treat missing devices as temporary unavailability, not orphans to delete.

**Problem**: When HA starts before sunrise, the inverter is off and not in the `/v1/livedata` response. Discovery only finds the datalogger. The old `_cleanup_orphaned_devices()` then deleted the inverter device and all its entities. The coordinator never re-discovered, requiring manual reload.

**Implementation**:

- `config_entry.data["known_devices"]`: Persisted list of `{device_id, device_type, is_datalogger}` dicts
- On startup: `_sync_known_devices()` merges discovered devices into known list (union — only adds, never auto-removes) and updates stale `device_type` values from discovery
- `_detect_missing_devices()` identifies known non-datalogger devices absent from discovery
- If missing: create `WARNING`-level repair notification
- Coordinator `_attempt_rediscovery()` runs `discover_vsn_device()` every poll cycle when devices are missing
- On recovery: `_update_discovery_state()` syncs coordinator AND client (via `client.update_discovered_devices()` which invalidates `_device_type_map`)
- `_handle_full_recovery()`: clear repair notification, `async_reload()` to create entities
- `_handle_partial_recovery()`: update repair issue with remaining missing devices
- Idempotency check in `_async_update_data()`: if data contains device IDs not in `known_devices`, trigger reload
- Device deletion via HA UI: always allowed, removes from `known_devices`. If device still physically exists, next discovery re-adds it
- Config entry migration v7→v8 populates `known_devices` from existing device registry

**Key Files**:

- `__init__.py`: `_sync_known_devices()`, `_detect_missing_devices()`, migration v8
- `coordinator.py`: `_attempt_rediscovery()`, `_update_discovery_state()`, `_sync_known_devices()`, idempotency check
- `client.py`: `update_discovered_devices()`, `_ensure_device_type_map()`, `_inject_device_types()`
- `repairs.py`: `create_partial_discovery_issue()`, `delete_partial_discovery_issue()`
- `const.py`: `CONF_KNOWN_DEVICES`

### Energy Sensor State Class & Accumulation Mode (v1.5.1)

**Decision**: Introduce `accumulation_mode` attribute to drive `state_class` derivation, separate from `sensor_scope` which drives the stale-value guard.

**Problem**: 32 periodic energy sensors (DayWH, WeekWH, MonthWH, YearWH, all `_7D`/`_30D`/`_1Y` series) had `state_class: "total"` instead of `"total_increasing"`. Per [HA developer docs](https://developers.home-assistant.io/docs/core/entity/sensor/#state-class-sensorstateclasstotal), `total` calculates negative deltas when values drop (e.g., 5kWh → 0 = -5kWh), causing negative solar production on the Energy Dashboard. These sensors match HA's Scenario 2: "Resets to zero, increases only" → `total_increasing`.

**Separation of Concerns — Two Independent Attributes:**

| Attribute | Question it Answers | Values | Used by |
|-----------|-------------------|--------|---------|
| `accumulation_mode` | When the value drops, is it a reset or a real decrease? | `monotonic`, `bidirectional` | Generator → derives `state_class` |
| `sensor_scope` | When (if ever) does it reset? | `lifetime`, `runtime`, `periodic` | `sensor.py` stale-value guard |

- `accumulation_mode: "monotonic"` → a drop is a **meter reset, not a real decrease** → `state_class: "total_increasing"`
- `accumulation_mode: "bidirectional"` → value can go up and down for real (net metering) → `state_class: "total"`
- `sensor_scope: "lifetime"` → **never resets** → guard rejects decreasing values
- `sensor_scope: "runtime"` → resets on reboot → guard allows it
- `sensor_scope: "periodic"` → resets at period boundary → guard allows it

> **"monotonic" does NOT mean "never decreases."** It means "increases *within its reset
> scope*; drops are resets." Of the 72 `monotonic` sensors, only the **21 `lifetime`** ones
> never reset — the **35 `periodic` + 16 `runtime`** ones legitimately drop to ~0 at their
> scope boundary. The only attribute that means "never decreases" is `sensor_scope ==
> "lifetime"`.
>
> **Critical (issue #61):** the stale-value guard MUST gate on `sensor_scope == "lifetime"`,
> never on `accumulation_mode == "monotonic"`. Gating on `monotonic` also caught the
> periodic/runtime counters and suppressed their normal reset to ~0 forever, stranding them
> on `unknown`.

**Why Not Derive state_class from sensor_scope?** Because they answer different questions. All three scopes happen to be `total_increasing` (monotonically increasing within their scope), but that's a coincidence of our current sensor set. A future net metering sensor could be `lifetime` scope (never resets) but `bidirectional` accumulation (value goes up and down).

**Generator Rule** (in `create_row_with_model_flags`):

```python
accumulation_mode = metadata.get("accumulation_mode")
if accumulation_mode == "monotonic":
    row["state_class"] = "total_increasing"
elif accumulation_mode == "bidirectional":
    row["state_class"] = "total"
```text

**Current State**: All 72 accumulating sensors are `monotonic` → `total_increasing` (21 `lifetime`, 35 `periodic`, 16 `runtime`). Only the 21 `lifetime` sensors never reset; the other 51 reset at reboot/period boundary. Zero `bidirectional` sensors exist (no net metering support yet). Zero sensors have `state_class: "total"`.

**Key Files**:

- `generate_mapping.py`: `SUNSPEC_TO_HA_METADATA` entries with `accumulation_mode` and `sensor_scope`
- `mapping_loader.py`: `PointMapping` dataclass with `accumulation_mode` field
- `sensor.py`: Reads `sensor_scope` for stale-value guard (unchanged)

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
1. Leakage Current Inverter: `ILeakDcAc` (VSN300, mA) vs `IleakInv` (VSN700, A) - **CRITICAL 1000x unit mismatch**
1. Leakage Current DC: `ILeakDcDc` (VSN300, mA) vs `IleakDC` (VSN700, A) - **CRITICAL 1000x unit mismatch**
1. Ground Voltage: `VGnd` (VSN300) vs `Vgnd` (VSN700) - capitalization only
1. Battery SoC: `Soc` (VSN300) vs `TSoc` (VSN700) - naming convention

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
```text

**Runtime Value Conversion** (normalizer.py):

```python
# VSN700 leakage current sensors report in A, standardize to mA
A_TO_MA_POINTS = {"IleakInv", "IleakDC"}

if vsn_model == "VSN700" and point_name in A_TO_MA_POINTS:
    point_value = point_value * 1000  # A → mA
```text

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

**Decision**: Use `has_entity_name=True` with `translation_key` for entity ID generation (v1.4.1+).

**How HA Core generates entity IDs** (verified against HA core source code):

- `_attr_suggested_object_id` does NOT exist in HA core. The `suggested_object_id` property is a computed `@property` that returns the entity's translated name. It is NOT in the `CACHED_PROPERTIES_WITH_ATTR_` set, so setting `self._attr_suggested_object_id = ...` does nothing.
- When `has_entity_name=True` and `translation_key` is set, HA looks up the translated name from `translations/{lang}.json` → `entity.sensor.{translation_key}.name`
- Entity ID = `sensor.{slugify(device_name)}_{slugify(translated_name)}`
- This means **changing display names in translations changes entity IDs**

**Implementation** (v1.4.1+):

- `has_entity_name = True` ✅
- `translation_key = point_name` (e.g., "watts" → looks up "Power AC" in translations)
- `_attr_name` set as fallback, but translations take precedence when available
- Device name: Friendly format from `format_device_name()` (e.g., "ABB FIMER Inverter")
- Entity ID: `sensor.abb_fimer_inverter_power_ac` (device name + translated display name)
- Result: Human-readable entity IDs, friendly names, translated in user's language

**Critical Note**: `_attr_suggested_object_id` is dead code — HA core ignores it. Always use `translation_key` for entity ID control.

### Simplified Entity IDs (No Model)

**Decision**: Remove model from entity IDs.

**Rationale**:

- Model information still available in attributes
- Shorter, cleaner entity IDs
- One device rarely has multiple models for same point
- Model info: `sunspec_model` attribute

**Implementation**:

- Old: `abb_vsn_rest_inverter_0765433f712345_m103_watts`
- New: `abb_vsn_rest_inverter_0765433f712345_watts`
- Unique ID: `abb_vsn_rest_inverter_0765433f712345_watts`

### Entity ID Standardization with Domain Prefix (v1.0.0-beta.22)

**Decision**: Add domain prefix to all entity IDs and align unique_id format.

**Rationale**:

- **Namespace Isolation**: Prevents conflicts with other integrations that might use similar entity naming patterns
- **Clear Ownership**: Immediately obvious which integration owns each entity
- **Consistency**: Aligns unique_id and entity_id formats for better maintainability
- **Dynamic Source**: Uses DOMAIN constant from manifest.json instead of hardcoded values

**Implementation**:

**Before (beta.21)**:

- Entity ID: `sensor.inverter_0765433f712345_ac_power`
- Unique ID: `abb_vsn_rest_inverter_0765433f712345_ac_power`
- Issue: No domain prefix in entity_id, inconsistent formats

**After (beta.22)**:

- Entity ID: `sensor.abb_fimer_pvi_vsn_rest_inverter_0765433f712345_ac_power`
- Unique ID: `abb_fimer_pvi_vsn_rest_inverter_0765433f712345_ac_power`
- Both use DOMAIN constant: `abb_fimer_pvi_vsn_rest`

**Code Changes**:

```python
# sensor.py - Entity naming configuration (v1.4.1+)
self._attr_has_entity_name = True

# Device identifier (for unique_id)
device_identifier = f"{DOMAIN}_{device_type_simple}_{device_sn_compact}"

# Unique ID (stable identifier - never changes)
unique_id = f"{device_identifier}_{point_name}"
self._attr_unique_id = unique_id

# Translation key (drives entity ID generation via translated display name)
self._attr_translation_key = point_name

# Entity name (fallback when translation not available)
self._attr_name = point_data.get("ha_display_name", point_data.get("label", point_name))

# Device name (friendly format for UI)
device_name = format_device_name(
    manufacturer=manufacturer,
    device_type_simple=self._device_type_simple,
    device_model=device_model,
    device_sn_original=self._device_id,
)
# Result: "ABB Datalogger VSN300 (110033-3A16-1234)"
# Entity ID: sensor.abb_datalogger_vsn300_110033_3a16_1234_firmware_version
#   (derived from slugify(device_name) + slugify(translated_display_name))
# Friendly Name: "ABB Datalogger VSN300 (110033-3A16-1234) Firmware Version"
```text

**Breaking Change (v1.4.1)**: Removed category prefixes from 57 display names (e.g., "Inverter - Type" → "Type"). Entity IDs changed accordingly. One-time config entry migration (version 1→2) auto-renames existing entity IDs.

**Breaking Change (beta.26)**: Switched to friendly device names for beautiful UI. Entity IDs changed to slugified friendly format.

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
```text

Updated `apply_display_name_corrections()` to apply both corrections and standardization in sequence.

**Breaking Change (v1.4.1)**: Removed category prefixes from 57 display names ("Inverter - ", "Device - ", "System - ", "Battery - ", "Grid - "). Since entity IDs are derived from translated display names, this changed entity IDs. One-time config entry migration (version 1→2) auto-renames existing entity IDs.

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
```text

**Implementation (sensor.py):**

- SysTime entity uses `device_class="timestamp"`
- Raw value from API is in Aurora epoch (seconds since Jan 1, 2000)
- Conversion: `datetime.fromtimestamp(value + AURORA_EPOCH_OFFSET, tz=tz)`
- Result: Correct datetime display in Home Assistant

**2. State Mapping (const.py):**

Status entities with integer state codes are translated to human-readable text:

| State Map | Description | States | Entities | |-----------|-------------|--------|----------| | `GLOBAL_STATE_MAP` | System-wide operational states | 42 | GlobState | |
`DCDC_STATE_MAP` | DC-DC converter states | 20 | DC1State, DC2State | | `INVERTER_STATE_MAP` | Inverter operational states | 38 | InvState | | `ALARM_STATE_MAP` | Alarm and error
codes | 65 | AlarmState, AlarmSt |

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
```text

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

1. **Diagnostic Icons** (diagnostic entities):

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
```text

### Logging

Never use f-strings in logging calls:

```python
# Good
_LOGGER.debug("Device %s has %d points", device_id, len(points))

# Bad
_LOGGER.debug(f"Device {device_id} has {len(points)} points")
```text

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
```text

**ConfigEntryNotReady** - HA handles logging automatically:

```python
# CORRECT - HA logs at DEBUG level and shows in UI
except Exception as err:
    raise ConfigEntryNotReady(f"Discovery failed: {err}") from err

# WRONG - redundant logging
except Exception as err:
    _LOGGER.error("Discovery failed: %s", err)  # ← Don't do this!
    raise ConfigEntryNotReady(f"Discovery failed: {err}") from err
```text

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
```text

### Runtime Data

Use `config_entry.runtime_data` (typed):

```python
@dataclass
class RuntimeData:
    coordinator: ABBFimerPVIVSNRestCoordinator

type ABBFimerPVIVSNRestConfigEntry = ConfigEntry[RuntimeData]
```text

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
```text

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

- Inverter: `"076543-3F71-2345"`
- Datalogger MAC: `"a8:03:e7:4c:31:5a"` → S/N: `"110033-3A16-1234"`

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

```text
scripts/vsn-mapping-generator/generate_mapping.py
```text

**NEVER, EVER:**

- ❌ Edit JSON mapping files directly (docs/ or custom_components/ folders)
- ❌ Edit Excel files directly
- ❌ Add sensor attribute logic to runtime code (normalizer.py, sensor.py)
- ❌ Create temporary fixes in the codebase

**Why This Rule Exists:**

1. **Single Source of Truth**: The generator script (`generate_mapping.py`) contains ALL sensor metadata in the `SUNSPEC_TO_HA_METADATA` dictionary
1. **Regeneration Safety**: When files are regenerated, manual edits to JSON/Excel are LOST
1. **Consistency**: All 253 sensors follow the same rules and patterns
1. **Version Control**: Changes to `generate_mapping.py` are tracked, reviewed, and documented

### The CORRECT Workflow for Sensor Changes

**Adding New Sensor or Modifying Existing Sensor:**

1. **Update the generator script ONLY:**

   ```bash
   # Edit: scripts/vsn-mapping-generator/generate_mapping.py
   # Add/modify entry in SUNSPEC_TO_HA_METADATA dictionary
   ```

1. **Regenerate ALL files** (see [Full Regeneration Pipeline](#full-regeneration-pipeline)):

   ```bash
   # Step 1: Generate Excel from source data
   python scripts/vsn-mapping-generator/generate_mapping.py

   # Step 2: Convert Excel to JSON + update translations/en.json sensor entries
   python scripts/vsn-mapping-generator/convert_to_json.py

   # Step 3: Regenerate all translation files (en.json + 9 languages)
   python scripts/generate-translations/generate_translations.py --all
   ```

1. **Verify changes:**

   ```bash
   # Check that the sensor has correct attributes
   # Test with real VSN device or test data
   ```

1. **Commit generator + generated files:**

   ```bash
   git add scripts/vsn-mapping-generator/generate_mapping.py
   git add scripts/vsn-mapping-generator/output/
   git add custom_components/.../data/vsn-sunspec-point-mapping.json
   git add custom_components/.../translations/en.json
   git add custom_components/.../translations/
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
```text

**✅ CORRECT (update generator):**

```python
# Edit: scripts/vsn-mapping-generator/generate_mapping.py
# Add to SUNSPEC_TO_HA_METADATA dictionary:

SUNSPEC_TO_HA_METADATA = {
    # ... existing entries ...

    # Instantaneous measurement (power, voltage, current, etc.)
    "MyNewSensor": {
        "device_class": "current",
        "state_class": "measurement",
        "unit": "A",
        "precision": 2,
    },
    # Accumulating energy sensor (use accumulation_mode, NOT state_class)
    "MyEnergySensor": {
        "device_class": "energy",
        "unit": "Wh",
        "accumulation_mode": "monotonic",  # → state_class derived as "total_increasing"
        "sensor_scope": "periodic",  # → stale-value guard allows resets
    },
}
```text

Then regenerate files.

### Where Sensor Attributes Are Defined

All sensor attributes live in `generate_mapping.py`:

| Attribute Type | Location in Generator |
|----------------|----------------------|
| Units, device_class | `SUNSPEC_TO_HA_METADATA` dictionary |
| state_class (energy sensors) | Derived from `accumulation_mode` in `SUNSPEC_TO_HA_METADATA` |
| state_class (other sensors) | Explicit `state_class` in `SUNSPEC_TO_HA_METADATA` |
| accumulation_mode, sensor_scope | `SUNSPEC_TO_HA_METADATA` dictionary |
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

**Exception**: Manual rounding in `sensor.py` is allowed for sensors that require `int()` conversion due to Home Assistant limitations, but this should be documented as a
workaround, not the primary solution.

### Adding New Mapping Points (DEPRECATED - Use Generator Instead)

**⚠️ This workflow is DEPRECATED as of v1.1.7+**

The old workflow of manually editing Excel files is NO LONGER SUPPORTED. All changes must go through the generator script.

If you need to add raw data sources:

1. Add VSN API data to `scripts/vsn-mapping-generator/data/`
1. Update the generator script to process the new data
1. Regenerate all files

### Updating Existing Mappings

**Use the generator script ONLY:**

1. Edit `scripts/vsn-mapping-generator/generate_mapping.py`
1. Add/modify entry in appropriate dictionary (`SUNSPEC_TO_HA_METADATA`, `DISPLAY_NAME_STANDARDIZATION`, etc.)
1. Run the [Full Regeneration Pipeline](#full-regeneration-pipeline) (all 3 steps)
1. Test changes
1. Commit generator + all generated files

### Full Regeneration Pipeline

The mapping/translation pipeline has **3 mandatory steps** that must always run together. Never run just one step — the outputs are chained.

```text
generate_mapping.py → Excel → convert_to_json.py → JSON + translations/en.json → generate_translations.py → 9 languages
```

Step 1 — Generate Excel from generator script (source of truth):

```bash
python scripts/vsn-mapping-generator/generate_mapping.py
```

- Reads VSN data sources + `SUNSPEC_TO_HA_METADATA`, `DESCRIPTION_IMPROVEMENTS`, `DISPLAY_NAME_STANDARDIZATION` dicts
- Outputs: `scripts/vsn-mapping-generator/output/vsn-sunspec-point-mapping.xlsx`

Step 2 — Convert Excel to JSON + sync translations/en.json:

```bash
python scripts/vsn-mapping-generator/convert_to_json.py
```

- Reads Excel, outputs JSON mapping to 2 locations:
  - `scripts/vsn-mapping-generator/output/vsn-sunspec-point-mapping.json`
  - `custom_components/.../data/vsn-sunspec-point-mapping.json` (runtime copy)
- Auto-updates `custom_components/.../translations/en.json` sensor entries from `HA Display Name` field
- Preserves `config`/`options` sections in `translations/en.json` (only replaces `entity.sensor`)

Step 3 — Regenerate all translations:

```bash
python scripts/generate-translations/generate_translations.py --all
```

- Reads `translations/en.json` (canonical English source)
- - Translates sensor names + options for 9 languages using `translation_dictionaries/*.py`

Generated files (commit all together):

| File                                                          | Generated By |
| ------------------------------------------------------------- | ------------ |
| `scripts/.../output/*.xlsx`                                   | Step 1       |
| `scripts/.../output/*.json`                                   | Step 2       |
| `custom_components/.../data/vsn-sunspec-point-mapping.json`   | Step 2       |
| `custom_components/.../translations/en.json` (sensor entries) | Step 2       |
| `custom_components/.../translations/en.json`                  | Step 3       |
| `custom_components/.../translations/{de,es,...,sv}.json`      | Step 3       |

NEVER manually edit any of these generated files — changes will be overwritten on next pipeline run.

### Mapping Quality Standards

- **Descriptions**: Use SunSpec specifications for standard models
- **Categories**: Proper categorization (Inverter, MPPT, Battery, Meter, System Monitoring, etc.)
- **HA Device Classes**: Use correct SensorDeviceClass (power, energy, current, voltage, etc.)
- **HA State Classes**: Use `accumulation_mode` for energy sensors (never hardcode
  `state_class` directly). Use `measurement` for instantaneous readings
- **Display Names**: User-friendly, concise, descriptive

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

**Exception:** You may prepare all release materials (bump versions, update CHANGELOG, create release notes), commit
changes, and push commits - but STOP before creating tags or
releases unless explicitly instructed.

**After Publishing a Release:**

1. The released version's documentation is now FROZEN
1. Immediately bump version to next version (e.g., v1.0.0-beta.2 → v1.0.0-beta.3)
1. Create `docs/releases/v(next-version).md` as a stub for ongoing work
1. All subsequent changes go to CHANGELOG.md under [Unreleased] or [next-version] heading
1. All bug fixes, features, improvements documented in next version's release notes only

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
```text

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
- `known_devices`: Persisted list of known devices (auto-managed, not user-configurable)

## Entity Unique IDs

**Config Entry:**

- Based on logger serial number: `logger_sn.lower()`
- Example: `"110033-3a16-1421"`

**Devices:**

- Identifier: `(DOMAIN, device_id)`
- Device Name: `abb_vsn_rest_{device_type}_{serial_compact}`
- Example: `abb_vsn_rest_inverter_0765433f712345`

**Sensors:**

- **Unique ID** (internal): `{device_identifier}_{point_name}`

  - Example: `abb_vsn_rest_inverter_0765433f712345_watts`
  - Format: Simplified without model

- **Entity ID** (visible): Auto-generated by HA from device + entity name

  - Example: `sensor.abb_vsn_rest_inverter_0765433f712345_ac_power`
  - Pattern: `sensor.{device_name}_{slugified_entity_name}`

**Serial Number Compacting:**

- Remove separators: `-`, `:`, `_`
- Convert to lowercase
- Examples:
  - `076543-3F71-2345` → `0765433f712345`
  - `ac:1f:0f:b0:50:b5` → `ac1f0fb050b5`
  - `110033-3A16-1234` → `1100333a161234`

## Dependencies

From `manifest.json`:

- Home Assistant core
- `aiohttp`: Async HTTP client

No external libraries for Modbus or SunSpec - we implement what we need.

### Dependency Update Checklist

**Before updating any dependency version in `manifest.json`:**

1. Verify the new version exists on PyPI: `https://pypi.org/project/PACKAGE_NAME/`
1. Check release notes for breaking changes
1. Test locally if possible

> **⚠️ IMPORTANT**: Always verify PyPI availability before committing dependency updates. We've had issues where upstream maintainers created GitHub releases but forgot to publish
> to PyPI, breaking our integration for users.

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

## Project-Specific Don't Do

In addition to the shared Don'ts:

**SENSOR MAPPING:**

- NEVER edit JSON mapping files directly (docs/ or custom_components/ folders)
- NEVER edit Excel mapping files directly
- NEVER add sensor attributes to runtime code (normalizer.py, sensor.py)
- NEVER create temporary fixes for sensor metadata
- ALWAYS use the generator script for ALL sensor changes

**Additional:**

- Create documentation files without explicit request
- Use emojis unless user requests

## Project-Specific Do

In addition to the shared Do's:

**SENSOR MAPPING:**

- ALWAYS use generator script for sensor attribute changes
- Edit `scripts/vsn-mapping-generator/generate_mapping.py` to modify sensors
- Regenerate files after generator changes
- Commit generator + generated files together
- Add sensor metadata to `SUNSPEC_TO_HA_METADATA` dictionary in generator

**Best Practices:**

- Use discovery module for device information
- Include firmware version in device_info (not VSN model!)
- Link devices with `via_device` to create hierarchy
- Use logger serial number for stable unique IDs
- Strip colons from MAC addresses (no underscores)
- Extract model from correct location (VSN300: status, VSN700: livedata)
- Test with both VSN300 and VSN700 data
- Use `has_entity_name=True` with `translation_key` for entity ID generation
- Populate comprehensive sensor attributes (14+ fields)
- Follow mapping quality standards (descriptions, categories, device classes)
- Update documentation when changing architecture

## Markdown Documentation Standards

All `.md` files must adhere to markdownlint rules for consistency and readability.

### Key Markdownlint Rules

**MD032 - Lists surrounded by blank lines:**

- Always add a blank line before and after lists
- Applies to both unordered (`-`) and ordered (`1.`) lists

**MD031 - Fenced code blocks surrounded by blank lines:**

- Add blank line before and after code blocks

**MD040 - Fenced code blocks should have a language:**

- Always specify language: ````  ```python ````, ````  ```json ````, ````  ```yaml ````, ````  ```bash ````, ````  ```text ````
- Use `text` for diagrams, plain output, or non-code content

**MD022/MD024 - Heading formatting:**

- MD022: Headings should be surrounded by blank lines
- MD024: Avoid multiple headings with same content (make them unique)

**Bold text formatting:**

- Add blank line after bold section headers (e.g., `**Responsibilities:**`)

### Example - Correct Formatting

````markdown
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
    ```text

More details here.
```text
# End of markdown example
````

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
```text

### When Creating/Updating Markdown Files

1. Always add blank lines around lists
1. Always add blank lines around code blocks
1. Always specify language for code blocks (use `text` if no language)
1. Always add blank line after bold headers
1. Make heading names unique within the file
1. Run markdownlint before committing (if available)

### Markdownlint Configuration

The project includes `.markdownlint.json` configuration:

- Line length: 120 characters (relaxed from default 80)
- Duplicate headings: Only siblings checked (allows same heading in different sections)
- HTML allowed (MD033 disabled)
- First line heading not required (MD041 disabled)

Run linting: `npx markdownlint-cli2 *.md docs/*.md`

<!-- BEGIN SHARED:repo-sync -->
<!-- Synced by repo-sync on 2026-06-27 -->

<!--
==============================================================================
⚠️  TEMPLATE-MANAGED ZONE — DO NOT EDIT BETWEEN BEGIN SHARED AND END SHARED.

This entire region is auto-generated from
ha-integration-template/templates/markers/CLAUDE_SHARED.md.j2 via
`repo-sync.py`. Edits between the marker lines are silently overwritten
on the next sync.

To change shared guidance:
  1. Edit CLAUDE_SHARED.md.j2 in ha-integration-template
  2. Sync downstream: `python repo-sync.py sync <consumer>`

Integration-specific guidance belongs OUTSIDE the markers (above
BEGIN SHARED or below END SHARED).
==============================================================================
-->

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

Benefits over `gh` CLI:

- Direct API access without shell escaping issues
- Structured JSON responses
- Better error handling
- No subprocess overhead

## CI Workflow Status and Logs

> **IMPORTANT**: Always use `gh` CLI for CI workflow status and logs — it's more efficient than GitHub MCP.

The project has 3 CI workflows: **Lint**, **Tests**, and **Validate**.

**List recent workflow runs:**

```bash
gh run list --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --limit 5
```

**Get workflow status for a specific run:**

```bash
gh run view <run_id> --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest
```

**Get test coverage from Tests workflow logs:**

```bash
gh run view <run_id> --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --log 2>&1 | grep "TOTAL"
```

**Quick one-liner to get latest Tests run coverage:**

```bash
# Get latest Tests run ID and fetch coverage
gh run list --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --limit 5 | grep Tests
# Then use the run ID from the output
gh run view <run_id> --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --log 2>&1 | grep "TOTAL"
```

## Coding Standards

### Data Storage Pattern

**DO use `runtime_data`** (modern pattern):

```python
entry.runtime_data = MyData(device_name=name)
```

**DO NOT use `hass.data[DOMAIN]`** (deprecated pattern)

### Translations (Custom Integrations)

Per [HA developer docs](https://developers.home-assistant.io/docs/internationalization/custom_integration/):

- **DO use `translations/en.json`** as the source of truth for English strings
- **DO NOT create `strings.json`** — it is a Core-only build-time feature and is ignored by custom integrations
- All translation files go in `translations/<lang>.json` (e.g., `en.json`, `de.json`, `it.json`)

### Logging

Use structured logging:

```python
_LOGGER.debug("Sensor %s subscribed to %s", key, topic)
```

**DO NOT** use f-strings in logger calls (deferred formatting is more efficient)

Use centralized logging helpers from `helpers.py` when available:

- `log_debug(logger, context, message, **kwargs)`
- `log_info(logger, context, message, **kwargs)`
- `log_warning(logger, context, message, **kwargs)`
- `log_error(logger, context, message, **kwargs)`

Always include context parameter (function name). Format: `(function_name) [key=value]: message`

**Never log manually what HA logs automatically:**

- **DataUpdateCoordinator**: Just raise `UpdateFailed` — HA handles logging automatically
- **ConfigEntryNotReady**: HA logs automatically — don't log manually
- This prevents log spam during extended outages

### Error Handling

- Use custom exceptions (not `return False`) for proper entity availability tracking
- Raise exceptions in the API layer and let the coordinator handle retries
- Define integration-specific exceptions (e.g., `ConnectionError`, `DataError`)

### Type Hints

Always use type hints for function signatures.

### Async/Await Conventions

- All coordinator methods are async
- API methods use async/await properly
- Config entry methods follow HA conventions:
  - `add_update_listener()` — sync
  - `async_on_unload()` — sync (despite the name)
  - `async_forward_entry_setups()` — async
  - `async_unload_platforms()` — async
- Never use blocking calls in async context

## Configuration Best Practices

Following HA best practices, configuration is split between `data` (initial config) and `options` (runtime tuning):

### config_entry.data (changed via Reconfigure flow)

Connection and identity parameters: name, host, port, device ID, etc.

### config_entry.options (changed via Options flow)

Runtime tuning parameters: scan_interval, timeout, etc. Use OptionsFlowWithReload for auto-reload.

### Config Flow Patterns

- Use `vol.Clamp()` for numeric inputs with min/max bounds (better UX than validation errors)
- Use `async_update_reload_and_abort()` for reconfigure flows
- Implement config entry migration (`async_migrate_entry()`) when changing config schema versions

## Entity and Device Patterns

### Device Registry

- Device identifier tuple: `(DOMAIN, unique_id)` where `unique_id` is MAC address, serial number, or similar
- Use `DeviceInfo` with manufacturer, model, sw_version, and configuration_url
- Changing host/IP should not affect entity IDs or historical data

### Entity Unique IDs

- Sensor unique_id pattern: `{device_unique_id}_{sensor_key}`
- Use stable identifiers (MAC address, serial number) — not connection parameters (IP, hostname)
- Config entry type alias: `type MyConfigEntry = ConfigEntry[RuntimeData]`

## Python Version & HA Baseline

These repos are standardized on the **Python 3.14+** toolchain:

- `pyproject.toml`: `requires-python = ">=3.14.2"` (matches Home Assistant
  core's own floor)
- `[tool.ruff]`: `target-version = "py314"`
- Minimum supported Home Assistant core: **2026.3.0** — the
  first HA release requiring Python 3.14.2. `hacs.json` is rendered from
  the same value, so HACS users on older HA don't see updates.

**Implication for source code**: code in these repos may use 3.14-only
syntax (e.g. PEP 758's parenthesis-free `except A, B:`) and is **not**
backwards-compatible with Python 3.13. Ruff with `target-version = "py314"`
will actively *rewrite* `except (A, B):` into the parenthesis-free form —
which is a SyntaxError on Python 3.13. If a contributor's toolchain
regresses to 3.13, expect lint-fixes from these repos to fail to parse
locally until the toolchain is re-aligned.

## Dependencies Best Practices

### Dependency Update Checklist

**Before updating any dependency version in `manifest.json`:**

1. Verify the new version exists on PyPI: `https://pypi.org/project/PACKAGE_NAME/`
1. Check release notes for breaking changes
1. Test locally if possible

> **WARNING**: Always verify PyPI availability before committing dependency updates. Upstream maintainers
> sometimes create GitHub releases but forget to publish to PyPI, breaking the integration for users.

## Git Workflow

### Commit Messages

Use conventional commits with Claude attribution:

```text
feat(api): implement new feature

[Description]

Co-Authored-By: Claude <noreply@anthropic.com>
```

> **NEVER put a GitHub issue-closing keyword in a commit message.**
> `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`, `resolve`/`resolves`/`resolved`
> followed by `#N` auto-close that issue the moment the commit lands on the default
> branch. Reference issues with a neutral phrase only — "Refs #N", "Reported in #N",
> "Addresses #N". Issues are closed manually by the user, never by automation.

### Branch Strategy

- Default branch (`main` or `master`) = next release
- Create tags for releases
- Use pre-release flag for beta versions

## Pre-Commit Configuration

Linting tools and settings are defined in `.pre-commit-config.yaml`:

| Hook        | Tool                           | Purpose                      |
| ----------- | ------------------------------ | ---------------------------- |
| ruff        | `ruff check --no-fix`          | Python linting               |
| ruff-format | `ruff format --check`          | Python formatting            |
| jsonlint    | `uvx --from demjson3 jsonlint` | JSON validation              |
| yamllint    | `uvx yamllint -d "{...}"`      | YAML linting (inline config) |
| pymarkdown  | `pymarkdown scan`              | Markdown linting             |

All hooks use `language: system` (local tools) with `verbose: true` for visibility.

## Pre-Commit Checks (MANDATORY)

> **CRITICAL: ALWAYS run pre-commit checks before ANY git commit.**
> This is a hard rule - no exceptions. Never commit without passing all checks.

```bash
pre-commit run --all-files
```

> Use `pre-commit` directly, **not** `uvx pre-commit`. The `ty` hook
> resolves the interpreter at runtime via `$(which python)` to match the
> devcontainer venv. `uvx` would provision its own ephemeral Python 3.14
> first on PATH, and that env doesn't have Home Assistant installed —
> `ty` would false-fail with unresolved-import errors even though the
> code is fine. The git commit hook and CI's lint workflow already use
> the venv-installed `pre-commit`, so plain `pre-commit run` matches
> their behavior exactly.

Or run individual tools:

```bash
# Python formatting and linting
ruff format .
ruff check . --fix

# Markdown linting
pymarkdown scan .
```

All checks must pass before committing. This applies to ALL commits, not just releases.

### Windows Shell Notes

When running shell commands on Windows, stray `nul` files may be created (Windows null device artifact).
Check for and delete them after command execution:

```bash
rm nul  # if it exists
```

## Testing

> **CRITICAL: NEVER run pytest locally. The local environment cannot be set up correctly for
> Home Assistant integration tests. ALWAYS use GitHub Actions CI to run tests.**

To run tests:

1. Commit and push changes to the repository
1. GitHub Actions will automatically run the test workflow
1. Check the workflow results in the Actions tab or use `mcp__github__*` tools

> **CRITICAL: NEVER modify production code to make tests pass. Always fix the tests instead.**
> Production code is the source of truth. If tests fail, the tests are wrong - not the production code.
> The only exception is when production code has an actual bug that tests correctly identified.

## Quality Scale Tracking (MUST DO)

This integration tracks [Home Assistant Quality Scale][qs] rules in `quality_scale.yaml`.

**When implementing new features or fixing bugs:**

1. Check if the change affects any quality scale rules
1. Update `quality_scale.yaml` status accordingly:
   - `done` - Rule is fully implemented
   - `todo` - Rule needs implementation
   - `exempt` with `comment` - Rule doesn't apply (explain why)
1. Aim to complete all Bronze tier rules first, then Silver, Gold, Platinum

[qs]: https://developers.home-assistant.io/docs/core/integration-quality-scale/

## Release Management - CRITICAL

> **STOP: NEVER create git tags or GitHub releases without explicit user command.**
> This is a hard rule. Always stop after commit/push and wait for user instruction.

**Published releases are FROZEN** - Never modify the git tag, the ZIP asset, or the
`docs/releases/vX.Y.Z.md` file in a way that changes the meaning of what shipped.

The GitHub *release body* (what shows on the release page) may be edited via
`gh release edit vX.Y.Z --notes-file docs/releases/vX.Y.Z.md` to fix typos, add
cross-references to companion files that landed on `main` shortly after the release,
or clarify scope — as long as the edit doesn't misrepresent what's actually in the
released ZIP. When you do this, also update the matching `docs/releases/vX.Y.Z.md` so
the file and the live release body stay in sync.

**Master branch = Next Release** - All commits target the next version with version bumped
in manifest.json and const.py.

### Version Bumping Rules

> **IMPORTANT: Do NOT bump version during a session. All changes go into the CURRENT unreleased version.**

- The version in `manifest.json` and `const.py` represents the NEXT release being prepared
- **NEVER bump version until user commands "tag and release"**
- Multiple features/fixes can be added to the same unreleased version
- Only bump to a NEW version number AFTER the current version is released

### Version Locations (Must Be Synchronized)

1. `custom_components/abb_fimer_pvi_vsn_rest/manifest.json` → `"version": "X.Y.Z"`
1. `custom_components/abb_fimer_pvi_vsn_rest/const.py` → `VERSION = "X.Y.Z"`

### Complete Release Workflow

> **IMPORTANT: Version Validation**
> The release workflow VALIDATES that tag, manifest.json, and const.py versions all match.
> You MUST update versions BEFORE creating the release, not after.

| Step | Tool           | Action                                                                  |
| ---- | -------------- | ----------------------------------------------------------------------- |
| 1    | Edit           | Update `CHANGELOG.md` with version summary                              |
| 2    | Write          | Create `docs/releases/vX.Y.Z.md` release notes (see format below)      |
| 3    | Edit           | Ensure `manifest.json` and `const.py` have correct version              |
| 4    | Bash           | Run linting: `pre-commit run --all-files`                               |
| 5    | Bash           | `git add . && git commit -m "..."`                                      |
| 6    | Bash           | `git push`                                                              |
| 7    | **STOP**       | Wait for user "tag and release" command                                 |
| 8    | **CI Check**   | Verify ALL CI workflows pass (see CI Verification below)                |
| 9    | **RRR**        | Display Release Readiness Report (see below)                            |
| 10   | Bash           | `git tag -a vX.Y.Z -m "Release vX.Y.Z"`                                |
| 11   | Bash           | `git push --tags`                                                       |
| 12   | gh CLI         | `gh release create vX.Y.Z --title "vX.Y.Z" --notes-file docs/releases/vX.Y.Z.md` |
| 13   | GitHub Actions | Validates versions match, then auto-uploads ZIP asset                   |
| 14   | Edit           | Bump versions in `manifest.json` and `const.py` to next version         |

### CI Verification (MANDATORY)

> **CRITICAL: Before tagging/releasing, ALWAYS verify ALL CI workflows are passing.**
> Use GitHub MCP tools to list workflow runs, then use `gh` CLI to get detailed logs if needed.
> NEVER proceed if any workflow is failing.

**Verification steps:**

1. Use `mcp__GitHub_MCP_Remote__actions_list` to list recent workflow runs:

   ```text
   actions_list(method="list_workflow_runs", owner="alexdelprete", repo="ha-abb-fimer-pvi-vsn-rest")
   ```

1. Check that ALL workflows show `conclusion: "success"`:
   - Lint workflow
   - Validate workflow
   - Tests workflow

1. If any workflow is failing, use `gh` CLI to get detailed failure logs:

   ```bash
   # View failed run logs (replace <run_id> with actual ID from step 1)
   gh run view <run_id> --log-failed

   # Or view full logs for a specific run
   gh run view <run_id> --log
   ```

1. Fix failing tests/issues, commit, push, and re-verify before proceeding

### Release Notes Format (MANDATORY)

Create a release notes file at `docs/releases/vX.Y.Z.md` using this template.
This file is then used as the body when creating the GitHub release.

```markdown
# Release vX.Y.Z

[![GitHub Downloads](https://img.shields.io/github/downloads/alexdelprete/ha-abb-fimer-pvi-vsn-rest/vX.Y.Z/total?style=for-the-badge)](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases/tag/vX.Y.Z)

**Release Date:** YYYY-MM-DD

**Type:** [Major/Minor/Patch/Beta] release - Brief description.

## What's Changed

### Added

- Feature 1

### Changed

- Change 1

### Fixed

- Fix 1

**Full Changelog**:
[compare/vPREV...vX.Y.Z](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/compare/vPREV...vX.Y.Z)
```

### Release Readiness Report (MANDATORY)

> **When user commands "tag and release", ALWAYS display the Release Readiness Report (RRR) BEFORE proceeding.**

Check CI workflows and display:

```markdown
## Release Readiness Report (RRR)

| Check | Status | Details |
|-------|--------|---------|
| **Lint** | status | date |
| **Tests** | status | date |
| **Validate** | status | date |
| **Test Coverage** | status | Minimum required: 97% |
| **Version** | X.Y.Z | manifest.json + const.py |
| **CHANGELOG.md** | status | Updated |
| **Release notes** | status | docs/releases/vX.Y.Z.md |
| **Working Tree** | status | No uncommitted changes |
```

**Test Coverage Requirement:**

> **CRITICAL: Test coverage MUST be at minimum 97%.**
> If coverage drops below 97%, flag it and do not proceed with release until fixed.

**How to get test coverage:**

```bash
gh run list --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --limit 5 | grep Tests
gh run view <run_id> --repo alexdelprete/ha-abb-fimer-pvi-vsn-rest --log 2>&1 | grep "TOTAL"
```

The coverage percentage is the last column in the TOTAL line.

### Issue References in Release Notes

When a release addresses a specific GitHub issue:

- Reference the issue number, but **NEVER use a GitHub closing keyword** —
  `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`, `resolve`/`resolves`/`resolved`
  followed by `#N` — anywhere in commit messages, release notes, the GitHub release
  body, or PR descriptions. Those keywords auto-close the issue when the commit lands
  on the default branch. Use a neutral phrase instead: "Reported in #42",
  "Addresses #42", "Refs #42".
- Thank the user who opened the issue by name and GitHub handle.
- **NEVER close the issue** — the user will do it manually.

### After Publishing a Release

1. Immediately bump versions in `manifest.json` and `const.py` to next version
1. Create new release notes file for next version
1. Mark previous version's documentation as frozen

### Release Documentation Structure

#### Stable/Official Release Notes (e.g., v1.0.0)

- **Scope**: ALL changes since previous stable release
- **Example**: v1.1.0 includes everything since v1.0.0
- **Purpose**: Complete picture for users upgrading from last stable

#### Beta Release Notes (e.g., v1.0.0-beta.1)

- **Scope**: Only incremental changes in this beta
- **Example**: v1.0.0-beta.2 shows only what's new since beta.1
- **Purpose**: Help beta testers focus on what to test

### Documentation Files

- **`CHANGELOG.md`** (root) — quick overview of all releases, Keep a Changelog format
- **`docs/releases/`** — detailed release notes (one file per version)
- **`docs/releases/README.md`** — release directory guide and templates

## Do's and Don'ts

**DO:**

- Run `pre-commit run --all-files` before EVERY commit (NOT `uvx pre-commit` — see Pre-Commit Checks section for why)
- Read CLAUDE.md at session start
- Use `runtime_data` for data storage (not `hass.data[DOMAIN]`)
- Use `@callback` decorator for message handlers
- Log with `%s` formatting (not f-strings)
- Handle missing data gracefully
- Update both manifest.json AND const.py for version bumps
- Get approval before creating tags/releases
- Use custom exceptions for error handling
- Verify PyPI availability before updating dependencies

**NEVER:**

- Commit without running pre-commit checks first
- Modify production code to make tests pass - fix the tests instead
- Use `hass.data[DOMAIN][entry_id]` - use `runtime_data` instead
- Shadow Python builtins (A001)
- Use f-strings in logging (G004)
- Create git tags or GitHub releases without explicit user instruction
- Forget to update VERSION in both manifest.json AND const.py
- Use blocking calls in async context
- Close GitHub issues without explicit user instruction
- Log manually what HA logs automatically (coordinator errors, ConfigEntryNotReady)
- Create documentation files without user request

<!--
==============================================================================
⚠️  END OF TEMPLATE-MANAGED ZONE.

The END SHARED marker line appears below this comment. Anything you add
BELOW the END SHARED marker is integration-specific and safe to edit —
it will not be touched by `repo-sync.py`.
==============================================================================
-->

<!-- END SHARED:repo-sync -->

## Related Projects

- **ha-abb-fimer-pvi-sunspec**: Direct Modbus/TCP (no datalogger)
- **ha-abb-powerone-pvi-sunspec**: Legacy v4.x (Modbus only)

This integration is the REST API variant that works through VSN dataloggers.
