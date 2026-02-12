# VSN REST Client - Standalone Testing Tool

A standalone Python script for testing and debugging VSN300/VSN700 datalogger REST APIs.
This tool mirrors the integration's client library features but runs independently of
Home Assistant.

## Purpose

This tool allows you to:

- Test connectivity to VSN300/VSN700 dataloggers
- Verify authentication (X-Digest for VSN300, Basic Auth for VSN700)
- Run full device discovery (logger metadata, inverters, meters, batteries)
- Fetch and inspect raw API responses (status, livedata, feeds)
- Normalize data with SunSpec mapping (downloaded from GitHub)
- Translate Aurora protocol state codes to human-readable text
- Export all data to JSON files for analysis

## Prerequisites

- Python 3.11+
- `aiohttp` library
- Network access to the VSN datalogger

## Installation

```bash
pip install aiohttp
```

## Usage

### Basic Usage

```bash
# Auto-detect VSN model, run discovery, normalize data
python vsn_rest_client.py --host 192.168.1.100

# With custom credentials
python vsn_rest_client.py --host 192.168.1.100 --username admin --password mypass

# With verbose output (shows raw status data)
python vsn_rest_client.py --host 192.168.1.100 -v

# Debug mode (shows all internal logging)
python vsn_rest_client.py --host 192.168.1.100 --debug
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | (required) | IP address or hostname of the datalogger |
| `--username` | `guest` | Authentication username |
| `--password` | `""` | Authentication password |
| `--timeout` | `10` | Request timeout in seconds |
| `-v, --verbose` | `False` | Show full raw API response data |
| `--debug` | `False` | Enable debug logging |

## Features

### Device Discovery

Automatically detects VSN model and discovers all connected devices:

- **Logger metadata**: Serial number, model, firmware, hostname
- **Connected devices**: Inverters, meters, batteries with manufacturer and firmware info
- **Synthetic datalogger device**: Created from status data (not in livedata)

### Data Normalization

Downloads the SunSpec mapping from GitHub and normalizes all sensor data:

- **Point name normalization**: M101/M102 -> M103 (VSN300), TSoc -> Soc (VSN700)
- **Unit conversions**: uA -> mA, A -> mA (VSN700 leakage), Wh -> kWh, bytes -> MB
- **Temperature correction**: Scale factor fix when value > 70 degrees
- **String cleanup**: Strip dashes from product numbers, title case normalization
- **Energy conversion**: All energy sensors converted Wh -> kWh (by device_class)

### Aurora State Translation

Status entities are translated to human-readable text:

- **Global State** (42 states): "Run", "Ground Fault", "Recovery", etc.
- **DC-DC State** (20 states): "MPPT", "Input OV", "Ramp Start", etc.
- **Inverter State** (38 states): "Stand By", "Checking Grid", "Run", etc.
- **Alarm State** (65 states): "No Alarm", "Over Temp.", "Grid Fail", etc.

### Error Handling

Custom exception hierarchy matching the integration:

- `VSNClientError` (base)
- `VSNConnectionError` - Network/connectivity failures
- `VSNAuthenticationError` - Authentication failures (401/403)
- `VSNDetectionError` - Model detection failures
- `VSNUnsupportedDeviceError` - Device doesn't support REST API (404)

## Output Files

The script generates these JSON files in the current directory:

| File | Description |
|------|-------------|
| `{model}_discovery.json` | Device discovery results with all metadata |
| `{model}_status.json` | Raw `/v1/status` response |
| `{model}_livedata.json` | Raw `/v1/livedata` response |
| `{model}_feeds.json` | Raw `/v1/feeds` response |
| `{model}_normalized.json` | Normalized data with HA metadata |

Where `{model}` is `vsn300` or `vsn700`.

## Troubleshooting

### Connection Refused

- Verify the datalogger is powered on and connected to the network
- Check that port 80 is accessible
- Try pinging the device first
- The script performs a socket check before HTTP requests for fast failure

### Authentication Failed

- VSN300: Default credentials are usually `guest` / `""` (empty password)
- VSN700: Check your admin credentials
- The script auto-detects the authentication method

### Timeout Errors

- Increase timeout with `--timeout 30`
- Check network connectivity
- VSN300 devices can be slow to respond

### Unsupported Device (404)

- The device doesn't have VSN REST API endpoints
- This tool requires VSN300 or VSN700 dataloggers

## Related

- Main integration: `custom_components/abb_fimer_pvi_vsn_rest/`
- Integration test script: `scripts/test_vsn_client.py`
- Test data: `docs/vsn-data/`
- Client library: `custom_components/abb_fimer_pvi_vsn_rest/abb_fimer_vsn_rest_client/`
