# Claude Code Development Guidelines

## Project Overview

This is the **ha-abb-fimer-pvi-vsn-rest** integration for Home Assistant.
It provides monitoring of ABB/FIMER/Power-One PVI inverters through VSN300
or VSN700 dataloggers via their REST API.

**Current Status**: v1.0.0-beta.2 - Active development

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

- Load mapping definitions from `mapping/` directory
- Transform device types (e.g., `inverter_3phases` → `abb_m103`)
- Map point names (e.g., `m103_1_W` → `abb_m103_w`)
- Apply SunSpec metadata (device_class, state_class, units, labels)
- Handle device ID normalization (MAC → S/N for datalogger)

**Mapping Structure:**

```json
{
  "inverter_3phases": {
    "device_class": "abb_m103",
    "points": {
      "m103_1_W": {
        "name": "abb_m103_w",
        "label": "AC Power",
        "sunspec_name": "W",
        "device_class": "power",
        "state_class": "measurement",
        "units": "W"
      }
    }
  }
}
```

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

Creates Home Assistant sensor entities.

**Entity Creation:**

- One sensor per data point per device
- Unique ID: `{DOMAIN}_{device_id}_{point_name}`
- Entity name: From point label
- Device class, state class, units from mapping

**Device Info:**

All HA device info fields populated from discovery:

- `identifiers`: `(DOMAIN, device_id)`
- `name`: Model + Serial (e.g., `"PVI-10.0-OUTD (077909-3G82-3112)"`)
- `manufacturer`: From `C_Mn` point
- `model`: Device model
- `serial_number`: Device S/N or clean MAC
- `sw_version`: Firmware version from `C_Vr` or `fw_ver`
- `hw_version`: Hardware version (if available)
- `configuration_url`: Datalogger hostname (datalogger only)
- `via_device`: Link to datalogger (for inverters/meters)

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

### Adding New Mapping

1. Identify VSN point name in livedata
2. Find SunSpec equivalent
3. Update `mapping/{device_type}.json`
4. Add point definition with:
   - `name`: HA entity name
   - `label`: Human-readable label
   - `sunspec_name`: SunSpec point name
   - `device_class`: HA device class
   - `state_class`: HA state class
   - `units`: Unit of measurement
   - `description`: Detailed description

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
7. **⚠️ STOP HERE** - Get explicit user approval before creating tags/releases
8. **Create Tag** (only when instructed): `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`
9. **Create GitHub Release** (only when instructed): `gh release create vX.Y.Z --prerelease` (beta) or `--latest` (stable)

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

- Based on device serial number or clean MAC
- Example: `"077909-3G82-3112"` or `"ac1f0fb050b5"`

**Sensors:**

- Format: `{DOMAIN}_{device_id}_{point_name}`
- Example: `"abb_fimer_pvi_vsn_rest_077909-3g82-3112_abb_m103_w"`

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
- `exceptions.py`: Custom exceptions
- `mapping/`: VSN→SunSpec mappings

**Documentation:**

- `README.md`: User documentation
- `CLAUDE.md`: This file (dev guidelines)
- `CHANGELOG.md`: Version history
- `docs/MAPPING_NOTES.md`: Mapping documentation

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
