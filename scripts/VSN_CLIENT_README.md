# VSN Client - Self-Contained Testing Script

## Overview

`vsn_client.py` is a self-contained Python script for testing ABB/FIMER VSN300
and VSN700 dataloggers without needing to install the full Home Assistant
integration.

## Features

✅ **Self-contained** - All code in a single file
✅ **Minimal dependencies** - Only requires Python standard library + aiohttp
✅ **Auto-detection** - Automatically detects VSN300 or VSN700
✅ **All endpoints** - Tests /v1/status, /v1/livedata, and /v1/feeds
✅ **Data normalization** - Transforms VSN data to Home Assistant format using SunSpec mapping
✅ **Easy to share** - Send single file to users for testing

## Requirements

- **Python 3.9 or higher**
- **aiohttp** library
- **Internet connection** (required for data normalization feature)

Install aiohttp:

```bash
pip install aiohttp
```

## Usage

### Basic Usage

```bash
python vsn_client.py <host>
```

### Examples

With IP address:

```bash
python vsn_client.py 192.168.1.100
```

With hostname:

```bash
python vsn_client.py abb-vsn300.axel.dom
```

The script automatically adds `http://` prefix if not provided.

## What It Tests

The script performs 5 tests:

1. **Device Detection** - Identifies if device is VSN300 or VSN700
2. **System Information** (/v1/status) - Retrieves device info, firmware version, network config
3. **Live Data** (/v1/livedata) - Fetches real-time measurements from inverters
4. **Data Normalization** - Transforms raw VSN data to Home Assistant entity format (requires internet)
5. **Feed Metadata** (/v1/feeds) - Gets feed definitions and configuration

## Output

The script creates up to 4 JSON files in the current directory:

- `vsn300_status.json` or `vsn700_status.json` - System information
- `vsn300_livedata.json` or `vsn700_livedata.json` - Raw live sensor data
- `vsn300_normalized.json` or `vsn700_normalized.json` - Normalized HA entity data (if internet available)
- `vsn300_feeds.json` or `vsn700_feeds.json` - Feed metadata

## Example Output

```text
================================================================================
VSN REST Client - Device Test
Host: abb-vsn300.axel.dom
Base URL: http://abb-vsn300.axel.dom
Username: guest (default)
Password: (empty)
================================================================================

[TEST 1] Device Detection
--------------------------------------------------------------------------------
✓ Device detected: VSN300

[TEST 2] /v1/status - System Information
--------------------------------------------------------------------------------
✓ Status endpoint successful
  - logger.sn: 111033-3N16-1421
  - device.invID: 077909-3G82-3112
  - device.modelDesc: PVI-10.0-OUTD
  - fw.release_number: 1.9.2
  - Saved to: vsn300_status.json

[TEST 3] /v1/livedata - Live Data
--------------------------------------------------------------------------------
✓ Livedata endpoint successful
  - Number of devices: 2
  - Device IDs: ['077909-3G82-3112', 'a4:06:e9:7f:42:49']
  - Saved to: vsn300_livedata.json

[TEST 3b] Data Normalization
--------------------------------------------------------------------------------
✓ Data normalized successfully
  - Normalized points: 53
  - Saved to: vsn300_normalized.json

[TEST 4] /v1/feeds - Feed Metadata
--------------------------------------------------------------------------------
✓ Feeds endpoint successful
  - Number of feeds: 2
  - Saved to: vsn300_feeds.json

================================================================================
TEST SUMMARY
================================================================================
✓ Device model: VSN300
✓ All 3 endpoints tested successfully!
✓ /v1/status: OK
✓ /v1/livedata: OK (2 devices)
✓ /v1/livedata normalized: OK (53 points)
✓ /v1/feeds: OK

Output files created:
  - vsn300_status.json
  - vsn300_livedata.json
  - vsn300_normalized.json
  - vsn300_feeds.json
================================================================================
```

## Data Normalization

The script automatically normalizes raw VSN data to Home Assistant entity format using a mapping file from GitHub. This transformation:

- Maps VSN-specific point names to standard SunSpec names
- Adds metadata (units, labels, descriptions, device classes)
- Creates properly structured HA entities
- Handles differences between VSN300 and VSN700 naming

**Requirements:**

- Internet connection to download the mapping file from GitHub
- If the mapping file is not yet available in the repository, normalization will be skipped with a warning

**Example normalized output:**

```json
{
  "devices": {
    "077909-3G82-3112": {
      "device_type": "inverter",
      "points": {
        "abb_m103_w": {
          "value": 8524.0,
          "units": "W",
          "label": "Watts",
          "description": "AC Power",
          "device_class": "power",
          "state_class": "measurement"
        }
      }
    }
  }
}
```

## Authentication

The script uses **guest** account with **empty password** by default, which should work for most VSN devices.

### VSN300

- Uses HTTP Digest authentication with custom X-Digest header
- Challenge-response flow for each request

### VSN700

- Uses HTTP Basic authentication
- Credentials sent with each request

## Troubleshooting

### "ERROR: aiohttp is required"

Install aiohttp:

```bash
pip install aiohttp
```

### Connection Timeout

- Check network connectivity to the device
- Verify the IP address or hostname is correct
- Ensure device is powered on and accessible

### Authentication Failed

- Default guest account should work for most devices
- Check if device requires different credentials
- Some devices may have authentication disabled

### 401 Unauthorized

- Device may require admin credentials
- Check firewall settings
- Verify device firmware version supports REST API

### Normalization Skipped

If you see "Normalization will be skipped":

- Check internet connectivity
- The mapping file may not be available yet in the GitHub repository
- This doesn't affect the main tests - raw data is still saved
- The normalized output is optional and mainly useful for integration development

## Sending to Users

To share with users for testing:

1. Send them the `vsn_client.py` file
2. Provide installation instructions (Python 3.9+ and aiohttp)
3. Give them the command: `python vsn_client.py <their_device_ip>`
4. Ask them to send back the generated JSON files (3-4 files depending on internet availability)

## Technical Details

### Supported Models

- **VSN300** - WiFi Logger Card (older model)
- **VSN700** - VSN700 datalogger (newer model)

### API Endpoints

- `/v1/status` - Device and system status
- `/v1/livedata` - Real-time measurements from inverters
- `/v1/feeds` - Feed configuration and metadata

### Protocol Differences

| Feature | VSN300 | VSN700 |
|---------|--------|--------|
| Auth Method | Digest | Basic |
| Header Name | Authorization | Authorization |
| Auth Scheme | X-Digest | Basic |
| Challenge | Yes (401) | No |
| Endpoints | Same (/v1/*) | Same (/v1/*) |

## License

Part of the ha-abb-fimer-pvi-vsn-rest Home Assistant integration project.

## Support

For issues or questions, please open an issue on the GitHub repository.
