#!/usr/bin/env python3
"""Analyze which VSN700 points get abb_ prefix."""

# Complete VSN700 point list from livedata sample
all_vsn700_points = {
    'AlarmState', 'BattExtCtrlEna', 'BattExtCtrlState', 'BattNum', 'BatteryMode',
    'Chc', 'ClockState', 'CommissioningFreeze', 'CountryStd', 'CycleNum',
    'DC1State', 'DC2State', 'DI0_mode', 'DI1_mode', 'DI_status',
    'DetectedBatteryNumber', 'Dhc', 'DynamicFeedInCtrl',
    'E0_1Y', 'E0_30D', 'E0_7D', 'E0_runtime',
    'E15_30D', 'E15_7D', 'E15_runtime',
    'E1_30D', 'E1_7D', 'E1_runtime',
    'E2_30D', 'E2_7D', 'E2_runtime',
    'E3_30D', 'E3_7D', 'E3_runtime',
    'E4_30D', 'E4_7D', 'E4_runtime',
    'E5_30D', 'E5_7D', 'E5_runtime',
    'E6_30D', 'E6_7D', 'E6_runtime',
    'E7_30D', 'E7_7D', 'E7_runtime',
    'E8_30D', 'E8_7D', 'E8_runtime',
    'EBackup', 'ECharge', 'ECharge_30D', 'ECharge_7D', 'ECharge_runtime',
    'ECt', 'EDischarge', 'EDischarge_30D', 'EDischarge_7D', 'EDischarge_runtime', 'EDt',
    'EGridExport', 'EGridImport',
    'ETotCharge_30D', 'ETotCharge_7D', 'ETotCharge_runtime',
    'ETotDischarge_30D', 'ETotDischarge_7D', 'ETotDischarge_runtime',
    'ETotal', 'ETotalAbsorbed', 'ETotalApparent',
    'Ein', 'Ein1', 'Ein2', 'Ein_30D', 'Ein_7D', 'Ein_runtime',
    'EnergyPolicy', 'FRT_state', 'Fan1rpm', 'Fan2rpm', 'Fcc', 'Fgrid', 'GlobState',
    'HouseIgrid_L1', 'HouseIgrid_L2', 'HouseIgrid_L3',
    'HousePInverter', 'HousePgrid_L1', 'HousePgrid_L2', 'HousePgrid_L3', 'HousePgrid_Tot',
    'Iba', 'Igrid', 'Iin1', 'Iin2', 'IleakDC', 'IleakInv', 'InputMode', 'InvState',
    'MeterFgrid',
    'MeterIgrid_L1', 'MeterIgrid_L2', 'MeterIgrid_L3',
    'MeterPgrid_L1', 'MeterPgrid_L2', 'MeterPgrid_L3', 'MeterPgrid_Tot',
    'MeterQgrid_L1', 'MeterQgrid_L2', 'MeterQgrid_L3', 'MeterQgrid_Tot',
    'MeterVgrid_L1', 'MeterVgrid_L2', 'MeterVgrid_L3',
    'NumOfMPPT', 'PACDeratingFlags', 'PCh', 'PDh',
    'PacStandAlone', 'PacTogrid', 'Pba', 'PbaT', 'Pgrid', 'Pin', 'Pin1', 'Pin2', 'Ppeak',
    'QACDeratingFlags', 'Qgrid', 'Riso',
    'SACDeratingFlags', 'ShU', 'Soc', 'Soh', 'SplitPhase', 'SysTime',
    'TSoc', 'Tba', 'TcMax', 'TcMin', 'Temp1', 'TempBst', 'TempInv',
    'VBulk', 'VBulkMid', 'Vba', 'VcMax', 'VcMin', 'Vgnd', 'Vgrid', 'VgridL1_N', 'VgridL2_N',
    'Vin1', 'Vin2', 'WRtg', 'WarningFlags', 'cosPhi',
    'gridExtCtrlEna', 'gridExtCtrlState', 'm126Mod_Ena', 'm132Mod_Ena'
}

# Points mapped to STANDARD SunSpec models (available in BOTH Modbus + REST)
mapped_to_standard_sunspec = {
    # M101/103 - Inverter
    'Pgrid', 'Igrid', 'Vgrid', 'Fgrid', 'cosPhi', 'Qgrid', 'Pin', 'ETotal', 'Ein',
    'TempInv', 'Temp1', 'WRtg',

    # M160 - MPPT
    'Iin1', 'Vin1', 'Pin1', 'Iin2', 'Vin2', 'Pin2',

    # M124 - Storage Controls
    'TSoc', 'PbaT',

    # M802 - Battery Base Model
    'Soc', 'Soh', 'Vba', 'Iba', 'Pba', 'Tba', 'CycleNum',
    'VcMax', 'VcMin', 'TcMax', 'TcMin', 'PCh', 'PDh', 'Fcc',

    # M101/102 - Split Phase Inverter
    'VgridL1_N', 'VgridL2_N', 'SplitPhase',

    # M203 - Three-Phase Meter
    'MeterPgrid_Tot', 'MeterPgrid_L1', 'MeterPgrid_L2', 'MeterPgrid_L3',
    'MeterVgrid_L1', 'MeterVgrid_L2', 'MeterVgrid_L3',
    'MeterIgrid_L1', 'MeterIgrid_L2', 'MeterIgrid_L3',
    'MeterQgrid_Tot', 'MeterQgrid_L1', 'MeterQgrid_L2', 'MeterQgrid_L3',
    'MeterFgrid',
    'EGridImport', 'EGridExport',
}

# Points that get abb_ prefix (ABB proprietary, not in ANY standard SunSpec model)
abb_prefix_points = all_vsn700_points - mapped_to_standard_sunspec

print('=== POINTS THAT WILL GET abb_ PREFIX ===')
print(f'Total: {len(abb_prefix_points)} points\n')

# Categorize for clarity
def categorize_point(p):
    if 'runtime' in p or '_7D' in p or '_30D' in p or '_1Y' in p:
        return 'Periodic Energy Counters'
    elif p.startswith('E') and len(p) < 20:
        return 'Energy Totals (ABB specific)'
    elif p.startswith('House'):
        return 'House Consumption Metering'
    elif p in ['VBulk', 'VBulkMid', 'Vgnd', 'Riso', 'IleakInv', 'IleakDC']:
        return 'Bulk Voltages & Isolation'
    elif 'State' in p or p in ['GlobState', 'AlarmState', 'InvState', 'DC1State', 'DC2State', 'CountryStd']:
        return 'State & Status'
    elif p in ['PacTogrid', 'PacStandAlone', 'EBackup']:
        return 'Hybrid Inverter Features'
    elif p in ['BattNum', 'DetectedBatteryNumber', 'BatteryMode', 'BattExtCtrlEna', 'BattExtCtrlState', 'Chc', 'Dhc', 'ShU', 'EnergyPolicy']:
        return 'Battery Extensions'
    elif 'Ctrl' in p or 'mode' in p or 'Ena' in p or 'Flags' in p or 'Mod' in p:
        return 'Control Flags & Modes'
    elif p in ['SysTime', 'NumOfMPPT', 'InputMode', 'Fan1rpm', 'Fan2rpm', 'TempBst', 'Ppeak', 'WarningFlags', 'FRT_state', 'ClockState', 'CommissioningFreeze', 'DI_status']:
        return 'System Info'
    else:
        return 'Other'

categories = {}
for p in abb_prefix_points:
    cat = categorize_point(p)
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(p)

for category in sorted(categories.keys()):
    points = categories[category]
    print(f'{category} ({len(points)} points):')
    for p in sorted(points):
        print(f'  {p:30s} → abb_{p}')
    print()
