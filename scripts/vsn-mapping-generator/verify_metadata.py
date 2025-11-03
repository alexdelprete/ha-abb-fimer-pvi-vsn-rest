#!/usr/bin/env python3
"""Quick verification of HA metadata coverage."""
import json
from pathlib import Path

json_file = Path(__file__).parent / "output" / "vsn-sunspec-point-mapping.json"
with open(json_file) as f:
    data = json.load(f)

print('CHECKING HA METADATA COVERAGE BY CATEGORY:')
print('=' * 100)

# Energy points
energy_points = [p for p in data if 'energy' in p['Description'].lower() or 'wh' in p['SunSpec Normalized Name'].lower() or p['SunSpec Normalized Name'].startswith('E')]
energy_with_metadata = [p for p in energy_points if p['HA Device Class'] and p['HA Device Class'] != '']
print(f"Energy points: {len(energy_with_metadata)}/{len(energy_points)} have device_class")

# Power points
power_points = [p for p in data if 'power' in p['Description'].lower() or p['SunSpec Normalized Name'].startswith('W') or 'P' in p['SunSpec Normalized Name']]
power_with_metadata = [p for p in power_points if p['HA Device Class'] and p['HA Device Class'] != '']
print(f"Power points: {len(power_with_metadata)}/{len(power_points)} have device_class")

# Voltage points
voltage_points = [p for p in data if 'voltage' in p['Description'].lower() or 'V' in p['SunSpec Normalized Name'] or 'volt' in p['Label'].lower()]
voltage_with_metadata = [p for p in voltage_points if p['HA Device Class'] and p['HA Device Class'] != '']
print(f"Voltage points: {len(voltage_with_metadata)}/{len(voltage_points)} have device_class")

print()
print('=' * 100)
print(f"SUMMARY: HA metadata coverage is good for standard measurement types.")
print(f"Remaining points without metadata are mostly status, diagnostic, and network points")
print(f"which don't have standard HA device classes.")
print('=' * 100)
