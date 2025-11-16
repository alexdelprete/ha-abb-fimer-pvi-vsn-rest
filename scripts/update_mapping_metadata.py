#!/usr/bin/env python3
"""Update VSN-to-SunSpec mapping file with missing device_class, units, state_class, and precision.

This script fixes the incomplete mapping entries identified from user feedback.
"""

import json
import sys
from pathlib import Path

# Define mapping fixes based on analysis
DEVICE_CLASS_FIXES = {
    # Current sensors
    "Iba": {
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "precision": 2,
    },
    "Iin1": {
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "precision": 2,
    },
    "Iin2": {
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "precision": 2,
    },
    "IleakInv": {
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "precision": 2,
    },
    "IleakDC": {
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "precision": 2,
    },
    # Voltage sensors
    "Vba": {
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "precision": 1,
    },
    "ShU": {
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "precision": 1,
    },
    "Vin1": {
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "precision": 1,
    },
    "Vin2": {
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "precision": 1,
    },
    # Power sensors
    "Pba": {
        "device_class": "power",
        "unit": "W",
        "state_class": "measurement",
        "precision": 0,
    },
    "MeterPgrid_L1": {
        "device_class": "power",
        "unit": "W",
        "state_class": "measurement",
        "precision": 0,
    },
    "MeterPgrid_L2": {
        "device_class": "power",
        "unit": "W",
        "state_class": "measurement",
        "precision": 0,
    },
    "MeterPgrid_L3": {
        "device_class": "power",
        "unit": "W",
        "state_class": "measurement",
        "precision": 0,
    },
    # Temperature sensors
    "Tba": {
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "precision": 1,
    },
    "TcMax": {
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "precision": 1,
    },
    "TcMin": {
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "precision": 1,
    },
    # Energy sensors (total_increasing)
    "ECt": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "EDt": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E4_runtime": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E4_7D": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E4_30D": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E5_runtime": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E5_7D": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E5_30D": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "Ein1": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "Ein2": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "EBackup": {
        "device_class": "energy",
        "unit": "Wh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    # Apparent power (VAh energy)
    "E2_runtime": {
        "device_class": "apparent_power",
        "unit": "VAh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E2_7D": {
        "device_class": "apparent_power",
        "unit": "VAh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    "E2_30D": {
        "device_class": "apparent_power",
        "unit": "VAh",
        "state_class": "total_increasing",
        "precision": 2,
    },
    # Frequency
    "Fcc": {
        "device_class": "frequency",
        "unit": "Hz",
        "state_class": "measurement",
        "precision": 2,
    },
    # Battery State of Charge
    "TSoc": {
        "device_class": "battery",
        "unit": "%",
        "state_class": "measurement",
        "precision": 0,
    },
    # Timestamp
    "SysTime": {
        "device_class": "timestamp",
        "unit": "",
        "state_class": "",
        "precision": 0,
    },
}

# Default precision by device_class for sensors that already have device_class
DEFAULT_PRECISION = {
    "power": 0,
    "current": 2,
    "voltage": 1,
    "energy": 2,
    "temperature": 1,
    "frequency": 2,
    "reactive_power": 0,
    "apparent_power": 0,
    "battery": 0,
    "timestamp": 0,
    "duration": 0,
    "": 0,  # No device class
}


def update_mapping_file(mapping_path: Path):
    """Update the mapping file with missing metadata."""

    print(f"Reading mapping file: {mapping_path}")
    with open(mapping_path, encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"Total entries in mapping: {len(mapping)}")

    # Track statistics
    stats = {
        "total": len(mapping),
        "updated_device_class": 0,
        "updated_unit": 0,
        "updated_state_class": 0,
        "added_precision": 0,
        "already_complete": 0,
    }

    # Update each entry
    for entry in mapping:
        vsn700_name = entry.get("REST Name (VSN700)", "")
        current_device_class = entry.get("HA Device Class", "")
        current_unit = entry.get("HA Unit of Measurement", "")
        current_state_class = entry.get("HA State Class", "")

        # Check if we have explicit fixes for this sensor
        if vsn700_name in DEVICE_CLASS_FIXES:
            fix = DEVICE_CLASS_FIXES[vsn700_name]

            # Update device_class if empty
            if not current_device_class and fix["device_class"]:
                entry["HA Device Class"] = fix["device_class"]
                stats["updated_device_class"] += 1

            # Update unit if empty
            if not current_unit and fix["unit"]:
                entry["HA Unit of Measurement"] = fix["unit"]
                stats["updated_unit"] += 1

            # Update state_class if empty
            if not current_state_class and fix["state_class"]:
                entry["HA State Class"] = fix["state_class"]
                stats["updated_state_class"] += 1

            # Add precision
            entry["Suggested Display Precision"] = fix["precision"]
            stats["added_precision"] += 1
        else:
            # For sensors without explicit fixes, add default precision based on device_class
            device_class = entry.get("HA Device Class", "")
            precision = DEFAULT_PRECISION.get(device_class, 0)
            entry["Suggested Display Precision"] = precision
            stats["added_precision"] += 1

            if current_device_class and current_unit and current_state_class:
                stats["already_complete"] += 1

    # Write updated mapping
    print(f"\nWriting updated mapping to: {mapping_path}")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    # Print statistics
    print("\n" + "=" * 60)
    print("UPDATE STATISTICS")
    print("=" * 60)
    print(f"Total entries: {stats['total']}")
    print(f"Updated device_class: {stats['updated_device_class']}")
    print(f"Updated unit: {stats['updated_unit']}")
    print(f"Updated state_class: {stats['updated_state_class']}")
    print(f"Added precision field: {stats['added_precision']}")
    print(f"Already complete: {stats['already_complete']}")
    print("=" * 60)

    return mapping, stats


def main():
    """Main entry point."""
    # Get repository root
    repo_root = Path(__file__).parent.parent
    mapping_path = (
        repo_root
        / "custom_components"
        / "abb_fimer_pvi_vsn_rest"
        / "abb_fimer_vsn_rest_client"
        / "data"
        / "vsn-sunspec-point-mapping.json"
    )

    if not mapping_path.exists():
        print(f"Error: Mapping file not found at {mapping_path}")
        sys.exit(1)

    # Update the mapping
    updated_mapping, stats = update_mapping_file(mapping_path)

    print("\nMapping file updated successfully!")
    print(f"Updated {stats['updated_device_class']} device_class fields")
    print(f"Updated {stats['updated_unit']} unit fields")
    print(f"Updated {stats['updated_state_class']} state_class fields")
    print(f"Added precision to all {stats['added_precision']} entries")


if __name__ == "__main__":
    main()
