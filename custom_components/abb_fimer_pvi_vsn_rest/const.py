"""Constants for ABB FIMER PVI VSN REST integration."""

DOMAIN = "abb_fimer_pvi_vsn_rest"
VERSION = "1.0.0-beta.22"

# Configuration
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_VSN_MODEL = "vsn_model"  # Cached detection result

DEFAULT_USERNAME = "guest"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 600

# VSN Models
VSN_MODEL_300 = "vsn300"
VSN_MODEL_700 = "vsn700"

# REST API Endpoints
ENDPOINT_STATUS = "/v1/status"
ENDPOINT_LIVEDATA = "/v1/livedata"
ENDPOINT_FEEDS = "/v1/feeds"

# Aurora protocol epoch offset (Jan 1, 2000 00:00:00 UTC)
# The Aurora protocol uses a custom epoch instead of Unix epoch (Jan 1, 1970)
# Reference: https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library/blob/master/include/utils.h#L8
# Protocol documentation: https://mischianti.org/wp-content/uploads/2022/01/AuroraCommunicationProtocol_4_2.pdf
AURORA_EPOCH_OFFSET = 946684800

# Aurora Protocol State Mappings
# Reference: https://github.com/xreef/ABB_Aurora_Solar_Inverter_Library/blob/master/include/statesNaming.h
# Protocol documentation: https://mischianti.org/wp-content/uploads/2022/01/AuroraCommunicationProtocol_4_2.pdf
# These mappings translate integer state codes to human-readable descriptions

# Global operational states (42 states: 0-38, 98-101)
GLOBAL_STATE_MAP = {
    0: "Sending Parameters",
    1: "Wait Sun / Grid",
    2: "Checking Grid",
    3: "Measuring Riso",
    4: "DcDc Start",
    5: "Inverter Start",
    6: "Run",
    7: "Recovery",
    8: "Pausev",
    9: "Ground Fault",
    10: "OTH Fault",
    11: "Address Setting",
    12: "Self Test",
    13: "Self Test Fail",
    14: "Sensor Test + Meas.Riso",
    15: "Leak Fault",
    16: "Waiting for manual reset",
    17: "Internal Error E026",
    18: "Internal Error E027",
    19: "Internal Error E028",
    20: "Internal Error E029",
    21: "Internal Error E030",
    22: "Sending Wind Table",
    23: "Failed Sending table",
    24: "UTH Fault",
    25: "Remote OFF",
    26: "Interlock Fail",
    27: "Executing Autotest",
    30: "Waiting Sun",
    31: "Temperature Fault",
    32: "Fan Staucked",
    33: "Int.Com.Fault",
    34: "Slave Insertion",
    35: "DC Switch Open",
    36: "TRAS Switch Open",
    37: "MASTER Exclusion",
    38: "Auto Exclusion",
    98: "Erasing Internal EEprom",
    99: "Erasing External EEprom",
    100: "Counting EEprom",
    101: "Freeze",
}

# DC-DC converter states (20 states: 0-19)
DCDC_STATE_MAP = {
    0: "DcDc OFF",
    1: "Ramp Start",
    2: "MPPT",
    3: "Not Used",
    4: "Input OC",
    5: "Input UV",
    6: "Input OV",
    7: "Input Low",
    8: "No Parameters",
    9: "Bulk OV",
    10: "Communication Error",
    11: "Ramp Fail",
    12: "Internal Error",
    13: "Input mode Error",
    14: "Ground Fault",
    15: "Inverter Fail",
    16: "DcDc IGBT Sat",
    17: "DcDc ILEAK Fail",
    18: "DcDc Grid Fail",
    19: "DcDc Comm. Error",
}

# Inverter operational states (38 states: 0-31, 40-47)
INVERTER_STATE_MAP = {
    0: "Stand By",
    1: "Checking Grid",
    2: "Run",
    3: "Bulk OV",
    4: "Out OC",
    5: "IGBT Sat",
    6: "Bulk UV",
    7: "Degauss Error",
    8: "No Parameters",
    9: "Bulk Low",
    10: "Grid OV",
    11: "Communication Error",
    12: "Degaussing",
    13: "Starting",
    14: "Bulk Cap Fail",
    15: "Leak Fail",
    16: "DcDc Fail",
    17: "Ileak Sensor Fail",
    18: "SelfTest: relay inverter",
    19: "SelfTest: wait for sensor test",
    20: "SelfTest: test relay DcDc + sensor",
    21: "SelfTest: relay inverter fail",
    22: "SelfTest: timeout fail",
    23: "SelfTest: relay DcDc fail",
    24: "Self Test 1",
    25: "Waiting self test start",
    26: "Dc Injection",
    27: "Self Test 2",
    28: "Self Test 3",
    29: "Self Test 4",
    30: "Internal Error",
    31: "Internal Error",
    40: "Forbidden State",
    41: "Input UC",
    42: "Zero Power",
    43: "Grid Not Present",
    44: "Waiting Start",
    45: "MPPT",
    46: "Grid Fail",
    47: "Input OC",
}

# Alarm states (65 states: 0-64)
ALARM_STATE_MAP = {
    0: "No Alarm",
    1: "Sun Low",
    2: "Input OC",
    3: "Input UV",
    4: "Input OV",
    5: "Sun Low",
    6: "No Parameters",
    7: "Bulk OV",
    8: "Comm.Error",
    9: "Output OC",
    10: "IGBT Sat",
    11: "Bulk UV",
    12: "Internal error",
    13: "Grid Fail",
    14: "Bulk Low",
    15: "Ramp Fail",
    16: "Dc/Dc Fail",
    17: "Wrong Mode",
    18: "Ground Fault",
    19: "Over Temp.",
    20: "Bulk Cap Fail",
    21: "Inverter Fail",
    22: "Start Timeout",
    23: "Ground Fault",
    24: "Degauss error",
    25: "Ileak sens.fail",
    26: "DcDc Fail",
    27: "Self Test Error 1",
    28: "Self Test Error 2",
    29: "Self Test Error 3",
    30: "Self Test Error 4",
    31: "DC inj error",
    32: "Grid OV",
    33: "Grid UV",
    34: "Grid OF",
    35: "Grid UF",
    36: "Z grid Hi",
    37: "Internal error",
    38: "Riso Low",
    39: "Vref Error",
    40: "Error Meas V",
    41: "Error Meas F",
    42: "Error Meas Z",
    43: "Error Meas Ileak",
    44: "Error Read V",
    45: "Error Read I",
    46: "Table fail",
    47: "Fan Fail",
    48: "UTH",
    49: "Interlock fail",
    50: "Remote Off",
    51: "Vout Avg errror",
    52: "Battery low",
    53: "Clk fail",
    54: "Input UC",
    55: "Zero Power",
    56: "Fan Stucked",
    57: "DC Switch Open",
    58: "Tras Switch Open",
    59: "AC Switch Open",
    60: "Bulk UV",
    61: "Autoexclusion",
    62: "Grid df / dt",
    63: "Den switch Open",
    64: "Jbox fail",
}

# Map SunSpec entity names to their corresponding state mapping dictionary
# Keys must match the SunSpec normalized names from vsn-sunspec-point-mapping.json
STATE_ENTITY_MAPPINGS = {
    "GlobalSt": GLOBAL_STATE_MAP,      # VSN300: m64061_1_GlobalSt
    "DcSt1": DCDC_STATE_MAP,           # VSN300: m64061_1_DcSt1
    "DcSt2": DCDC_STATE_MAP,           # VSN300: m64061_1_DcSt2
    "InverterSt": INVERTER_STATE_MAP,  # VSN300: m64061_1_InverterSt
    "AlarmState": ALARM_STATE_MAP,
    "AlarmSt": ALARM_STATE_MAP,        # VSN300: m64061_1_AlarmSt
}

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
ABB/FIMER PVI VSN REST
Version: {VERSION}
This is a custom integration for Home Assistant
If you have any issues, please report them at:
https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/issues
-------------------------------------------------------------------
"""
