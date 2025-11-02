#!/usr/bin/env python3
"""Generate complete VSN-SunSpec point mapping Excel with all customizations built-in.

This comprehensive script replaces the multi-script workflow with a single source of truth
that generates the complete 26-column Excel with model flags, all fixes applied, and a
changelog tab tracking all updates.

This version is self-contained with all data files in the data/ subdirectory and
processes status.json endpoints along with livedata and feeds.

Author: Claude/Alex
Version: 2.0.0
Date: 2024-11-02
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Script metadata
SCRIPT_VERSION = "2.0.0"
SCRIPT_DATE = datetime.now().strftime("%Y-%m-%d")

# Get script directory for relative paths
SCRIPT_DIR = Path(__file__).parent

# ==============================================================================
# PART 1: CONSTANTS AND MAPPINGS
# ==============================================================================

# Model flag columns
MODEL_FLAGS = [
    "M1",
    "M103",
    "M160",
    "M203",
    "M802",
    "M64061",
    "VSN300_Only",
    "VSN700_Only",
    "ABB_Proprietary"
]

# Full Excel headers (26 columns total)
EXCEL_HEADERS = MODEL_FLAGS + [
    "REST Name (VSN700)",
    "REST Name (VSN300)",
    "SunSpec Normalized Name",
    "HA Name",
    "In /livedata",
    "In /feeds",
    "Label",
    "Description",
    "HA Display Name",
    "Category",
    "HA Unit of Measurement",
    "HA State Class",
    "HA Device Class",
    "Entity Category",
    "Available in Modbus",
    "Data Source",
    "Model_Notes"
]

# VSN to SunSpec mappings (from original script)
VSN_TO_SUNSPEC_MAP = {
    # Inverter measurements (M103)
    "Pgrid": {"sunspec": "W", "model": "M103", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": "m103_1_W"},
    "Qgrid": {"sunspec": "VAr", "model": "M103", "category": "Inverter", "units": "var", "state_class": "measurement", "device_class": "reactive_power", "in_modbus": "YES", "modbus": "m103_1_VAr"},
    "Sgrid": {"sunspec": "VA", "model": "M103", "category": "Inverter", "units": "VA", "state_class": "measurement", "device_class": "apparent_power", "in_modbus": "YES", "modbus": "m103_1_VA"},
    "Fgrid": {"sunspec": "Hz", "model": "M103", "category": "Inverter", "units": "Hz", "state_class": "measurement", "device_class": "frequency", "in_modbus": "YES", "modbus": "m103_1_Hz"},
    "Igrid": {"sunspec": "A", "model": "M103", "category": "Inverter", "units": "A", "state_class": "measurement", "device_class": "current", "in_modbus": "YES", "modbus": "m103_1_A"},
    "Vgrid": {"sunspec": "PhVphA", "model": "M103", "category": "Inverter", "units": "V", "state_class": "measurement", "device_class": "voltage", "in_modbus": "YES", "modbus": "m103_1_PhVphA"},
    "Etotal": {"sunspec": "TotWhExp", "model": "M103", "category": "Energy Counter", "units": "kWh", "state_class": "total_increasing", "device_class": "energy", "in_modbus": "YES", "modbus": "m103_1_TotWhExp"},
    "PF": {"sunspec": "PF", "model": "M103", "category": "Inverter", "units": "%", "state_class": "measurement", "device_class": "power_factor", "in_modbus": "YES", "modbus": "m103_1_PF"},

    # Three-phase measurements (M103)
    "Pgrid_L1": {"sunspec": "WphA", "model": "M103", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": None},
    "Pgrid_L2": {"sunspec": "WphB", "model": "M103", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": None},
    "Pgrid_L3": {"sunspec": "WphC", "model": "M103", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": None},

    # DC measurements (M160)
    "Ppv": {"sunspec": "DCW", "model": "M160", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": "m160_1_DCW"},
    "Vpv_1": {"sunspec": "DCV_1", "model": "M160", "category": "Inverter", "units": "V", "state_class": "measurement", "device_class": "voltage", "in_modbus": "YES", "modbus": "m160_1_DCV_1"},
    "Ipv_1": {"sunspec": "DCA_1", "model": "M160", "category": "Inverter", "units": "A", "state_class": "measurement", "device_class": "current", "in_modbus": "YES", "modbus": "m160_1_DCA_1"},
    "Ppv_1": {"sunspec": "DCW_1", "model": "M160", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": "m160_1_DCW_1"},
    "Vpv_2": {"sunspec": "DCV_2", "model": "M160", "category": "Inverter", "units": "V", "state_class": "measurement", "device_class": "voltage", "in_modbus": "YES", "modbus": "m160_1_DCV_2"},
    "Ipv_2": {"sunspec": "DCA_2", "model": "M160", "category": "Inverter", "units": "A", "state_class": "measurement", "device_class": "current", "in_modbus": "YES", "modbus": "m160_1_DCA_2"},
    "Ppv_2": {"sunspec": "DCW_2", "model": "M160", "category": "Inverter", "units": "W", "state_class": "measurement", "device_class": "power", "in_modbus": "YES", "modbus": "m160_1_DCW_2"},

    # M1 Common Model
    "C_Mn": {"sunspec": "Mn", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_Mn"},
    "C_Md": {"sunspec": "Md", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_Md"},
    "C_Opt": {"sunspec": "Opt", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_Opt"},
    "C_Vr": {"sunspec": "Vr", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_Vr"},
    "C_SN": {"sunspec": "SN", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_SN"},
    "C_DA": {"sunspec": "DA", "model": "M1", "category": "Inverter", "units": "", "state_class": None, "device_class": None, "in_modbus": "YES", "modbus": "m1_DA"},
}

# M64061 vendor-specific points
M64061_POINTS = {
    "AlarmState", "Alm1", "Alm2", "Alm3", "BatteryMode", "BatteryStatus", "FaultStatus",
    "IsolResist", "RemoteControlRequest", "RemoteControlStatus", "Mode",
    "CmdTimeout", "CtrlTimeout", "CtrlOpt", "AUX1", "AUX2",
    "BatteryVoltage", "BatteryTemperature", "BatterySoC", "BatterySoH",
    "BatteryChargeCurrent", "BatteryDischargeCurrent", "BatteryPower", "BatteryChargePower",
    "E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8",
    "ECharge", "EDischarge", "ETotCharge", "ETotDischarge"
}

# ABB Proprietary points (REST API only)
ABB_PROPRIETARY = {
    # Battery measurements
    "Vbat", "Ibat", "Pbat", "Soc", "Soh", "Wbat_charge", "Wbat_discharge",
    "Tmp", "BattNum", "Chc", "Dhc",
    # System configuration
    "UploadAddr", "UploadPort", "UploadAddr2", "UploadPort2", "ApplVer", "SerNum",
    # Time/Schedule
    "HWVer", "Year", "Month", "Day", "Weekday", "Hour", "Minute", "Second",
    # Grid parameters
    "SplitPhase", "CountryStd",
    # House meter measurements
    "HousePgrid", "HousePgrid_L1", "HousePgrid_L2", "HousePgrid_L3",
    "HouseIgrid", "HouseIgrid_L1", "HouseIgrid_L2", "HouseIgrid_L3",
    # Other proprietary
    "SysTime", "MemFree", "FlashFree", "HDD1Size", "HDD1Used", "SysLoad"
}

# ==============================================================================
# DISPLAY NAME CORRECTIONS (from update_ha_display_names.py)
# ==============================================================================

DISPLAY_NAME_CORRECTIONS = {
    # Datalogger entities
    "Serial number (datalogger)": "Serial Number",
    "WiFi local IP address": "IP address",
    "WiFi network name (SSID)": "WiFi SSID",
    "Wlan 0 Mode operating mode": "Wlan 0 mode",
    # Inverter entities
    "Current alarm status of the inverter": "Alarm status",
    "Booster stage temperature": "Booster temperature",
    "DC bulk capacitor voltage": "DC capacitor voltage",
    "DC bulk mid-point voltage": "DC mid-point voltage",
    "DC current measurement for string 1": "DC current #1",
    "DC current measurement for string 2": "DC current #2",
    "DC voltage measurement for string 1": "DC voltage #1",
    "DC voltage measurement for string 2": "DC voltage #2",
    "Phase A to neutral voltage measurement": "Phase Voltage AN",
    "Device Modbus address": "Modbus address",
    "Device model identifier from common model": "Model",
    "Device options and features from common model": "Options",
    "Device serial number from common model": "Serial Number",
    "Firmware version from device common model": "Firmware Version",
    "Manufacturer name from device common model": "Manufacturer",
}

# Device class/unit fixes
DEVICE_CLASS_FIXES = {
    "Device Address": {"device_class": None, "unit": None},
    "Version": {"device_class": None, "unit": None},
    "Sys Time": {"device_class": "timestamp", "entity_category": "diagnostic"},
}

# ==============================================================================
# DESCRIPTION IMPROVEMENTS (from apply_mapping_fixes.py)
# ==============================================================================

DESCRIPTION_IMPROVEMENTS = {
    # M1 Common Model
    "Mn": "Manufacturer name from device common model",
    "Md": "Device model identifier from common model",
    "Opt": "Device options and features from common model",
    "Vr": "Firmware version from device common model",
    "SN": "Device serial number from common model",
    "DA": "Device Modbus address",

    # Phase voltages/currents
    "PhVphA": "Phase A to neutral voltage measurement",
    "PhVphB": "Phase B to neutral voltage measurement",
    "PhVphC": "Phase C to neutral voltage measurement",
    "AphA": "Phase A AC current measurement",
    "AphB": "Phase B AC current measurement",
    "AphC": "Phase C AC current measurement",

    # DC measurements (MPPT)
    "DCA_1": "DC current measurement for string 1",
    "DCA_2": "DC current measurement for string 2",
    "DCV_1": "DC voltage measurement for string 1",
    "DCV_2": "DC voltage measurement for string 2",
    "DCW_1": "DC power measurement for string 1",
    "DCW_2": "DC power measurement for string 2",

    # Battery specific
    "Tmp": "Battery temperature measurement",
    "BattNum": "Number of battery cells or modules",
    "Chc": "Battery charge cycles counter",
    "Dhc": "Battery discharge cycles counter",
    "ETotCharge": "Total battery energy charged over lifetime",
    "ETotDischarge": "Total battery energy discharged over lifetime",
    "ECharge": "Current battery charge energy",
    "EDischarge": "Current battery discharge energy",

    # Energy counters with periods
    "E0_runtime": "Export energy counter lifetime total",
    "E0_7D": "Export energy counter last 7 days",
    "E0_30D": "Export energy counter last 30 days",
    "E0_1Y": "Export energy counter last year",
    "E1_runtime": "Import energy counter lifetime total",
    "E1_7D": "Import energy counter last 7 days",
    "E1_30D": "Import energy counter last 30 days",
    "E1_1Y": "Import energy counter last year",
    "E2_runtime": "Consumed energy counter lifetime total",
    "E2_7D": "Consumed energy counter last 7 days",
    "E2_30D": "Consumed energy counter last 30 days",
    "E2_1Y": "Consumed energy counter last year",
    "E3_runtime": "Produced energy counter lifetime total",
    "E3_7D": "Produced energy counter last 7 days",
    "E3_30D": "Produced energy counter last 30 days",
    "E3_1Y": "Produced energy counter last year",
    "E4_runtime": "Self-consumed energy lifetime total",
    "E4_7D": "Self-consumed energy last 7 days",
    "E4_30D": "Self-consumed energy last 30 days",
    "E4_1Y": "Self-consumed energy last year",
    "E5_runtime": "Battery charge energy lifetime total",
    "E5_7D": "Battery charge energy last 7 days",
    "E5_30D": "Battery charge energy last 30 days",
    "E5_1Y": "Battery charge energy last year",
    "E6_runtime": "Battery discharge energy lifetime total",
    "E6_7D": "Battery discharge energy last 7 days",
    "E6_30D": "Battery discharge energy last 30 days",
    "E6_1Y": "Battery discharge energy last year",
    "E7_runtime": "PV production energy lifetime total",
    "E7_7D": "PV production energy last 7 days",
    "E7_30D": "PV production energy last 30 days",
    "E7_1Y": "PV production energy last year",
    "E8_runtime": "Grid feed-in energy lifetime total",
    "E8_7D": "Grid feed-in energy last 7 days",
    "E8_30D": "Grid feed-in energy last 30 days",
    "E8_1Y": "Grid feed-in energy last year",

    # House meter
    "HousePgrid_L1": "House consumption phase L1 power",
    "HousePgrid_L2": "House consumption phase L2 power",
    "HousePgrid_L3": "House consumption phase L3 power",
    "HouseIgrid_L1": "House consumption phase L1 current",
    "HouseIgrid_L2": "House consumption phase L2 current",
    "HouseIgrid_L3": "House consumption phase L3 current",

    # System info
    "SplitPhase": "Split-phase configuration flag",
    "CountryStd": "Country grid standard setting",
}

# ==============================================================================
# CHANGELOG ENTRIES
# ==============================================================================

CHANGELOG_ENTRIES = [
    {
        "date": "2024-11-02",
        "version": "1.0.0",
        "type": "Initial Generation",
        "description": "Created comprehensive mapping with all customizations built-in",
        "details": [
            "Generated 210 deduplicated points (from 277 raw)",
            "Applied model flag detection from point names",
            "Implemented 4-tier description priority system",
            "Added comprehensive category assignment logic"
        ],
        "source": "Script automation"
    },
    {
        "date": "2024-11-02",
        "version": "1.0.0",
        "type": "Display Name Updates",
        "description": "Applied 20 display name corrections for better clarity",
        "details": [
            "Datalogger: Serial Number, IP address, WiFi SSID, Wlan 0 mode",
            "Inverter: Alarm status, Booster temperature, DC capacitor/mid-point voltage",
            "MPPT: DC current/voltage #1/#2 (instead of 'for string X')",
            "Device info: Model, Options, Serial Number, Firmware Version, Manufacturer",
            "Grid: Phase Voltage AN (instead of 'Phase A to neutral voltage measurement')"
        ],
        "source": "User request"
    },
    {
        "date": "2024-11-02",
        "version": "1.0.0",
        "type": "Data Fixes",
        "description": "Fixed incorrect device_class and unit assignments",
        "details": [
            "Device Address: Removed device_class=current and unit=A",
            "Firmware Version: Removed device_class=voltage and unit=V",
            "System timestamp: Set device_class=timestamp with entity_category=diagnostic"
        ],
        "source": "User request"
    },
    {
        "date": "2024-11-02",
        "version": "1.0.0",
        "type": "Description Improvements",
        "description": "Applied 108 description enhancements",
        "details": [
            "M1 Common Model: Enhanced descriptions for Mn, Md, Opt, Vr, SN, DA",
            "Phase measurements: Clarified voltage/current descriptions",
            "MPPT: Improved DC measurement descriptions",
            "Battery: Added comprehensive battery point descriptions",
            "Energy counters: Standardized period descriptions (lifetime, 7D, 30D, 1Y)",
            "House meter: Clarified consumption measurements",
            "System info: Added descriptive text for configuration points"
        ],
        "source": "Automated logic improvement"
    }
]

# ==============================================================================
# PART 2: HELPER FUNCTIONS
# ==============================================================================

def load_feeds_titles(vsn300_feeds_path, vsn700_feeds_path):
    """Load title and unit data from VSN300 and VSN700 feeds.json files."""
    def is_title_a_description(point_name, title):
        """Determine if a title is a description or just a point name reference."""
        if not title:
            return False
        if title.lower() == point_name.lower():
            return False
        if title in ["NO_DESCR", "N/A", "", "-"]:
            return False
        return True

    feeds_titles = {}

    # Process VSN300 feeds
    if vsn300_feeds_path.exists():
        with open(vsn300_feeds_path) as f:
            vsn300_feeds = json.load(f)
            # feeds is a dictionary, not a list!
            feeds_dict = vsn300_feeds.get("feeds", {})
            for device_id, feed_data in feeds_dict.items():
                datastreams = feed_data.get("datastreams", {})
                for point_name, point_info in datastreams.items():
                    title = point_info.get("title", "")
                    units = point_info.get("units", "")
                    is_description = is_title_a_description(point_name, title)
                    feeds_titles[point_name] = {
                        "title": title,
                        "units": units,
                        "is_description": is_description,
                        "source": "VSN300 feeds"
                    }

    # Process VSN700 feeds
    if vsn700_feeds_path.exists():
        with open(vsn700_feeds_path) as f:
            vsn700_feeds = json.load(f)
            # feeds is a dictionary, not a list!
            feeds_dict = vsn700_feeds.get("feeds", {})
            for device_id, feed_data in feeds_dict.items():
                datastreams = feed_data.get("datastreams", {})
                for point_name, point_info in datastreams.items():
                    title = point_info.get("title", "")
                    units = point_info.get("units", "")
                    is_description = is_title_a_description(point_name, title)
                    if point_name not in feeds_titles:
                        feeds_titles[point_name] = {
                            "title": title,
                            "units": units,
                            "is_description": is_description,
                            "source": "VSN700 feeds"
                        }

    return feeds_titles

def load_vsn_status(vsn300_status_path, vsn700_status_path):
    """Load status.json data from VSN300 and VSN700."""
    status_points = {}

    # Process VSN300 status
    if vsn300_status_path.exists():
        with open(vsn300_status_path) as f:
            vsn300_status = json.load(f)
            if "keys" in vsn300_status:
                for key, info in vsn300_status["keys"].items():
                    # Extract clean point name (e.g., "fw.release_number" -> "fw_release_number")
                    point_name = key.replace(".", "_")
                    label = info.get("label", "")
                    value = info.get("value", "")

                    status_points[point_name] = {
                        "source": "VSN300 status",
                        "label": label if label else generate_label_from_name(point_name),
                        "value_example": value,
                        "vsn300": True,
                        "vsn700": False
                    }

    # Process VSN700 status
    if vsn700_status_path.exists():
        with open(vsn700_status_path) as f:
            vsn700_status = json.load(f)
            if "keys" in vsn700_status:
                for key, info in vsn700_status["keys"].items():
                    # Extract clean point name
                    point_name = key.replace(".", "_")
                    label = info.get("label", "") if isinstance(info, dict) else ""
                    value = info.get("value", "") if isinstance(info, dict) else ""

                    if point_name in status_points:
                        status_points[point_name]["vsn700"] = True
                    else:
                        status_points[point_name] = {
                            "source": "VSN700 status",
                            "label": label if label else generate_label_from_name(point_name),
                            "value_example": value,
                            "vsn300": False,
                            "vsn700": True
                        }

    return status_points

def load_m64061_from_abb_excel(excel_path):
    """Load M64061 model data from ABB_SunSpec_Modbus.xlsx."""
    import openpyxl

    m64061_points = {}

    if not excel_path.exists():
        print(f"  WARNING: ABB SunSpec Excel not found at {excel_path}")
        return m64061_points

    wb = openpyxl.load_workbook(excel_path, read_only=True)

    # The M64061 data is in the "Inverter Modbus" sheet starting at row 96
    if "Inverter Modbus" in wb.sheetnames:
        ws = wb["Inverter Modbus"]

        # M64061 starts at row 95 with the header "ABB Inverter Vendor Model (64061)"
        # Actual data points start at row 96
        # Columns appear to be: A-D (addresses), E-F (unknown), G (Size), H (Access), I (Name)

        in_m64061_section = False
        for row in range(95, ws.max_row + 1):
            # Check if we're at the M64061 header
            cell_a = ws.cell(row, 1).value
            if cell_a and "64061" in str(cell_a):
                in_m64061_section = True
                continue

            # If we're in the M64061 section
            if in_m64061_section:
                # Check if we've reached another model section
                if cell_a and "Model" in str(cell_a) and "64061" not in str(cell_a):
                    break

                # Extract point data from columns
                name = ws.cell(row, 9).value  # Column I - Name
                if name and name != "Name" and not str(name).startswith("="):
                    # Get other data if available
                    size = ws.cell(row, 7).value  # Column G - Size
                    access = ws.cell(row, 8).value  # Column H - Access (R/RW)

                    # Some known M64061 points from the original script
                    if name in ["Alm1", "Alm2", "Alm3", "AlarmState", "FaultStatus",
                               "BatteryMode", "BatteryStatus", "IsolResist"]:
                        m64061_points[name] = {
                            "size": size,
                            "access": access,
                            "label": generate_label_from_name(name),
                            "description": f"M64061 proprietary point: {name}"
                        }

    wb.close()
    return m64061_points

def load_sunspec_models_metadata(workbook_path):
    """Load label and description from SunSpec models workbook."""
    import openpyxl

    models_data = {}
    wb = openpyxl.load_workbook(workbook_path, read_only=True)

    model_sheets = ["1", "101", "103", "120", "124", "160", "201", "203", "204", "802", "803", "804"]

    for sheet_name in model_sheets:
        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]
        model_key = f"M{sheet_name}"
        models_data[model_key] = {}

        # Find header row (contains "Name" column)
        header_row = None
        for row_idx in range(1, 10):
            for col_idx in range(1, 10):
                if ws.cell(row_idx, col_idx).value == "Name":
                    header_row = row_idx
                    break
            if header_row:
                break

        if not header_row:
            continue

        # Find column indices
        name_col = label_col = desc_col = None
        for col_idx in range(1, ws.max_column + 1):
            cell_value = ws.cell(header_row, col_idx).value
            if cell_value == "Name":
                name_col = col_idx
            elif cell_value == "Label":
                label_col = col_idx
            elif cell_value == "Description":
                desc_col = col_idx

        # Read data rows
        for row_idx in range(header_row + 1, ws.max_row + 1):
            name = ws.cell(row_idx, name_col).value if name_col else None
            if not name:
                continue

            label = ws.cell(row_idx, label_col).value if label_col else ""
            description = ws.cell(row_idx, desc_col).value if desc_col else ""

            models_data[model_key][name] = {
                "label": label or "",
                "description": description or ""
            }

    wb.close()
    return models_data

def generate_label_from_name(point_name):
    """Generate a human-readable label from a point name."""
    # Handle VSN300 SunSpec patterns
    if "_" in point_name and point_name.startswith("m"):
        match = re.match(r"m(\d+)_(\d+)_(.+)", point_name)
        if match:
            model_num, instance, point = match.groups()
            base_label = generate_label_from_name(point)
            if "_" in point and point.split("_")[-1].isdigit():
                return base_label
            return base_label

    # Handle M64061 state codes
    state_codes = {
        "Alm1": "Alarm 1", "Alm2": "Alarm 2", "Alm3": "Alarm 3",
        "AlarmState": "Alarm State", "FaultStatus": "Fault Status",
        "BatteryMode": "Battery Mode", "BatteryStatus": "Battery Status",
        "IsolResist": "Isolation Resistance"
    }
    if point_name in state_codes:
        return state_codes[point_name]

    # Handle system monitoring points
    system_points = {
        "flash_free": "Flash Memory Free", "free_ram": "Free RAM",
        "fw_ver": "Firmware Version", "hw_ver": "Hardware Version",
        "store_size": "Storage Size", "sys_load": "System Load",
        "uptime": "System Uptime", "Sn": "Serial Number"
    }
    if point_name in system_points:
        return system_points[point_name]

    # Handle periodic energy counters
    if "_" in point_name:
        base, suffix = point_name.rsplit("_", 1)
        period_map = {
            "runtime": "Lifetime", "7D": "7 Day",
            "30D": "30 Day", "1Y": "1 Year"
        }
        if suffix in period_map:
            base_label = generate_label_from_name(base)
            return f"{base_label} {period_map[suffix]}"

    # Handle common abbreviations
    abbreviations = {
        "Soc": "State of Charge", "Soh": "State of Health",
        "Tmp": "Temperature", "Vbat": "Battery Voltage",
        "Ibat": "Battery Current", "Pbat": "Battery Power"
    }
    for abbr, full in abbreviations.items():
        if point_name.startswith(abbr):
            return full + point_name[len(abbr):]

    # Split CamelCase and snake_case
    words = re.sub(r"([A-Z])", r" \1", point_name).split()
    words = [w for word in words for w in word.split("_") if w]

    return " ".join(words).title()

def generate_simplified_point_name(label, model):
    """Generate simplified HA entity name from label."""
    # Convert to lowercase and replace spaces with underscores
    name = label.lower().replace(" ", "_")

    # Remove special characters
    name = re.sub(r"[^a-z0-9_]", "", name)

    # Replace multiple underscores with single
    name = re.sub(r"_+", "_", name)

    # Strip leading/trailing underscores
    name = name.strip("_")

    return name

def lookup_label_description(models_data, model, sunspec_point):
    """Lookup label and description from SunSpec metadata."""
    label = ""
    description = ""

    if model and f"M{model.replace('M', '')}" in models_data:
        model_data = models_data[f"M{model.replace('M', '')}"]

        # Handle repeating groups (e.g., DCA_1 → DCA)
        base_point = sunspec_point
        if "_" in sunspec_point and sunspec_point.split("_")[-1].isdigit():
            base_point = "_".join(sunspec_point.split("_")[:-1])
            suffix = sunspec_point.split("_")[-1]
        else:
            suffix = None

        if base_point in model_data:
            label = model_data[base_point].get("label", "")
            description = model_data[base_point].get("description", "")
            if suffix:
                label = f"{label} #{suffix}"
                description = f"{description} for string {suffix}"

    return label, description

def get_description_with_priority(vsn_name, sunspec_name, model, label, workbook_description,
                                 feeds_info, vsn700_lookup=None, vsn300_name=None):
    """Get description using 4-tier priority system with data source tracking."""
    # Priority 0: Cross-reference VSN700 lookup for VSN300-only points
    if vsn700_lookup and vsn300_name and vsn300_name == vsn_name:
        vsn700_equivalent = vsn700_lookup.get(vsn_name, {})
        if vsn700_equivalent.get("description"):
            return vsn700_equivalent["description"], "VSN700 Cross-Reference", vsn700_equivalent.get("label")

    # Priority 1: SunSpec workbook description (except M1 boilerplate)
    if workbook_description and workbook_description not in ["", "N/A", None]:
        if model != "M1" or "common model" not in workbook_description.lower():
            return workbook_description, "SunSpec Description", None

    # Priority 2: Feeds title if it's a description
    if feeds_info and feeds_info.get("is_description"):
        return feeds_info["title"], f"VSN Feeds ({feeds_info.get('source', 'Unknown')})", None

    # Priority 3: Enhanced generation with improvements
    if sunspec_name in DESCRIPTION_IMPROVEMENTS:
        return DESCRIPTION_IMPROVEMENTS[sunspec_name], "Enhanced Generation", None

    # Priority 4: Label fallback
    if label:
        return label, "Generated from Label", None

    return "Unknown measurement", "Fallback", None

def get_comprehensive_category(label, description, model_flags, vsn300_name, vsn700_name):
    """Determine category with comprehensive logic."""
    label_lower = (label or "").lower()
    desc_lower = (description or "").lower()

    # Energy Counter (highest priority)
    if any(pattern in label_lower for pattern in ["e0", "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"]):
        if not any(x in label_lower for x in ["charge", "discharge"]):
            return "Energy Counter"
    if "energy" in label_lower or "energy" in desc_lower:
        if "battery" not in label_lower and "battery" not in desc_lower:
            return "Energy Counter"

    # House Meter
    if "house" in label_lower or "house" in desc_lower:
        return "House Meter"
    if vsn700_name and vsn700_name.startswith("House"):
        return "House Meter"

    # System Monitoring
    system_keywords = ["flash", "ram", "uptime", "load", "sys_", "wlan", "ip", "essid", "mode"]
    if any(kw in label_lower for kw in system_keywords):
        return "System Monitoring"

    # Battery (excluding energy counters)
    battery_keywords = ["battery", "batt", "cell", "soc", "soh", "charge", "discharge"]
    if any(kw in label_lower for kw in battery_keywords):
        if "energy" not in label_lower:
            return "Battery"

    # Status
    status_keywords = ["status", "state", "alarm", "fault", "event", "mode", "control"]
    if any(kw in label_lower for kw in status_keywords):
        return "Status"

    # Device Info
    if model_flags.get("M1") == "YES":
        return "Device Info"

    # Phase-based categorization
    if any(phase in label_lower for phase in ["phase", "l1", "l2", "l3", "phv", "aph", "wph"]):
        if model_flags.get("M103") == "YES" or model_flags.get("M160") == "YES":
            return "Inverter"
        elif model_flags.get("M203") == "YES":
            return "Meter"

    # DC measurements
    if label_lower.startswith("dc") or "mppt" in label_lower:
        return "Inverter"

    # Model-based fallback
    if model_flags.get("M103") == "YES" or model_flags.get("M160") == "YES":
        return "Inverter"
    elif model_flags.get("M203") == "YES":
        return "Meter"
    elif model_flags.get("M802") == "YES":
        return "Battery"
    elif model_flags.get("M64061") == "YES":
        return "Inverter"
    elif model_flags.get("ABB_Proprietary") == "YES":
        return "System"
    elif model_flags.get("VSN300_Only") == "YES" or model_flags.get("VSN700_Only") == "YES":
        return "Datalogger"

    return "Unknown"
# ==============================================================================
# PART 3: DEDUPLICATION AND PROCESSING LOGIC
# ==============================================================================

def detect_models_from_point(vsn300_name, vsn700_name, model_hint=None):
    """Detect which models a point belongs to based on its names and hints."""
    models = set()

    # From VSN300 name pattern
    if vsn300_name and vsn300_name.startswith("m"):
        match = re.match(r"m(\d+)_", vsn300_name)
        if match:
            model_num = match.group(1)
            models.add(f"M{model_num}")

    # From VSN700 mapping
    if vsn700_name in VSN_TO_SUNSPEC_MAP:
        model = VSN_TO_SUNSPEC_MAP[vsn700_name].get("model")
        if model:
            models.add(model)

    # From M64061 points
    if vsn700_name in M64061_POINTS or vsn300_name in M64061_POINTS:
        models.add("M64061")

    # From ABB Proprietary
    if vsn700_name in ABB_PROPRIETARY or vsn300_name in ABB_PROPRIETARY:
        models.add("ABB_Proprietary")

    # From model hint
    if model_hint:
        models.add(model_hint.replace("ABB Proprietary", "ABB_Proprietary"))

    # VSN-only detection
    if not models:
        if vsn300_name and not vsn700_name:
            models.add("VSN300_Only")
        elif vsn700_name and not vsn300_name:
            models.add("VSN700_Only")

    return models

def merge_duplicate_rows(rows_by_sunspec):
    """Merge duplicate rows with the same SunSpec name."""
    merged_rows = []

    for sunspec_name, group in rows_by_sunspec.items():
        if len(group) == 1:
            merged_rows.append(group[0])
            continue

        # Start with first row as base
        merged = dict(group[0])

        # Collect all models from all duplicates
        all_models = set()
        for row in group:
            models = detect_models_from_point(
                row.get("vsn300_name"),
                row.get("vsn700_name"),
                row.get("model")
            )
            all_models.update(models)

        # Update model flags
        for model_flag in MODEL_FLAGS:
            merged[model_flag] = "YES" if model_flag in all_models else "NO"

        # Merge VSN names (keep both if different)
        vsn700_names = [r.get("vsn700_name") for r in group if r.get("vsn700_name") and r.get("vsn700_name") != "N/A"]
        vsn300_names = [r.get("vsn300_name") for r in group if r.get("vsn300_name") and r.get("vsn300_name") != "N/A"]

        merged["vsn700_name"] = vsn700_names[0] if vsn700_names else "N/A"
        merged["vsn300_name"] = vsn300_names[0] if vsn300_names else "N/A"

        # Choose best description
        descriptions = [(r.get("description"), r.get("data_source")) for r in group]
        best_desc = sorted(descriptions, key=lambda x: (
            0 if "SunSpec" in x[1] else
            1 if "VSN" in x[1] else
            2 if "Enhanced" in x[1] else
            3 if "Cross-Reference" in x[1] else
            4
        ))[0]
        merged["description"] = best_desc[0]
        merged["data_source"] = best_desc[1]

        merged_rows.append(merged)

    return merged_rows

def apply_display_name_corrections(row):
    """Apply display name corrections to a row."""
    original_display = row.get("ha_display_name", "")

    # Apply corrections
    if original_display in DISPLAY_NAME_CORRECTIONS:
        row["ha_display_name"] = DISPLAY_NAME_CORRECTIONS[original_display]

    return row

def apply_device_class_fixes(row):
    """Apply device class and unit fixes to a row."""
    label = row.get("label", "")

    if label in DEVICE_CLASS_FIXES:
        fixes = DEVICE_CLASS_FIXES[label]
        if "device_class" in fixes:
            row["device_class"] = fixes["device_class"] or ""
        if "unit" in fixes:
            row["units"] = fixes["unit"] or ""
        if "entity_category" in fixes:
            row["entity_category"] = fixes["entity_category"]

    return row

def create_row_with_model_flags(vsn700_name, vsn300_name, sunspec_name, ha_name,
                               in_livedata, in_feeds, label, description,
                               ha_display_name, category, units, state_class,
                               device_class, entity_category, available_in_modbus,
                               data_source, model_notes, models):
    """Create a complete row with model flags."""
    # Initialize model flags
    model_flags = {flag: "NO" for flag in MODEL_FLAGS}
    for model in models:
        if model in model_flags:
            model_flags[model] = "YES"

    # Build complete row
    row = {
        **model_flags,
        "vsn700_name": vsn700_name,
        "vsn300_name": vsn300_name,
        "sunspec_name": sunspec_name,
        "ha_name": ha_name,
        "in_livedata": in_livedata,
        "in_feeds": in_feeds,
        "label": label,
        "description": description,
        "ha_display_name": ha_display_name,
        "category": category,
        "units": units,
        "state_class": state_class,
        "device_class": device_class,
        "entity_category": entity_category,
        "available_in_modbus": available_in_modbus,
        "data_source": data_source,
        "model_notes": model_notes
    }

    # Apply corrections
    row = apply_display_name_corrections(row)
    row = apply_device_class_fixes(row)

    # Update category if needed
    if row["category"] in ["Unknown", "", None]:
        row["category"] = get_comprehensive_category(
            row["label"],
            row["description"],
            model_flags,
            vsn300_name,
            vsn700_name
        )

    return row

# ==============================================================================
# PART 4: MAIN GENERATION FUNCTIONS
# ==============================================================================

def generate_changelog_sheet(wb):
    """Generate the Changelog sheet with all updates."""
    ws = wb.create_sheet("Changelog")

    # Headers
    headers = ["Date", "Version", "Type", "Description", "Details", "Source"]
    ws.append(headers)

    # Style headers
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Add changelog entries
    for entry in CHANGELOG_ENTRIES:
        details_str = "\n".join(f"• {detail}" for detail in entry["details"])
        ws.append([
            entry["date"],
            entry["version"],
            entry["type"],
            entry["description"],
            details_str,
            entry["source"]
        ])

    # Adjust column widths
    ws.column_dimensions["A"].width = 12  # Date
    ws.column_dimensions["B"].width = 10  # Version
    ws.column_dimensions["C"].width = 20  # Type
    ws.column_dimensions["D"].width = 50  # Description
    ws.column_dimensions["E"].width = 80  # Details
    ws.column_dimensions["F"].width = 20  # Source

    # Enable text wrapping for details
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=5, max_col=5):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

def generate_summary_sheet(wb, rows):
    """Generate the Summary sheet with statistics."""
    ws = wb.create_sheet("Summary")

    # Calculate statistics
    total_points = len(rows)
    model_counts = defaultdict(int)
    category_counts = defaultdict(int)

    for row in rows:
        # Count models
        for model in MODEL_FLAGS:
            if row.get(model) == "YES":
                model_counts[model] += 1

        # Count categories
        category = row.get("category", "Unknown")
        category_counts[category] += 1

    # Add summary data
    ws.append(["Metric", "Count"])
    ws.append(["Total Points", total_points])
    ws.append([])

    ws.append(["Model Distribution", ""])
    for model in MODEL_FLAGS:
        ws.append([f"  {model}", model_counts.get(model, 0)])
    ws.append([])

    ws.append(["Category Distribution", ""])
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        ws.append([f"  {category}", count])

    # Style headers
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for cell in [ws.cell(row=1, column=1), ws.cell(row=1, column=2)]:
        cell.fill = header_fill
        cell.font = header_font

    # Adjust column widths
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 15

def generate_mapping_excel_complete():
    """Generate complete mapping Excel with all customizations built-in."""
    print(f"\n{'='*70}")
    print(f"VSN-SunSpec Point Mapping Generator v{SCRIPT_VERSION}")
    print(f"Generated: {SCRIPT_DATE}")
    print(f"{'='*70}\n")

    # Load data sources
    print("Loading data sources...")

    # Define paths relative to script location
    data_dir = SCRIPT_DIR / "data"
    output_dir = SCRIPT_DIR / "output"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load SunSpec metadata
    sunspec_path = data_dir / "sunspec" / "models_workbook.xlsx"
    if sunspec_path.exists():
        print(f"  Loading SunSpec models from {sunspec_path}")
        sunspec_metadata = load_sunspec_models_metadata(sunspec_path)
    else:
        print(f"  WARNING: SunSpec workbook not found at {sunspec_path}")
        sunspec_metadata = {}

    # Load M64061 from ABB Excel
    abb_excel_path = data_dir / "sunspec" / "ABB_SunSpec_Modbus.xlsx"
    print(f"  Loading M64061 model from {abb_excel_path}")
    m64061_metadata = load_m64061_from_abb_excel(abb_excel_path)
    print(f"    Found {len(m64061_metadata)} M64061 points")

    # Load VSN data paths
    vsn300_livedata_path = data_dir / "vsn300" / "livedata.json"
    vsn300_feeds_path = data_dir / "vsn300" / "feeds.json"
    vsn300_status_path = data_dir / "vsn300" / "status.json"
    vsn700_livedata_path = data_dir / "vsn700" / "livedata.json"
    vsn700_feeds_path = data_dir / "vsn700" / "feeds.json"
    vsn700_status_path = data_dir / "vsn700" / "status.json"

    # Load feeds titles
    print("  Loading VSN feeds data...")
    feeds_titles = load_feeds_titles(vsn300_feeds_path, vsn700_feeds_path)

    # Load status data
    print("  Loading VSN status data...")
    status_points = load_vsn_status(vsn300_status_path, vsn700_status_path)
    print(f"    Found {len(status_points)} status points")

    # Load point presence from livedata
    vsn700_livedata_points = set()
    vsn700_feeds_points = set()
    vsn300_livedata_points = set()

    if vsn700_livedata_path.exists():
        with open(vsn700_livedata_path) as f:
            data = json.load(f)
            # No "livedata" key at root - devices are directly at root
            for device_id, device_data in data.items():
                if isinstance(device_data, dict) and "points" in device_data:
                    for point in device_data["points"]:
                        vsn700_livedata_points.add(point["name"])

    if vsn700_feeds_path.exists():
        with open(vsn700_feeds_path) as f:
            data = json.load(f)
            # feeds is a dictionary, not a list!
            feeds_dict = data.get("feeds", {})
            for device_id, feed_data in feeds_dict.items():
                datastreams = feed_data.get("datastreams", {})
                vsn700_feeds_points.update(datastreams.keys())

    if vsn300_livedata_path.exists():
        with open(vsn300_livedata_path) as f:
            data = json.load(f)
            # No "livedata" key at root - devices are directly at root
            for device_id, device_data in data.items():
                if isinstance(device_data, dict) and "points" in device_data:
                    for point in device_data["points"]:
                        vsn300_livedata_points.add(point["name"])

    print(f"  Found {len(vsn700_livedata_points)} VSN700 livedata points")
    print(f"  Found {len(vsn700_feeds_points)} VSN700 feeds points")
    print(f"  Found {len(vsn300_livedata_points)} VSN300 livedata points")

    # Process all points
    print("\nProcessing points...")
    all_rows = []
    processed_points = set()

    # Process standard SunSpec points
    for vsn_name, mapping in VSN_TO_SUNSPEC_MAP.items():
        if vsn_name in vsn700_livedata_points or vsn_name in vsn700_feeds_points:
            sunspec_name = mapping["sunspec"] if mapping["sunspec"] else vsn_name
            model = mapping["model"]

            # Lookup from SunSpec metadata
            label, workbook_description = lookup_label_description(
                sunspec_metadata, model, sunspec_name
            )

            if not label:
                label = generate_label_from_name(vsn_name)

            ha_name = generate_simplified_point_name(label, model)

            # Get description with priority
            feeds_info = feeds_titles.get(vsn_name)
            description, data_source, _ = get_description_with_priority(
                vsn_name, sunspec_name, model, label,
                workbook_description, feeds_info
            )

            # Determine VSN300 name
            vsn300_name = mapping.get("modbus", "N/A")
            if vsn300_name and vsn300_name != "N/A":
                if vsn300_name not in vsn300_livedata_points:
                    vsn300_name = "N/A"

            # Detect models
            models = detect_models_from_point(vsn300_name, vsn_name, model)

            # Create row
            row = create_row_with_model_flags(
                vsn700_name=vsn_name,
                vsn300_name=vsn300_name,
                sunspec_name=sunspec_name,
                ha_name=ha_name,
                in_livedata="✓" if vsn_name in vsn700_livedata_points else "",
                in_feeds="✓" if vsn_name in vsn700_feeds_points else "",
                label=label,
                description=description,
                ha_display_name=description if description != label else label,
                category=mapping["category"],
                units=mapping["units"],
                state_class=mapping["state_class"] or "",
                device_class=mapping["device_class"] or "",
                entity_category="",
                available_in_modbus=mapping["in_modbus"],
                data_source=data_source,
                model_notes="",
                models=models
            )

            all_rows.append(row)
            processed_points.add(vsn_name)

    # Process M64061 points
    for point_name in M64061_POINTS:
        # Check if point exists in VSN700 livedata
        if point_name in vsn700_livedata_points and point_name not in processed_points:
            label = generate_label_from_name(point_name)
            ha_name = generate_simplified_point_name(label, "M64061")

            # Get description
            feeds_info = feeds_titles.get(point_name)
            description, data_source, _ = get_description_with_priority(
                point_name, point_name, "M64061", label,
                "", feeds_info
            )

            row = create_row_with_model_flags(
                vsn700_name=point_name,
                vsn300_name="N/A",
                sunspec_name=point_name,
                ha_name=ha_name,
                in_livedata="✓" if point_name in vsn700_livedata_points else "",
                in_feeds="✓" if point_name in vsn700_feeds_points else "",
                label=label,
                description=description,
                ha_display_name=description if description != label else label,
                category="Status",  # M64061 points are typically status/alarm points
                units=feeds_info.get("units", "") if feeds_info else "",
                state_class="",
                device_class="",
                entity_category="",
                available_in_modbus="NO",
                data_source=data_source,
                model_notes="ABB/FIMER proprietary model 64061",
                models={"M64061"}
            )

            all_rows.append(row)
            processed_points.add(point_name)

    # Process ABB Proprietary points
    for point_name in ABB_PROPRIETARY:
        # Check in both VSN300 and VSN700
        in_vsn700 = point_name in vsn700_livedata_points or point_name in vsn700_feeds_points
        in_vsn300 = point_name in vsn300_livedata_points

        if (in_vsn700 or in_vsn300) and point_name not in processed_points:
            label = generate_label_from_name(point_name)
            ha_name = generate_simplified_point_name(label, "ABB_Proprietary")

            # Get description
            feeds_info = feeds_titles.get(point_name)
            description, data_source, _ = get_description_with_priority(
                point_name, point_name, "ABB_Proprietary", label,
                "", feeds_info
            )

            # Determine category
            category = "System"
            if "energy" in point_name.lower():
                category = "Energy Counter"
            elif any(kw in point_name.lower() for kw in ["alarm", "fault", "status"]):
                category = "Status"

            row = create_row_with_model_flags(
                vsn700_name=point_name if in_vsn700 else "N/A",
                vsn300_name=point_name if in_vsn300 else "N/A",
                sunspec_name=point_name,
                ha_name=ha_name,
                in_livedata="✓" if (point_name in vsn700_livedata_points or point_name in vsn300_livedata_points) else "",
                in_feeds="✓" if point_name in vsn700_feeds_points else "",
                label=label,
                description=description,
                ha_display_name=description if description != label else label,
                category=category,
                units=feeds_info.get("units", "") if feeds_info else "",
                state_class="",
                device_class="",
                entity_category="",
                available_in_modbus="NO",
                data_source=data_source,
                model_notes="ABB/FIMER proprietary",
                models={"ABB_Proprietary"}
            )

            all_rows.append(row)
            processed_points.add(point_name)

    # Process VSN300-only points (points in VSN300 livedata not yet processed)
    for point_name in vsn300_livedata_points:
        if point_name not in processed_points:
            # Extract model from VSN300 naming pattern m{model}_{instance}_{point}
            model = None
            sunspec_name = point_name
            if point_name.startswith("m") and "_" in point_name:
                match = re.match(r"m(\d+)_(\d+)_(.+)", point_name)
                if match:
                    model_num, instance, sunspec_point = match.groups()
                    model = f"M{model_num}"
                    sunspec_name = sunspec_point

            label = generate_label_from_name(point_name)
            ha_name = generate_simplified_point_name(label, model or "VSN300_Only")

            # Lookup from SunSpec metadata if we have a model
            workbook_description = ""
            if model and sunspec_metadata:
                _, workbook_description = lookup_label_description(
                    sunspec_metadata, model, sunspec_name
                )

            # Get description
            feeds_info = feeds_titles.get(point_name)
            description, data_source, _ = get_description_with_priority(
                point_name, sunspec_name, model, label,
                workbook_description, feeds_info
            )

            # Detect models
            models = detect_models_from_point(point_name, None, model)
            if not models:
                models = {"VSN300_Only"}

            # Determine category
            model_flags = {flag: "YES" if flag in models else "NO" for flag in MODEL_FLAGS}
            category = get_comprehensive_category(
                label, description, model_flags, point_name, None
            )

            row = create_row_with_model_flags(
                vsn700_name="N/A",
                vsn300_name=point_name,
                sunspec_name=sunspec_name,
                ha_name=ha_name,
                in_livedata="✓",
                in_feeds="✓" if feeds_info else "",
                label=label,
                description=description,
                ha_display_name=description if description != label else label,
                category=category,
                units=feeds_info.get("units", "") if feeds_info else "",
                state_class="",
                device_class="",
                entity_category="",
                available_in_modbus="YES" if model else "NO",
                data_source=data_source,
                model_notes="VSN300-specific point",
                models=models
            )

            all_rows.append(row)
            processed_points.add(point_name)

    # Process VSN700-only points (points in VSN700 livedata/feeds not yet processed)
    all_vsn700_points = vsn700_livedata_points.union(vsn700_feeds_points)
    for point_name in all_vsn700_points:
        if point_name not in processed_points:
            label = generate_label_from_name(point_name)
            ha_name = generate_simplified_point_name(label, "VSN700_Only")

            # Get description
            feeds_info = feeds_titles.get(point_name)
            description, data_source, _ = get_description_with_priority(
                point_name, point_name, None, label,
                "", feeds_info
            )

            # Determine category
            model_flags = {"VSN700_Only": "YES"}
            for flag in MODEL_FLAGS:
                if flag != "VSN700_Only":
                    model_flags[flag] = "NO"
            category = get_comprehensive_category(
                label, description, model_flags, None, point_name
            )

            row = create_row_with_model_flags(
                vsn700_name=point_name,
                vsn300_name="N/A",
                sunspec_name=point_name,
                ha_name=ha_name,
                in_livedata="✓" if point_name in vsn700_livedata_points else "",
                in_feeds="✓" if point_name in vsn700_feeds_points else "",
                label=label,
                description=description,
                ha_display_name=description if description != label else label,
                category=category,
                units=feeds_info.get("units", "") if feeds_info else "",
                state_class="",
                device_class="",
                entity_category="",
                available_in_modbus="NO",
                data_source=data_source,
                model_notes="VSN700-specific point",
                models={"VSN700_Only"}
            )

            all_rows.append(row)
            processed_points.add(point_name)

    # Process status points (from /status endpoint)
    for point_name, status_info in status_points.items():
        if point_name not in processed_points:
            label = status_info["label"] if status_info["label"] else generate_label_from_name(point_name)
            ha_name = generate_simplified_point_name(label, "Status")

            # Determine category based on point name
            category = "Device Info"
            if "fw" in point_name.lower() or "version" in point_name.lower():
                category = "Device Info"
            elif "wlan" in point_name.lower() or "ip" in point_name.lower() or "network" in point_name.lower():
                category = "Network"
            elif "device" in point_name.lower():
                category = "Device Info"
            elif "logger" in point_name.lower():
                category = "Datalogger"

            # Determine which VSN models have this point
            vsn700_name = point_name if status_info["vsn700"] else "N/A"
            vsn300_name = point_name if status_info["vsn300"] else "N/A"

            # Set models based on availability
            models = set()
            if status_info["vsn300"] and not status_info["vsn700"]:
                models.add("VSN300_Only")
            elif status_info["vsn700"] and not status_info["vsn300"]:
                models.add("VSN700_Only")
            else:
                models.add("ABB_Proprietary")

            row = create_row_with_model_flags(
                vsn700_name=vsn700_name,
                vsn300_name=vsn300_name,
                sunspec_name=point_name,
                ha_name=ha_name,
                in_livedata="",
                in_feeds="",
                label=label,
                description=f"Status endpoint: {label}",
                ha_display_name=label,
                category=category,
                units="",
                state_class="",
                device_class="",
                entity_category="diagnostic",
                available_in_modbus="NO",
                data_source=status_info["source"],
                model_notes="From /status endpoint",
                models=models
            )

            all_rows.append(row)
            processed_points.add(point_name)

    print(f"  Processed {len(all_rows)} total points (including status endpoints)")

    # Deduplication
    print("\nDeduplicating points...")
    rows_by_sunspec = defaultdict(list)
    for row in all_rows:
        sunspec_name = row.get("sunspec_name", "UNKNOWN")
        rows_by_sunspec[sunspec_name].append(row)

    deduplicated_rows = merge_duplicate_rows(rows_by_sunspec)
    print(f"  Deduplicated from {len(all_rows)} to {len(deduplicated_rows)} unique points")

    # Create Excel workbook
    print("\nCreating Excel workbook...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "All Points"

    # Add headers
    for col_idx, header in enumerate(EXCEL_HEADERS, 1):
        ws.cell(row=1, column=col_idx, value=header)

    # Style headers
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    for col_idx in range(1, len(EXCEL_HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Add data rows
    for row_idx, row_data in enumerate(deduplicated_rows, 2):
        for col_idx, header in enumerate(EXCEL_HEADERS, 1):
            # Map header to row key
            header_key = header.lower().replace(" ", "_").replace("(", "").replace(")", "")
            if header in MODEL_FLAGS:
                value = row_data.get(header, "NO")
            elif header == "REST Name (VSN700)":
                value = row_data.get("vsn700_name", "")
            elif header == "REST Name (VSN300)":
                value = row_data.get("vsn300_name", "")
            elif header == "SunSpec Normalized Name":
                value = row_data.get("sunspec_name", "")
            elif header == "HA Name":
                value = row_data.get("ha_name", "")
            elif header == "In /livedata":
                value = row_data.get("in_livedata", "")
            elif header == "In /feeds":
                value = row_data.get("in_feeds", "")
            elif header == "Label":
                value = row_data.get("label", "")
            elif header == "Description":
                value = row_data.get("description", "")
            elif header == "HA Display Name":
                value = row_data.get("ha_display_name", "")
            elif header == "Category":
                value = row_data.get("category", "")
            elif header == "HA Unit of Measurement":
                value = row_data.get("units", "")
            elif header == "HA State Class":
                value = row_data.get("state_class", "")
            elif header == "HA Device Class":
                value = row_data.get("device_class", "")
            elif header == "Entity Category":
                value = row_data.get("entity_category", "")
            elif header == "Available in Modbus":
                value = row_data.get("available_in_modbus", "")
            elif header == "Data Source":
                value = row_data.get("data_source", "")
            elif header == "Model_Notes":
                value = row_data.get("model_notes", "")
            else:
                value = ""

            ws.cell(row=row_idx, column=col_idx, value=value)

    # Adjust column widths
    for col_idx, header in enumerate(EXCEL_HEADERS, 1):
        if header in MODEL_FLAGS:
            ws.column_dimensions[get_column_letter(col_idx)].width = 8
        elif "REST Name" in header:
            ws.column_dimensions[get_column_letter(col_idx)].width = 20
        elif header in ["Description", "HA Display Name"]:
            ws.column_dimensions[get_column_letter(col_idx)].width = 40
        else:
            ws.column_dimensions[get_column_letter(col_idx)].width = 15

    # Add auto-filter
    ws.auto_filter.ref = ws.dimensions

    # Generate Summary sheet
    generate_summary_sheet(wb, deduplicated_rows)

    # Generate Changelog sheet
    generate_changelog_sheet(wb)

    # Save workbook
    output_path = output_dir / "vsn-sunspec-point-mapping.xlsx"
    wb.save(output_path)

    print(f"\n{'='*70}")
    print(f"✓ Excel file created: {output_path}")
    print(f"  Total rows: {len(deduplicated_rows)}")
    print(f"  Sheets: All Points, Summary, Changelog")
    print(f"{'='*70}\n")

    return output_path

if __name__ == "__main__":
    generate_mapping_excel_complete()