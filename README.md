# ABB/FIMER PVI VSN REST Integration

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Community Forum][forum-shield]][forum]

[![Tests][tests-shield]][tests]
[![Code Coverage][coverage-shield]][coverage]
[![Downloads][downloads-shield]][downloads]

Home Assistant custom integration for ABB/FIMER/Power-One PVI inverters via **VSN300/VSN700 datalogger REST API**.

## Overview

This integration connects to VSN300 or VSN700 dataloggers to monitor ABB/FIMER/Power-One PV inverters. It communicates via the datalogger's REST API and normalizes data to
SunSpec-compatible format for consistent Home Assistant entity creation.

### Features

- ✅ **Automatic Discovery**: Detects VSN model (VSN300/VSN700) and discovers all connected devices
- ✅ **VSN300 Support**: HTTP Digest authentication with X-Digest scheme
- ✅ **VSN700 Support**: HTTP Basic authentication
- ✅ **Multi-Device**: Supports inverters, meters, batteries, and storage devices
- ✅ **SunSpec Normalization**: VSN data mapped to SunSpec standard format
- ✅ **Device Hierarchy**: Proper device relationships (inverters via datalogger)
- ✅ **Complete Metadata**: Model, manufacturer, firmware version, serial numbers
- ✅ **Configuration UI**: Easy setup through Home Assistant UI
- ✅ **Multi-Language**: English and Italian translations included

### Supported Devices

**VSN Dataloggers:**

- VSN300 (WIFI LOGGER CARD)
- VSN700 (Ethernet/WiFi datalogger)

**Inverters:** (via datalogger)

- Single-phase: REACT2-3.6-TL, REACT2-5.0-TL, etc.
- Three-phase: PVI-10.0-OUTD, PVI-12.5-OUTD, etc.

**Other Devices:** (via datalogger)

- Energy meters
- Battery storage systems

## Installation

### HACS (Recommended)

This integration is available in the official [HACS] default repository:

[![Quick installation link](https://my.home-assistant.io/badges/hacs_repository.svg)][my-hacs]

1. Open HACS in Home Assistant
1. Go to "Integrations"
1. Search for "ABB FIMER PVI VSN REST"
1. Click "Download"
1. Restart Home Assistant

### Manual Installation

1. Download the latest release from [Releases](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases)
1. Extract and copy `custom_components/abb_fimer_pvi_vsn_rest` to your `config/custom_components/` directory
1. Restart Home Assistant

## Configuration

### Prerequisites

1. VSN300 or VSN700 datalogger connected to your network
1. Datalogger IP address or hostname
1. Valid credentials (check your datalogger's web interface for configured users)

### Setup Steps

1. Go to **Settings** → **Devices & Services**
1. Click **"+ Add Integration"**
1. Search for **"ABB FIMER PVI VSN REST"**
1. Enter configuration:
   - **Host**: IP address or hostname (e.g., `192.168.1.100` or `abb-vsn300.local`)
   - **Username**: Authentication username (commonly `guest`, but check your device)
   - **Password**: Authentication password (may be empty or configured on your device)
1. Click **"Submit"**

The integration will:

- Detect VSN model (VSN300 or VSN700)
- Discover all connected devices (inverters, meters, batteries)
- Create Home Assistant entities for all data points

### Configuration Options

After setup, click **"Configure"** on the integration card to access the options dialog. All configuration options are described below:

#### Polling Settings

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Scan interval** | 60 | 10-600 sec | How often to fetch data from the VSN device |

#### Failure Notifications

| Option | Default | Description |
|--------|---------|-------------|
| **Enable runtime failure notifications** | On | Notify when device becomes unreachable during normal operation |
| **Enable startup failure notifications** | Off | Notify when device is unreachable at Home Assistant startup |
| **Failures before notification** | 3 (1-10) | Consecutive failures before creating a notification |
| **Recovery script** | (none) | Script to execute when failures threshold is reached (e.g., `script.restart_router`) |

**Runtime vs Startup Notifications:**
- **Runtime**: Monitors failures during normal operation after HA is running
- **Startup**: Monitors failures when HA starts/restarts and can't connect to the device

**Tip for solar-only systems**: If your inverter is offline at night and you restart HA at night,
disable "Enable startup failure notifications" to avoid unnecessary alerts.

#### Device Name Customization

| Option | Description |
|--------|-------------|
| **Inverter device name** | Custom name for inverter devices. Leave empty for default. |
| **Datalogger device name** | Custom name for datalogger devices. Leave empty for default. |
| **Meter device name** | Custom name for meter devices. Leave empty for default. |
| **Battery device name** | Custom name for battery devices. Leave empty for default. |
| **Regenerate entity IDs** | ⚠️ Update entity IDs to match new names. **Breaks automations!** |

**Note**: Only device types discovered in your system will appear in the options dialog.

See [Custom Device Names](#custom-device-names) below for detailed examples.

### Connection Failure Notifications

The integration can notify you when the datalogger becomes unreachable and optionally execute a recovery script.

**How It Works:**

1. When the datalogger fails to respond, the integration tracks consecutive failures
2. After reaching the threshold (default: 3), a persistent notification appears
3. If configured, a recovery script executes automatically (e.g., `script.restart_router`)
4. When connection recovers, a recovery notification shows downtime details

**Recovery Script Use Cases:**

- Restart router/network equipment via smart plug
- Power cycle the datalogger
- Send alerts via external services
- Trigger any Home Assistant automation

**Recovery Script Variables:**

When your recovery script is called, the integration passes these variables that you can use:

| Variable | Description | Example |
|----------|-------------|---------|
| `device_name` | Full device name | `VSN300 (111033-3N16-1421)` |
| `host` | Device hostname/IP | `192.168.1.100` |
| `vsn_model` | Datalogger model | `VSN300` or `VSN700` |
| `logger_sn` | Logger serial number | `111033-3N16-1421` |
| `failures_count` | Number of consecutive failures | `3` |

**Example Script:**

```yaml
# scripts.yaml
power_cycle_datalogger:
  alias: "Power Cycle Datalogger"
  sequence:
    - service: switch.turn_off
      target:
        entity_id: switch.datalogger_plug
    - delay:
        seconds: 10
    - service: switch.turn_on
      target:
        entity_id: switch.datalogger_plug
    - service: notify.mobile_app
      data:
        title: "Datalogger Recovery"
        message: "Power cycled {{ device_name }} after {{ failures_count }} failures"
```

### Reconfiguration

If you need to change the hostname/IP or credentials:

1. Go to the integration card
1. Click the three dots menu → **"Reconfigure"**
1. Enter new settings

## Entities

The integration creates sensor entities for all available data points from your devices.

### Entity Naming

The integration uses Home Assistant's modern entity naming pattern (`has_entity_name=True`).

**Device Names**: Friendly format for beautiful UI display

- Format: `{Manufacturer} {DeviceType} {Model} ({Serial})`
- Examples:
  - `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112)`
  - `ABB Datalogger VSN300 (111033-3N16-1421)`
  - `FIMER Inverter REACT2-3.6-TL (123456-ABCD-5678)`

**Entity IDs**: Automatically generated by Home Assistant (slugified device name + measurement)

- Format: `sensor.{manufacturer}_{device_type}_{model}_{serial}_{measurement}`
- Examples:
  - `sensor.power_one_inverter_pvi_10_0_outd_077909_3g82_3112_ac_power`
  - `sensor.abb_datalogger_vsn300_111033_3n16_1421_firmware_version`
  - `sensor.fimer_inverter_react2_3_6_tl_123456_abcd_5678_ac_energy`

**Entity Friendly Names**: Shown in the UI (device name + measurement display name)

- Examples:
  - `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112) AC Power`
  - `ABB Datalogger VSN300 (111033-3N16-1421) Firmware Version`
  - `FIMER Inverter REACT2-3.6-TL (123456-ABCD-5678) AC Energy`

**Notes**:

- Entity IDs are stable and won't change once created
- Friendly names make entities easy to identify in the UI
- Device page groups all entities by device for easy management

### Custom Device Names

You can customize device names for each device type through the integration options. This is useful if you want shorter, friendlier names for your devices.

**To configure custom names**:

1. Go to **Settings** → **Devices & Services**
1. Find the **ABB/FIMER PVI VSN REST** integration card
1. Click **Configure**
1. Enter custom names for any device type you want to customize
1. Leave fields empty to keep default naming

**Example**:

| Setting | Device Name | Entity ID Example | |---------|-------------|-------------------| | **No prefix (default)** | `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112)` |
`sensor.power_one_inverter_pvi_...` | | **Custom: "Solar Inverter"** | `Solar Inverter` | `sensor.solar_inverter_power_ac` |

**Dynamic Options Form**: The configuration only shows prefix fields for device types that were actually discovered. For example, if you only have an inverter and datalogger, you
won't see fields for meter or battery.

**Entity ID Behavior**:

| Action | Entity ID | Automations | |--------|-----------|-------------| | Change device name only | **Preserved** | Keep working ✅ | | Change name + check "Regenerate entity IDs"
| **Updated** | **Will break** ⚠️ |

**⚠️ Warning**: The "Regenerate entity IDs" checkbox will update all entity IDs to match new device names. This **will break** existing automations, scripts, and dashboards that
reference these entities. Only use this option if you understand the implications and are prepared to update your automations.

### Supported Languages

The integration includes native translations for entity names in 10 European languages:

| Language | Code | Status | |----------|------|--------| | English | `en` | ✅ Complete (258 sensors) | | Italian | `it` | ✅ Complete (258 sensors) | | French | `fr` | ✅ Complete
(258 sensors) | | Spanish | `es` | ✅ Complete (258 sensors) | | Portuguese | `pt` | ✅ Complete (258 sensors) | | German | `de` | ✅ Complete (258 sensors) | | Swedish | `sv` | ✅
Complete (258 sensors) | | Norwegian Bokmål | `nb` | ✅ Complete (258 sensors) | | Finnish | `fi` | ✅ Complete (258 sensors) | | Estonian | `et` | ✅ Complete (258 sensors) |

**Automatic Language Selection**: Home Assistant automatically selects the appropriate language based on your system settings. No configuration needed!

**Examples**:

- **English**: `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112) Power AC`
- **Italian**: `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112) Potenza AC`
- **French**: `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112) Puissance AC`
- **German**: `Power-One Inverter PVI-10.0-OUTD (077909-3G82-3112) AC-Leistung`

**Note**: Device names (manufacturer, model, serial) remain in their original format. Only measurement names are translated.

### Device Information

Each device includes complete metadata:

| Field | Description | Example | |-------|-------------|---------| | Name | Device model + Serial | `PVI-10.0-OUTD (077909-3G82-3112)` | | Manufacturer | From device data |
`Power-One`, `ABB`, `FIMER` | | Model | Device model | `PVI-10.0-OUTD` | | Serial Number | Device S/N | `077909-3G82-3112` | | Firmware | Device firmware | `C008` | | Configuration
URL | Datalogger only | `http://abb-vsn300.local` | | Via Device | Device connection | Linked to datalogger |

### Typical Entities (Inverter)

**Production:**

- AC Power (W)
- AC Current (A)
- AC Voltage (V)
- AC Frequency (Hz)
- Total Energy (Wh)
- Daily Energy (Wh)

**DC Inputs (per MPPT):**

- DC Voltage (V)
- DC Current (A)
- DC Power (W)

**Status:**

- Operating State
- Cabinet Temperature
- Isolation Resistance

## Architecture

### Data Flow

```text
VSN Datalogger
    ↓ (REST API)
VSN REST Client
    ↓ (Raw JSON)
Normalizer
    ↓ (SunSpec-compatible JSON)
Coordinator
    ↓ (Polling)
Sensor Platform
    ↓
Home Assistant Entities
```

### Key Components

1. **Discovery Module** (`discovery.py`)

   - Detects VSN model (VSN300/VSN700)
   - Discovers all connected devices
   - Extracts metadata (model, manufacturer, firmware)
   - Handles device identification (S/N, MAC addresses)

1. **REST Client** (`client.py`)

   - Authenticates with VSN datalogger
   - Fetches data from REST API endpoints
   - Handles VSN300/VSN700 authentication differences

1. **Normalizer** (`normalizer.py`)

   - Transforms VSN proprietary format to SunSpec standard
   - Uses mapping definitions from `mapping/` directory
   - Provides consistent data structure

1. **Coordinator** (`coordinator.py`)

   - Manages periodic data polling
   - Handles errors and retries
   - Distributes data to sensors

1. **Config Flow** (`config_flow.py`)

   - User interface for setup
   - Connection validation
   - Reconfiguration support

## VSN Authentication

The integration automatically detects which VSN model you have and uses the appropriate authentication method.

### Detection Process

1. **Send unauthenticated request** to `/v1/status`
1. **Examine response**:
   - **HTTP 401** with `WWW-Authenticate: X-Digest...` → **VSN300** (auth required)
   - **HTTP 401** without digest → Try preemptive Basic auth → **VSN700** (auth required)
   - **HTTP 200** → Analyze status data → **VSN300 or VSN700** (no auth required)

### VSN300

- **Scheme**: Custom HTTP Digest (X-Digest header)
- **Process**:
  1. Request challenge from endpoint
  1. Compute MD5 digest response: `MD5(MD5(username:realm:password):nonce:MD5(method:uri))`
  1. Send request with `Authorization: X-Digest username="...", realm="...", nonce="...", response="..."`

### VSN700

- **Scheme**: Preemptive HTTP Basic Authentication
- **Process**: Send `Authorization: Basic {base64(username:password)}` with every request
- **Note**: VSN700 accepts credentials immediately without requiring a challenge-response flow

### Devices Without Authentication

Some VSN devices may have authentication disabled. The integration fully supports this:

- When the device returns HTTP 200 (no authentication required), the integration analyzes the status data structure to determine the model
- **VSN300 indicators**: `logger.board_model = "WIFI LOGGER CARD"`, serial format `XXXXXX-XXXX-XXXX`, or many status keys (>10)
- **VSN700 indicators**: `logger.loggerId` in MAC address format, or minimal status keys (≤3)
- All subsequent requests are made without authentication headers

All authentication methods are handled automatically by the integration - no configuration needed!

## Troubleshooting

### Connection Issues

**Symptom**: "Cannot connect" error during setup

**Solutions**:

1. Verify datalogger IP/hostname is correct
1. Ensure datalogger is powered on and network-accessible
1. Check firewall rules allow HTTP (port 80)
1. Try accessing `http://{host}/v1/status` in browser

### Authentication Issues

**Symptom**: "Authentication failed" error

**Solutions**:

1. Check your datalogger's web interface for valid credentials
1. Check credentials in datalogger web interface
1. Reset datalogger credentials if necessary

### No Entities Created

**Symptom**: Integration loads but no sensors appear

**Solutions**:

1. Check Home Assistant logs for errors
1. Verify inverter is connected to datalogger
1. Check datalogger web interface shows inverter data
1. Enable debug logging (see below)

### Debug Logging

To enable debug logging for this integration, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.abb_fimer_pvi_vsn_rest: debug
```

After adding this configuration:

1. **Restart Home Assistant** to apply the logging configuration
2. **Reproduce the issue** you're experiencing
3. **Download the full logs** using one of these methods:

#### Method 1: Home Assistant UI (Recommended)

1. Go to **Settings** → **System** → **Logs**
2. Click **"Download Full Log"** button in the top right
3. The downloaded file contains all log entries including debug messages

#### Method 2: Direct File Access

If you have access to your Home Assistant configuration directory:

```bash
# The log file is located at:
config/home-assistant.log

# To filter only this integration's logs:
grep "abb_fimer_pvi_vsn_rest" home-assistant.log > integration_debug.log
```

#### Method 3: SSH/Terminal Access

```bash
# View live logs filtered by integration:
ha core logs | grep "abb_fimer_pvi_vsn_rest"

# Or for Docker installations:
docker logs homeassistant 2>&1 | grep "abb_fimer_pvi_vsn_rest"
```

#### What to Include When Reporting Issues

When opening a GitHub issue, please include:

1. **Full debug log** (downloaded via Method 1 above)
2. **Integration version** (found in HACS or Settings → Devices & Services)
3. **Home Assistant version** (Settings → About)
4. **VSN datalogger model** (VSN300 or VSN700)
5. **Inverter model** (e.g., PVI-10.0-OUTD, REACT2-3.6-TL)
6. **Steps to reproduce** the issue

**Privacy Note**: Debug logs may contain your device's IP address and serial numbers. Review the log before sharing and redact sensitive information if needed.

### Testing and Reporting Issues

If you're experiencing connection or authentication issues, you can use the standalone test script to diagnose the problem and provide detailed logs when reporting issues.

#### Using the VSN Test Script

The repository includes a standalone diagnostic script that can test your VSN device without installing the integration:

1. **Download the script**:

   ```bash
   wget https://raw.githubusercontent.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/master/scripts/vsn-rest-client/vsn_rest_client.py
   ```

1. **Install dependencies**:

   ```bash
   pip install aiohttp
   ```

1. **Run the test**:

   ```bash
   python vsn_rest_client.py 192.168.1.100
   ```

   (Replace `192.168.1.100` with your datalogger's IP address)

1. **Review output**:

   The script will:

   - Auto-detect VSN300 vs VSN700
   - Test all REST API endpoints
   - Create JSON output files with raw and normalized data
   - Display comprehensive debug information

1. **When reporting issues**:

   - Include the console output showing device detection and any errors
   - Attach the generated JSON files (especially `vsn300_status.json` or `vsn700_status.json`)
   - Specify your inverter model and VSN datalogger model

#### Common Test Results

**Successful VSN300 detection**:

```text
[VSN Detection] Detected VSN300 (digest auth in WWW-Authenticate: X-Digest realm="...")
✓ Device detected: VSN300
```

**Successful VSN700 detection**:

```text
[VSN Detection] Not VSN300. Attempting preemptive Basic authentication for VSN700.
[VSN Detection] Detected VSN700 (preemptive Basic authentication)
✓ Device detected: VSN700
```

**Authentication failure**:

```text
[VSN Detection] Preemptive Basic auth failed with status 401.
Device authentication failed. Not VSN300/VSN700 compatible.
```

If you see this, verify your credentials and ensure the device is a VSN300/VSN700 datalogger.

## Data Mapping

VSN data points are mapped to SunSpec-compatible schema using definitions in the `mapping/` directory.

The mapping includes:

- Device classification (inverter type, meter, battery, etc.)
- Point name translation (VSN → SunSpec)
- Unit conversions and scaling
- Device class and state class for Home Assistant
- Proper labels and descriptions

For details, see [MAPPING_NOTES.md](docs/MAPPING_NOTES.md).

## Translations

The integration includes complete translations for entity names in **10 European languages**:

- 🇬🇧 **English** (`en.json`) - 258 sensors
- 🇮🇹 **Italian** (`it.json`) - 258 sensors
- 🇫🇷 **French** (`fr.json`) - 258 sensors
- 🇪🇸 **Spanish** (`es.json`) - 258 sensors
- 🇵🇹 **Portuguese** (`pt.json`) - 258 sensors
- 🇩🇪 **German** (`de.json`) - 258 sensors
- 🇸🇪 **Swedish** (`sv.json`) - 258 sensors
- 🇳🇴 **Norwegian** (`nb.json`) - 258 sensors
- 🇫🇮 **Finnish** (`fi.json`) - 258 sensors
- 🇪🇪 **Estonian** (`et.json`) - 258 sensors

The integration automatically uses the language configured in your Home Assistant instance. All UI strings, error messages, configuration flows, and **entity names** are fully
translated.

### Contributing Translations

Want to add a new language or improve existing translations? Here's how:

**For Entity Names** (258 sensors in `entity.sensor` section):

1. Fork the repository

1. Copy `translations/en.json` to `translations/[language_code].json`

   - Use [ISO 639-1 language codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g., `nl` for Dutch, `da` for Danish)

1. Translate the `entity.sensor` section:

   ```json
   "entity": {
     "sensor": {
       "watts": { "name": "Your Translation Here" },
       "dc_voltage_1": { "name": "Your Translation Here" },
       ...
     }
   }
   ```

1. Keep the `config` and `options` sections from `en.json` (or translate those too!)

1. Test with your Home Assistant instance (set HA language to your new language)

1. Submit a pull request

**Translation Tips**:

- Maintain technical accuracy (e.g., "Power AC" should remain related to AC power)
- Keep translations concise (they appear in entity names)
- Preserve measurement context (e.g., distinguish "Voltage DC - String 1" from "Voltage AC")
- Review existing languages for consistency

**Questions?** Open a [GitHub Discussion](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/discussions) - the community is happy to help!

See [translations/](custom_components/abb_fimer_pvi_vsn_rest/translations/) for existing translations.

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

### Project Structure

```text
custom_components/abb_fimer_pvi_vsn_rest/
├── __init__.py              # Integration entry point
├── config_flow.py           # UI configuration
├── coordinator.py           # Data update coordinator
├── sensor.py                # Sensor platform
├── const.py                 # Constants and state mappings
├── manifest.json            # Integration manifest
├── translations/            # Entity name translations (10 languages)
│   ├── de.json             # German
│   ├── en.json             # English
│   ├── es.json             # Spanish
│   ├── et.json             # Estonian
│   ├── fi.json             # Finnish
│   ├── fr.json             # French
│   ├── it.json             # Italian
│   ├── nb.json             # Norwegian Bokmål
│   ├── pt.json             # Portuguese
│   └── sv.json             # Swedish
└── abb_fimer_vsn_rest_client/  # Client library
    ├── __init__.py         # Library exports
    ├── client.py           # REST API client
    ├── auth.py             # Authentication (VSN300/VSN700)
    ├── discovery.py        # VSN model and device discovery
    ├── normalizer.py       # VSN→SunSpec data normalization
    ├── mapping_loader.py   # Mapping file loader
    ├── models.py           # Data models
    ├── utils.py            # Helper utilities
    ├── exceptions.py       # Custom exceptions
    └── data/               # Client library resources
        └── vsn-sunspec-point-mapping.json  # VSN→SunSpec mapping (258 points)
```

## Related Projects

- **[ha-abb-fimer-pvi-sunspec](https://github.com/alexdelprete/ha-abb-fimer-pvi-sunspec)** Direct Modbus/TCP integration (no datalogger required)

- **[ha-abb-powerone-pvi-sunspec](https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec)** Legacy v4.x integration (Modbus only)

## Support

- **Issues**: [GitHub Issues](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/issues)
- **Discussions**: [GitHub Discussions](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/discussions)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Developed by [Alessandro Del Prete](https://github.com/alexdelprete)

SunSpec model definitions from [SunSpec Models Repository](https://github.com/sunspec/models) (Apache-2.0 license)

## Coffee

If you like this integration, I'll gladly accept some quality coffee, but please don't feel obliged. :)

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

______________________________________________________________________

[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge
[coverage]: https://codecov.io/gh/alexdelprete/ha-abb-fimer-pvi-vsn-rest
[coverage-shield]: https://img.shields.io/codecov/c/github/alexdelprete/ha-abb-fimer-pvi-vsn-rest?style=for-the-badge
[downloads]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases
[downloads-shield]: https://img.shields.io/github/downloads/alexdelprete/ha-abb-fimer-pvi-vsn-rest/total?style=for-the-badge
[forum]: https://community.home-assistant.io/t/integration-for-abb-fimer-power-one-pvi-inverters-via-vsn300-vsn700-datalogger-rest-api/
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[hacs]: https://hacs.xyz
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-abb-fimer-pvi-vsn-rest&category=integration
[releases]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-abb-fimer-pvi-vsn-rest?style=for-the-badge&color=darkgreen
[tests]: https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/actions/workflows/test.yml
[tests-shield]: https://img.shields.io/github/actions/workflow/status/alexdelprete/ha-abb-fimer-pvi-vsn-rest/test.yml?style=for-the-badge&label=Tests
