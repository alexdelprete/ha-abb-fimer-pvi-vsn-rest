#!/usr/bin/env python3
"""Generate comprehensive VSN-SunSpec point mapping Excel file."""

import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Complete mapping: VSN700 → SunSpec
VSN_TO_SUNSPEC_MAP = {
    # ===== Standard SunSpec Models (Available in BOTH Modbus + REST) =====
    # M103 - Inverter
    'Pgrid': {'sunspec': 'W', 'modbus': 'm103_1_W', 'model': 'M103', 'category': 'Inverter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'Igrid': {'sunspec': 'A', 'modbus': 'm103_1_A', 'model': 'M103', 'category': 'Inverter', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'Vgrid': {'sunspec': 'PhVphA', 'modbus': 'm103_1_PhVphA', 'model': 'M103', 'category': 'Inverter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'Fgrid': {'sunspec': 'Hz', 'modbus': 'm103_1_Hz', 'model': 'M103', 'category': 'Inverter', 'units': 'Hz', 'state_class': 'measurement', 'device_class': 'frequency', 'in_modbus': 'YES'},
    'cosPhi': {'sunspec': 'PF', 'modbus': 'm103_1_PF', 'model': 'M103', 'category': 'Inverter', 'units': '%', 'state_class': 'measurement', 'device_class': 'power_factor', 'in_modbus': 'YES'},
    'Qgrid': {'sunspec': 'VAR', 'modbus': 'm103_1_VAR', 'model': 'M103', 'category': 'Inverter', 'units': 'var', 'state_class': 'measurement', 'device_class': 'reactive_power', 'in_modbus': 'YES'},
    'Pin': {'sunspec': 'DCW', 'modbus': 'm103_1_DCW', 'model': 'M103', 'category': 'Inverter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'ETotal': {'sunspec': 'WH', 'modbus': 'm103_1_WH', 'model': 'M103', 'category': 'Inverter', 'units': 'Wh', 'state_class': 'total_increasing', 'device_class': 'energy', 'in_modbus': 'YES'},
    'Ein': {'sunspec': 'WH', 'modbus': 'm103_1_WH', 'model': 'M103', 'category': 'Inverter', 'units': 'Wh', 'state_class': 'total_increasing', 'device_class': 'energy', 'in_modbus': 'YES'},
    'TempInv': {'sunspec': 'TmpOt', 'modbus': 'm103_1_TmpOt', 'model': 'M103', 'category': 'Inverter', 'units': '°C', 'state_class': 'measurement', 'device_class': 'temperature', 'in_modbus': 'YES'},
    'Temp1': {'sunspec': 'TmpCab', 'modbus': 'm103_1_TmpCab', 'model': 'M103', 'category': 'Inverter', 'units': '°C', 'state_class': 'measurement', 'device_class': 'temperature', 'in_modbus': 'YES'},

    # M120 - Nameplate
    'WRtg': {'sunspec': 'WRtg', 'modbus': 'm120_1_WRtg', 'model': 'M120', 'category': 'Inverter', 'units': 'W', 'state_class': None, 'device_class': 'power', 'in_modbus': 'YES'},

    # M160 - MPPT
    'Iin1': {'sunspec': 'DCA_1', 'modbus': 'm160_1_DCA_1', 'model': 'M160', 'category': 'MPPT', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'Vin1': {'sunspec': 'DCV_1', 'modbus': 'm160_1_DCV_1', 'model': 'M160', 'category': 'MPPT', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'Pin1': {'sunspec': 'DCW_1', 'modbus': 'm160_1_DCW_1', 'model': 'M160', 'category': 'MPPT', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'Iin2': {'sunspec': 'DCA_2', 'modbus': 'm160_1_DCA_2', 'model': 'M160', 'category': 'MPPT', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'Vin2': {'sunspec': 'DCV_2', 'modbus': 'm160_1_DCV_2', 'model': 'M160', 'category': 'MPPT', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'Pin2': {'sunspec': 'DCW_2', 'modbus': 'm160_1_DCW_2', 'model': 'M160', 'category': 'MPPT', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},

    # M124 - Storage
    'TSoc': {'sunspec': 'ChaState', 'modbus': 'm124_1_ChaState', 'model': 'M124', 'category': 'Battery', 'units': '%', 'state_class': 'measurement', 'device_class': 'battery', 'in_modbus': 'YES'},
    'PbaT': {'sunspec': 'InWRte', 'modbus': 'm124_1_InWRte', 'model': 'M124', 'category': 'Battery', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},

    # M802 - Battery
    'Soc': {'sunspec': 'SoC', 'modbus': 'm802_1_SoC', 'model': 'M802', 'category': 'Battery', 'units': '%', 'state_class': 'measurement', 'device_class': 'battery', 'in_modbus': 'YES'},
    'Soh': {'sunspec': 'SoH', 'modbus': 'm802_1_SoH', 'model': 'M802', 'category': 'Battery', 'units': '%', 'state_class': 'measurement', 'device_class': None, 'in_modbus': 'YES'},
    'Vba': {'sunspec': 'V', 'modbus': 'm802_1_V', 'model': 'M802', 'category': 'Battery', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'Iba': {'sunspec': 'A', 'modbus': 'm802_1_A', 'model': 'M802', 'category': 'Battery', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'Pba': {'sunspec': 'W', 'modbus': 'm802_1_W', 'model': 'M802', 'category': 'Battery', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'Tba': {'sunspec': 'Tmp', 'modbus': 'm802_1_Tmp', 'model': 'M802', 'category': 'Battery', 'units': '°C', 'state_class': 'measurement', 'device_class': 'temperature', 'in_modbus': 'YES'},
    'CycleNum': {'sunspec': 'NCyc', 'modbus': 'm802_1_NCyc', 'model': 'M802', 'category': 'Battery', 'units': '', 'state_class': 'total', 'device_class': None, 'in_modbus': 'YES'},
    'VcMax': {'sunspec': 'CellVMax', 'modbus': 'm802_1_CellVMax', 'model': 'M802', 'category': 'Battery', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'VcMin': {'sunspec': 'CellVMin', 'modbus': 'm802_1_CellVMin', 'model': 'M802', 'category': 'Battery', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'TcMax': {'sunspec': 'CellTmpMax', 'modbus': 'm802_1_CellTmpMax', 'model': 'M802', 'category': 'Battery', 'units': '°C', 'state_class': 'measurement', 'device_class': 'temperature', 'in_modbus': 'YES'},
    'TcMin': {'sunspec': 'CellTmpMin', 'modbus': 'm802_1_CellTmpMin', 'model': 'M802', 'category': 'Battery', 'units': '°C', 'state_class': 'measurement', 'device_class': 'temperature', 'in_modbus': 'YES'},
    'PCh': {'sunspec': 'AChaMax', 'modbus': 'm802_1_AChaMax', 'model': 'M802', 'category': 'Battery', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'PDh': {'sunspec': 'ADisChaMax', 'modbus': 'm802_1_ADisChaMax', 'model': 'M802', 'category': 'Battery', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'Fcc': {'sunspec': 'AHRtg', 'modbus': 'm802_1_AHRtg', 'model': 'M802', 'category': 'Battery', 'units': 'Ah', 'state_class': None, 'device_class': None, 'in_modbus': 'YES'},

    # M101/102 - Split Phase
    'VgridL1_N': {'sunspec': 'PhVphA', 'modbus': 'm101_1_PhVphA', 'model': 'M101', 'category': 'Inverter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'VgridL2_N': {'sunspec': 'PhVphB', 'modbus': 'm101_1_PhVphB', 'model': 'M101', 'category': 'Inverter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'SplitPhase': {'sunspec': None, 'modbus': None, 'model': 'M101', 'category': 'Inverter', 'units': '', 'state_class': None, 'device_class': None, 'in_modbus': 'YES'},

    # M203 - Meter
    'MeterPgrid_Tot': {'sunspec': 'W', 'modbus': 'm203_1_W', 'model': 'M203', 'category': 'Meter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'MeterPgrid_L1': {'sunspec': 'WphA', 'modbus': 'm203_1_WphA', 'model': 'M203', 'category': 'Meter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'MeterPgrid_L2': {'sunspec': 'WphB', 'modbus': 'm203_1_WphB', 'model': 'M203', 'category': 'Meter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'MeterPgrid_L3': {'sunspec': 'WphC', 'modbus': 'm203_1_WphC', 'model': 'M203', 'category': 'Meter', 'units': 'W', 'state_class': 'measurement', 'device_class': 'power', 'in_modbus': 'YES'},
    'MeterVgrid_L1': {'sunspec': 'PhVphA', 'modbus': 'm203_1_PhVphA', 'model': 'M203', 'category': 'Meter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'MeterVgrid_L2': {'sunspec': 'PhVphB', 'modbus': 'm203_1_PhVphB', 'model': 'M203', 'category': 'Meter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'MeterVgrid_L3': {'sunspec': 'PhVphC', 'modbus': 'm203_1_PhVphC', 'model': 'M203', 'category': 'Meter', 'units': 'V', 'state_class': 'measurement', 'device_class': 'voltage', 'in_modbus': 'YES'},
    'MeterIgrid_L1': {'sunspec': 'AphA', 'modbus': 'm203_1_AphA', 'model': 'M203', 'category': 'Meter', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'MeterIgrid_L2': {'sunspec': 'AphB', 'modbus': 'm203_1_AphB', 'model': 'M203', 'category': 'Meter', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'MeterIgrid_L3': {'sunspec': 'AphC', 'modbus': 'm203_1_AphC', 'model': 'M203', 'category': 'Meter', 'units': 'A', 'state_class': 'measurement', 'device_class': 'current', 'in_modbus': 'YES'},
    'MeterQgrid_Tot': {'sunspec': 'VAR', 'modbus': 'm203_1_VAR', 'model': 'M203', 'category': 'Meter', 'units': 'var', 'state_class': 'measurement', 'device_class': 'reactive_power', 'in_modbus': 'YES'},
    'MeterQgrid_L1': {'sunspec': 'VARphA', 'modbus': 'm203_1_VARphA', 'model': 'M203', 'category': 'Meter', 'units': 'var', 'state_class': 'measurement', 'device_class': 'reactive_power', 'in_modbus': 'YES'},
    'MeterQgrid_L2': {'sunspec': 'VARphB', 'modbus': 'm203_1_VARphB', 'model': 'M203', 'category': 'Meter', 'units': 'var', 'state_class': 'measurement', 'device_class': 'reactive_power', 'in_modbus': 'YES'},
    'MeterQgrid_L3': {'sunspec': 'VARphC', 'modbus': 'm203_1_VARphC', 'model': 'M203', 'category': 'Meter', 'units': 'var', 'state_class': 'measurement', 'device_class': 'reactive_power', 'in_modbus': 'YES'},
    'MeterFgrid': {'sunspec': 'Hz', 'modbus': 'm203_1_Hz', 'model': 'M203', 'category': 'Meter', 'units': 'Hz', 'state_class': 'measurement', 'device_class': 'frequency', 'in_modbus': 'YES'},
    'EGridImport': {'sunspec': 'TotWhImp', 'modbus': 'm203_1_TotWhImp', 'model': 'M203', 'category': 'Meter', 'units': 'Wh', 'state_class': 'total_increasing', 'device_class': 'energy', 'in_modbus': 'YES'},
    'EGridExport': {'sunspec': 'TotWhExp', 'modbus': 'm203_1_TotWhExp', 'model': 'M203', 'category': 'Meter', 'units': 'Wh', 'state_class': 'total_increasing', 'device_class': 'energy', 'in_modbus': 'YES'},
}

# M64061 points - will be added with abb_ prefix
M64061_POINTS = {
    'AlarmState', 'DC1State', 'DC2State', 'GlobState', 'InvState',
    'IleakInv', 'IleakDC', 'Riso',
    'VBulk', 'VBulkMid', 'Vgnd',
    'TempBst', 'SysTime', 'Ppeak', 'CountryStd',
}

# ABB Proprietary (non-M64061)
ABB_PROPRIETARY = {
    'BattExtCtrlEna', 'BattExtCtrlState', 'BattNum', 'BatteryMode',
    'Chc', 'ClockState', 'CommissioningFreeze',
    'DI0_mode', 'DI1_mode', 'DI_status',
    'DetectedBatteryNumber', 'Dhc', 'DynamicFeedInCtrl',
    'EBackup', 'ECharge', 'ECt', 'EDischarge', 'EDt',
    'ETotalAbsorbed', 'ETotalApparent', 'Ein1', 'Ein2',
    'EnergyPolicy', 'FRT_state', 'Fan1rpm', 'Fan2rpm',
    'HouseIgrid_L1', 'HouseIgrid_L2', 'HouseIgrid_L3',
    'HousePInverter', 'HousePgrid_L1', 'HousePgrid_L2', 'HousePgrid_L3', 'HousePgrid_Tot',
    'InputMode', 'NumOfMPPT',
    'PACDeratingFlags', 'PacStandAlone', 'PacTogrid',
    'QACDeratingFlags', 'SACDeratingFlags',
    'ShU', 'WarningFlags',
    'gridExtCtrlEna', 'gridExtCtrlState',
    'm126Mod_Ena', 'm132Mod_Ena',
}

print('Loading VSN700 data...')

# Load VSN700 data
with open('vsnx00-monitor/data-samples/vsn700-json-data/livedata.json') as f:
    livedata = json.load(f)

with open('vsnx00-monitor/data-samples/vsn700-json-data/feeds.json') as f:
    feeds_data = json.load(f)

# Extract point presence
livedata_points = set()
for device_id, device_data in livedata.items():
    if 'points' in device_data:
        for point in device_data['points']:
            livedata_points.add(point['name'])

feeds_points = set()
for feed_key, feed_data in feeds_data['feeds'].items():
    if 'datastreams' in feed_data:
        for point_name in feed_data['datastreams'].keys():
            feeds_points.add(point_name)

print(f'Found {len(livedata_points)} points in /livedata')
print(f'Found {len(feeds_points)} points in /feeds')

# Get periodic energy counters
periodic_suffixes = ['_runtime', '_7D', '_30D', '_1Y']
periodic_points = {p for p in livedata_points if any(suffix in p for suffix in periodic_suffixes)}

print(f'Found {len(periodic_points)} periodic energy counters')

# Create workbook
print('Creating Excel workbook...')
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'All Points'

# Define headers
headers = [
    'REST Name (VSN700)',
    'REST Name (VSN300)',
    'SunSpec Normalized Name',
    'HA Entity Name',
    'In /livedata',
    'In /feeds',
    'SunSpec Model',
    'Category',
    'Units',
    'State Class',
    'Device Class',
    'Available in Modbus'
]

# Write headers with formatting
header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
header_font = Font(bold=True, color='FFFFFF')
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

for col_num, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_num)
    cell.value = header
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = thin_border

# Prepare all data rows
rows = []

# Standard SunSpec points
for vsn_name, mapping in VSN_TO_SUNSPEC_MAP.items():
    if vsn_name in livedata_points or vsn_name in feeds_points:
        sunspec_name = mapping['sunspec'] if mapping['sunspec'] else vsn_name
        ha_name = sunspec_name if sunspec_name else vsn_name
        rows.append([
            vsn_name,
            mapping['modbus'] if mapping['modbus'] else 'N/A',
            sunspec_name if sunspec_name else 'N/A',
            ha_name,
            '✓' if vsn_name in livedata_points else '',
            '✓' if vsn_name in feeds_points else '',
            mapping['model'],
            mapping['category'],
            mapping['units'],
            mapping['state_class'] if mapping['state_class'] else '',
            mapping['device_class'] if mapping['device_class'] else '',
            mapping['in_modbus']
        ])

# M64061 periodic energy counters
for p in sorted(periodic_points):
    if p.startswith('E'):
        rows.append([
            p,
            f'm64061_1_{p}' if '_runtime' not in p else 'N/A',
            f'abb_{p}',
            f'abb_{p}',
            '✓' if p in livedata_points else '',
            '✓' if p in feeds_points else '',
            'M64061',
            'Energy Counter',
            'Wh',
            'total',
            'energy',
            'MAYBE'
        ])

# M64061 non-periodic
for p in sorted(M64061_POINTS):
    if p in livedata_points or p in feeds_points:
        category = 'Diagnostic'
        if 'State' in p:
            category = 'Status'
        elif 'leak' in p or p in ['Riso', 'VBulk', 'VBulkMid', 'Vgnd']:
            category = 'Isolation'

        rows.append([
            p,
            f'm64061_1_{p}',
            f'abb_{p}',
            f'abb_{p}',
            '✓' if p in livedata_points else '',
            '✓' if p in feeds_points else '',
            'M64061',
            category,
            'V' if 'V' in p else ('A' if 'leak' in p else ''),
            'measurement',
            'voltage' if 'V' in p else '',
            'MAYBE'
        ])

# ABB Proprietary
for p in sorted(ABB_PROPRIETARY):
    if p in livedata_points or p in feeds_points:
        category = 'Other'
        if p.startswith('House'):
            category = 'House Meter'
        elif p.startswith('Batt') or p in ['Chc', 'Dhc', 'ShU', 'EnergyPolicy']:
            category = 'Battery Ext'
        elif p.startswith('E'):
            category = 'Energy Counter'
        elif 'Ctrl' in p or 'mode' in p or 'Flags' in p or 'Mod' in p:
            category = 'Control'
        elif p in ['Fan1rpm', 'Fan2rpm', 'NumOfMPPT', 'InputMode']:
            category = 'System Info'
        elif p in ['PacTogrid', 'PacStandAlone', 'EBackup']:
            category = 'Hybrid'

        rows.append([
            p,
            'N/A',
            f'abb_{p}',
            f'abb_{p}',
            '✓' if p in livedata_points else '',
            '✓' if p in feeds_points else '',
            'ABB Proprietary',
            category,
            'W' if 'P' in p and 'grid' in p else ('A' if 'Igrid' in p else ''),
            'measurement' if not p.startswith('E') else 'total_increasing',
            'power' if 'P' in p and 'grid' in p else ('current' if 'Igrid' in p else ''),
            'NO'
        ])

# Write all rows
for row_num, row_data in enumerate(rows, 2):
    for col_num, value in enumerate(row_data, 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.value = value
        cell.border = thin_border

        # Color code by model
        if row_data[6] == 'M64061':
            cell.fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
        elif row_data[6] == 'ABB Proprietary':
            cell.fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')

# Auto-size columns
for col_num in range(1, len(headers) + 1):
    column_letter = get_column_letter(col_num)
    max_length = len(headers[col_num - 1])
    for row in ws.iter_rows(min_row=2, min_col=col_num, max_col=col_num):
        if row[0].value:
            max_length = max(max_length, len(str(row[0].value)))
    ws.column_dimensions[column_letter].width = min(max_length + 2, 40)

# Freeze header row
ws.freeze_panes = 'A2'

# Add filter
ws.auto_filter.ref = ws.dimensions

# Add summary statistics
summary_ws = wb.create_sheet('Summary')
summary_ws.append(['Category', 'Count'])
summary_ws.append(['Total Points', len(rows)])
summary_ws.append(['Standard SunSpec (Both protocols)', len([r for r in rows if r[11] == 'YES'])])
summary_ws.append(['M64061 (Maybe in Modbus)', len([r for r in rows if r[6] == 'M64061'])])
summary_ws.append(['ABB Proprietary (REST only)', len([r for r in rows if r[6] == 'ABB Proprietary'])])
summary_ws.append(['In /livedata', len([r for r in rows if r[4] == '✓'])])
summary_ws.append(['In /feeds', len([r for r in rows if r[5] == '✓'])])

# Format summary
for row in summary_ws.iter_rows(min_row=1, max_row=summary_ws.max_row):
    row[0].font = Font(bold=True)

# Save workbook
output_path = 'docs/vsn-sunspec-point-mapping.xlsx'
wb.save(output_path)
print(f'✓ Excel file created: {output_path}')
print(f'  Total rows: {len(rows)}')
print(f'  Standard SunSpec: {len([r for r in rows if r[11] == "YES"])}')
print(f'  M64061: {len([r for r in rows if r[6] == "M64061"])}')
print(f'  ABB Proprietary: {len([r for r in rows if r[6] == "ABB Proprietary"])}')
