# ABB/FIMER PVI VSN REST Integration

[![GitHub Release](https://img.shields.io/github/release/alexdelprete/ha-abb-fimer-pvi-vsn-rest.svg?style=flat-square)](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases)
[![License](https://img.shields.io/github/license/alexdelprete/ha-abb-fimer-pvi-vsn-rest.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

⚠️ **BETA v1.0.0-beta.2** - Active Development

Home Assistant custom integration for ABB/FIMER/Power-One PVI inverters via **VSN300/VSN700 datalogger REST API**.

## Overview

This integration connects to VSN300 or VSN700 dataloggers to monitor ABB/FIMER/Power-One PV inverters. It communicates via the datalogger's REST API and normalizes data to SunSpec-compatible format for consistent Home Assistant entity creation.

### Features

- ✅ **Automatic Discovery**: Detects VSN model (VSN300/VSN700) and discovers all connected devices
- ✅ **VSN300 Support**: HTTP Digest authentication with X-Digest scheme
- ✅ **VSN700 Support**: HTTP Basic authentication
- ✅ **Multi-Device**: Supports inverters, meters, batteries, and storage devices
- ✅ **SunSpec Normalization**: VSN data mapped to SunSpec standard format
- ✅ **Device Hierarchy**: Proper device relationships (inverters via datalogger)
- ✅ **Complete Metadata**: Model, manufacturer, firmware version, serial numbers
- ✅ **Configuration UI**: Easy setup through Home Assistant UI

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

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add repository: `https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest`
5. Category: Integration
6. Click "Add"
7. Search for "ABB FIMER PVI VSN REST"
8. Click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [Releases](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases)
2. Extract and copy `custom_components/abb_fimer_pvi_vsn_rest` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Prerequisites

1. VSN300 or VSN700 datalogger connected to your network
2. Datalogger IP address or hostname
3. Valid credentials (default: username=`guest`, password=empty)

### Setup Steps

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"ABB FIMER PVI VSN REST"**
4. Enter configuration:
   - **Host**: IP address or hostname (e.g., `192.168.1.100` or `abb-vsn300.local`)
   - **Username**: Authentication username (optional, default: `guest`)
   - **Password**: Authentication password (optional, default: empty)
5. Click **"Submit"**

The integration will:
- Detect VSN model (VSN300 or VSN700)
- Discover all connected devices (inverters, meters, batteries)
- Create Home Assistant entities for all data points

### Configuration Options

After setup, click **"Configure"** on the integration card to adjust:

- **Scan Interval**: How often to poll data (default: 60 seconds, range: 30-600)

### Reconfiguration

If you need to change the hostname/IP or credentials:

1. Go to the integration card
2. Click the three dots menu → **"Reconfigure"**
3. Enter new settings

## Entities

The integration creates sensor entities for all available data points from your devices.

### Entity Naming

Entities are automatically named based on the device and measurement:

- **Format**: `sensor.{device_model}_{serial}_{measurement}`
- **Example**: `sensor.pvi_10_0_outd_077909_3g82_3112_watts`

### Device Information

Each device includes complete metadata:

| Field | Description | Example |
|-------|-------------|---------|
| Name | Device model + Serial | `PVI-10.0-OUTD (077909-3G82-3112)` |
| Manufacturer | From device data | `Power-One`, `ABB`, `FIMER` |
| Model | Device model | `PVI-10.0-OUTD` |
| Serial Number | Device S/N | `077909-3G82-3112` |
| Firmware | Device firmware | `C008` |
| Configuration URL | Datalogger only | `http://abb-vsn300.local` |
| Via Device | Device connection | Linked to datalogger |

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

```
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

2. **REST Client** (`client.py`)
   - Authenticates with VSN datalogger
   - Fetches data from REST API endpoints
   - Handles VSN300/VSN700 authentication differences

3. **Normalizer** (`normalizer.py`)
   - Transforms VSN proprietary format to SunSpec standard
   - Uses mapping definitions from `mapping/` directory
   - Provides consistent data structure

4. **Coordinator** (`coordinator.py`)
   - Manages periodic data polling
   - Handles errors and retries
   - Distributes data to sensors

5. **Config Flow** (`config_flow.py`)
   - User interface for setup
   - Connection validation
   - Reconfiguration support

## VSN Authentication

### VSN300
- **Scheme**: Custom HTTP Digest (X-Digest header)
- **Process**:
  1. Request challenge from `/v1/dgst`
  2. Compute SHA-256 digest
  3. Add `Authorization: X-Digest {digest}` header

### VSN700
- **Scheme**: HTTP Basic Authentication
- **Process**: Standard Basic Auth with base64-encoded credentials

Both schemes are handled automatically by the integration.

## Troubleshooting

### Connection Issues

**Symptom**: "Cannot connect" error during setup

**Solutions**:
1. Verify datalogger IP/hostname is correct
2. Ensure datalogger is powered on and network-accessible
3. Check firewall rules allow HTTP (port 80)
4. Try accessing `http://{host}/v1/status` in browser

### Authentication Issues

**Symptom**: "Authentication failed" error

**Solutions**:
1. Try default credentials (username: `guest`, password: empty)
2. Check credentials in datalogger web interface
3. Reset datalogger credentials if necessary

### No Entities Created

**Symptom**: Integration loads but no sensors appear

**Solutions**:
1. Check Home Assistant logs for errors
2. Verify inverter is connected to datalogger
3. Check datalogger web interface shows inverter data
4. Enable debug logging (see below)

### Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.abb_fimer_pvi_vsn_rest: debug
```

Restart Home Assistant and check logs for detailed information.

## Data Mapping

VSN data points are mapped to SunSpec-compatible schema using definitions in the `mapping/` directory. The mapping includes:

- Device classification (inverter type, meter, battery, etc.)
- Point name translation (VSN → SunSpec)
- Unit conversions and scaling
- Device class and state class for Home Assistant
- Proper labels and descriptions

For details, see [MAPPING_NOTES.md](docs/MAPPING_NOTES.md).

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

### Project Structure

```
custom_components/abb_fimer_pvi_vsn_rest/
├── __init__.py              # Integration entry point
├── config_flow.py           # UI configuration
├── coordinator.py           # Data update coordinator
├── sensor.py                # Sensor platform
├── const.py                 # Constants
├── manifest.json            # Integration manifest
├── strings.json             # UI strings
├── translations/
│   └── en.json             # English translations
└── abb_fimer_vsn_rest_client/
    ├── client.py           # REST API client
    ├── auth.py             # Authentication handling
    ├── discovery.py        # Device discovery
    ├── normalizer.py       # Data normalization
    ├── exceptions.py       # Custom exceptions
    └── mapping/            # VSN→SunSpec mapping files
```

## Related Projects

- **[ha-abb-fimer-pvi-sunspec](https://github.com/alexdelprete/ha-abb-fimer-pvi-sunspec)** - Direct Modbus/TCP integration (no datalogger required)
- **[ha-abb-powerone-pvi-sunspec](https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec)** - Legacy v4.x integration (Modbus only)

## Support

- **Issues**: [GitHub Issues](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/issues)
- **Discussions**: [GitHub Discussions](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/discussions)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Developed by [Alex Del Prete](https://github.com/alexdelprete)

SunSpec model definitions from [pysunspec2](https://github.com/sunspec/pysunspec2) (Apache-2.0 license)
