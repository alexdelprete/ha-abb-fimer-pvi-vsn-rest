# VSN-SunSpec Point Mapping Generator

A self-contained tool for generating comprehensive point mappings between VSN300/VSN700 dataloggers and SunSpec models for the ABB FIMER PVI VSN REST Home Assistant integration.

## Overview

This generator creates a complete mapping file that:
- Maps VSN300/VSN700 REST API points to SunSpec normalized names
- Includes metadata like labels, descriptions, units, and Home Assistant device classes
- Tracks which SunSpec models each point belongs to (M1, M103, M160, M203, M802, M64061)
- Identifies VSN-only and ABB proprietary points
- Processes data from `/livedata`, `/feeds`, and `/status` endpoints

## Directory Structure

```
vsn-mapping-generator/
├── generate_mapping.py           # Main mapping generator script
├── convert_to_json.py            # Excel to JSON converter
├── README.md                     # This file
├── data/                         # Input data files
│   ├── vsn300/
│   │   ├── livedata.json        # VSN300 livedata endpoint data
│   │   ├── feeds.json           # VSN300 feeds metadata
│   │   └── status.json          # VSN300 status endpoint data
│   ├── vsn700/
│   │   ├── livedata.json        # VSN700 livedata endpoint data
│   │   ├── feeds.json           # VSN700 feeds metadata
│   │   └── status.json          # VSN700 status endpoint data
│   └── sunspec/
│       ├── models_workbook.xlsx # Official SunSpec model definitions
│       └── ABB_SunSpec_Modbus.xlsx # ABB proprietary M64061 definitions
└── output/
    ├── vsn-sunspec-point-mapping.xlsx  # Generated Excel mapping
    └── vsn-sunspec-point-mapping.json  # Generated JSON for integration
```

## Usage

### 1. Generate the Mapping Excel File

```bash
python generate_mapping.py
```

This will:
- Load all VSN data from the `data/` directory
- Load SunSpec model definitions
- Process status endpoint data
- Generate a comprehensive Excel file with 26 columns
- Create three sheets: All Points, Summary, Changelog

### 2. Convert Excel to JSON

```bash
python convert_to_json.py
```

This will:
- Read the generated Excel file
- Convert it to JSON format
- Save to `output/vsn-sunspec-point-mapping.json`
- Copy to the integration's data folder

## Output Format

### Excel Columns (26 total)

1. **Model Flags** (9 columns): M1, M103, M160, M203, M802, M64061, VSN300_Only, VSN700_Only, ABB_Proprietary
2. **Point Names** (3 columns): REST Name (VSN700), REST Name (VSN300), SunSpec Normalized Name
3. **HA Integration** (4 columns): HA Name, HA Display Name, HA Unit of Measurement, HA State Class, HA Device Class
4. **Metadata** (5 columns): Label, Description, Category, Entity Category, Available in Modbus
5. **Tracking** (3 columns): In /livedata, In /feeds, Data Source
6. **Notes** (1 column): Model_Notes

### JSON Structure

```json
[
  {
    "models": ["M103"],
    "REST Name (VSN700)": "Pgrid",
    "REST Name (VSN300)": "m103_1_W",
    "SunSpec Normalized Name": "W",
    "HA Name": "watts",
    "Label": "Active Power",
    "Description": "Total active power",
    "HA Display Name": "Grid Power",
    "Category": "Inverter",
    "HA Unit of Measurement": "W",
    "HA State Class": "measurement",
    "HA Device Class": "power",
    ...
  }
]
```

## Data Sources

### VSN Data Files
- **livedata.json**: Real-time measurement points from inverters, meters, and batteries
- **feeds.json**: Metadata including titles, units, and descriptions
- **status.json**: Device information, firmware versions, network configuration

### SunSpec Models
- **models_workbook.xlsx**: Official SunSpec Alliance model definitions (M1, M103, M160, etc.)
- **ABB_SunSpec_Modbus.xlsx**: ABB/FIMER proprietary M64061 model points

## Features

### Status Endpoint Processing (v2.0.0+)
The generator now processes `/status` endpoint data, extracting:
- Device information (model, serial number, firmware versions)
- Network configuration (IP addresses, WLAN status)
- Logger information (board model, hostname)

### Automatic Categorization
Points are automatically categorized into:
- Inverter
- Energy Counter
- Battery
- Meter
- Device Info
- Network
- Status
- System Monitoring
- Datalogger

### Data Source Priority
Descriptions are selected using a 4-tier priority system:
1. SunSpec official descriptions
2. VSN feeds titles (if descriptive)
3. Enhanced generated descriptions
4. Label fallback

### Deduplication
Points with the same SunSpec normalized name are merged, preserving the best available metadata from all sources.

## Updating Data

### To Update VSN Data
1. Export new data from VSN300/VSN700 devices
2. Place JSON files in appropriate `data/vsn300/` or `data/vsn700/` directories
3. Run `generate_mapping.py`

### To Update SunSpec Models
1. Download latest model workbook from SunSpec Alliance
2. Replace `data/sunspec/models_workbook.xlsx`
3. Run `generate_mapping.py`

## Version History

- **v2.0.0** (2024-11-02): Self-contained generator with status.json processing
- **v1.0.0** (2024-11-02): Initial comprehensive generator replacing multi-script workflow

## Integration

The generated `vsn-sunspec-point-mapping.json` file is used by the Home Assistant integration to:
- Map VSN REST API responses to standardized entities
- Apply proper units and device classes
- Normalize point names across VSN300 and VSN700

## Contributing

When adding new points or models:
1. Update the appropriate data files
2. Run both generator scripts
3. Verify the output in the Excel file
4. Test with the Home Assistant integration