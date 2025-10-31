# Claude Code Development Guidelines

## Project Overview

This is the **ha-abb-fimer-pvi-vsn-rest** integration for Home Assistant.
It provides monitoring of ABB/FIMER/Power-One PVI inverters through VSN300
or VSN700 dataloggers via their REST API.

**Current Status**: v1.0.0-beta.14 - Active development

**Key Features**:

- Automatic VSN300/VSN700 detection
- Multi-device support (inverters, meters, batteries)
- SunSpec-normalized data schema
- Modern Home Assistant entity naming pattern
- Comprehensive sensor attributes
- 210 unique mapped data points

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

**Mapping Structure (v2 - Deduplicated):**

- **Source**: `docs/vsn-sunspec-point-mapping-v2.xlsx` (Excel with model flags)
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

1. Edit Excel: `docs/vsn-sunspec-point-mapping-v2.xlsx`
2. Convert to JSON: `python scripts/convert_excel_to_json_v2.py`
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

- **Device Name**: `abb_vsn_rest_{device_type}_{serial_compact}`
  - Example: `abb_vsn_rest_inverter_0779093g823112`
  - Device type simplified: `inverter`, `datalogger`, `meter`, `battery`
  - Serial compacted: remove `-`, `:`, `_` and lowercase

- **Entity Name**: Friendly display name from mapping
  - Example: "AC Power", "DC Current #1", "Total Energy"
  - From `HA Display Name` field in mapping

- **Entity ID** (auto-generated by HA):
  - Format: `sensor.{device_name}_{slugified_entity_name}`
  - Example: `sensor.abb_vsn_rest_inverter_0779093g823112_ac_power`

- **Unique ID**: Simplified format without model
  - Format: `{device_identifier}_{point_name}`
  - Example: `abb_vsn_rest_inverter_0779093g823112_watts`

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

**Decision**: Use `has_entity_name=True` pattern with friendly display names.

**Rationale**:

- Modern Home Assistant pattern (recommended since 2023.4)
- Allows both custom entity IDs and friendly display names
- Clean device cards (no redundant prefix repetition)
- User-facing names are meaningful ("AC Power" not "abb_vsn_rest_inverter_0779093g823112_m103_watts")

**Implementation**:

- Device name: `abb_vsn_rest_{device_type}_{serial_compact}`
- Entity name: Friendly display name from mapping
- Entity ID: Auto-generated by HA (device + entity name)
- Result: Clean IDs with great UX

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
- `vsn_client.py`: Standalone client for user testing

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

### Adding New Mapping Points

1. Open Excel file: `docs/vsn-sunspec-point-mapping-v2.xlsx`
2. Add new row with all required columns:
   - VSN REST names (VSN300 and VSN700)
   - SunSpec Normalized Name
   - HA Name (internal entity name)
   - Label and Description
   - HA Display Name (user-facing)
   - Category
   - HA Unit of Measurement
   - HA State Class
   - HA Device Class
   - Entity Category (if diagnostic)
   - Model flags (M1, M103, M160, etc.)
3. Save Excel file
4. Convert to JSON: `python scripts/convert_excel_to_json_v2.py`
5. Test with real VSN device or test data
6. Commit all files: Excel + both JSON copies

### Updating Existing Mappings

1. Edit Excel file: `docs/vsn-sunspec-point-mapping-v2.xlsx`
2. Modify descriptions, labels, device classes, etc.
3. Convert to JSON: `python scripts/convert_excel_to_json_v2.py`
4. Test changes
5. Commit all files

### Mapping Quality Standards

- **Descriptions**: Use SunSpec specifications for standard models
- **Categories**: Proper categorization (Inverter, MPPT, Battery, Meter, System Monitoring, etc.)
- **HA Device Classes**: Use correct SensorDeviceClass (power, energy, current, voltage, etc.)
- **HA State Classes**: Use correct SensorStateClass (measurement, total, total_increasing)
- **Display Names**: User-friendly, concise, descriptive

### Release Management

**⚠️ CRITICAL PRINCIPLES:**

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

**Complete Release Workflow:**

See [docs/releases/README.md](docs/releases/README.md) for the detailed 8-step process. Summary:

1. **Prepare Release Notes**: Create `docs/releases/vX.Y.Z.md` with comprehensive release notes following the template
2. **Update CHANGELOG.md**: Add new version section with summary and links
3. **Bump Version Numbers**: Update `manifest.json` version field
4. **Bump Version Constants**: Update `const.py` VERSION and STARTUP_MESSAGE
5. **Commit Changes**: `git add . && git commit -m "chore(release): bump version to vX.Y.Z"`
6. **Push Commits**: `git push`
7. **⚠️ VERIFY CLEAN STATE**: Run `git status` to ensure ALL changes are committed and pushed
   - Check for any uncommitted changes
   - Check for any unpushed commits
   - **CRITICAL**: Do NOT proceed to tags/releases with uncommitted changes
8. **⚠️ STOP HERE** - Get explicit user approval before creating tags/releases
9. **Create Tag** (only when instructed): `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`
10. **Create GitHub Release** (only when instructed): `gh release create vX.Y.Z --prerelease` (beta) or `--latest` (stable)

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

- `docs/vsn-sunspec-point-mapping-v2.xlsx`: Source mapping (Excel with model flags)
- `docs/vsn-sunspec-point-mapping.json`: Generated mapping (docs copy)
- `custom_components/.../data/vsn-sunspec-point-mapping.json`: Runtime mapping

**Scripts:**

- `scripts/generate_mapping_excel.py`: Original script to create Excel mapping
- `scripts/convert_excel_to_json_v2.py`: Convert v2 Excel to JSON (current)
- `scripts/analyze_and_deduplicate_mapping.py`: Analyze and deduplicate mappings
- `scripts/apply_mapping_fixes.py`: Apply automated fixes to mappings
- `scripts/vsn_client.py`: Standalone test client
- `scripts/test_vsn_client.py`: Integration test script

**Documentation:**

- `README.md`: User documentation
- `CLAUDE.md`: This file (dev guidelines)
- `CHANGELOG.md`: Version history
- `docs/MAPPING_FORMAT.md`: Mapping file format and workflow
- `docs/releases/`: Per-version release notes

## Don't Do

- ❌ Use `hass.data[DOMAIN]` - Use `config_entry.runtime_data`
- ❌ Use f-strings in logging - Use `%s` formatting
- ❌ Shadow built-ins - Check with ruff
- ❌ Mix sync/async - All I/O must be async
- ❌ Forget to await async methods
- ❌ Use blocking calls in async context
- ❌ Create documentation files without explicit request
- ❌ Use emojis unless user requests

## Do

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
- ✅ Update documentation when changing architecture
- ✅ Use HA-prefixed column names in mapping ("HA Unit of Measurement", etc.)
- ✅ Use `has_entity_name=True` for modern entity naming pattern
- ✅ Populate comprehensive sensor attributes (14+ fields)
- ✅ Regenerate JSON after editing Excel mapping
- ✅ Commit both Excel and JSON files when updating mappings
- ✅ Use model flags in Excel (not duplicate rows)
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
