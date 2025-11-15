#!/usr/bin/env python3
"""Generate complete German translations from English source."""

import json
from pathlib import Path

# Complete German translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Leistung AC",
    "Reactive Power - Grid Connection": "Blindleistung - Netzverbindung",
    "Frequency AC - Grid": "Frequenz AC - Netz",
    "Current AC": "Strom AC",
    "Power DC": "Leistung DC",
    "Voltage DC": "Spannung DC",
    "Voltage AC": "Spannung AC",
    "Current DC": "Strom DC",
    "DC energy": "Energie DC",
    "Energy AC": "Energie AC",
    "Energy DC": "Energie DC",
    "Energy": "Energie",
    "energy": "Energie",
    "Power": "Leistung",
    "Voltage": "Spannung",
    "Current": "Strom",
    "Temperature": "Temperatur",
    "Frequency": "Frequenz",
    # Components
    "Phase A": "Phase A",
    "Phase B": "Phase B",
    "Phase C": "Phase C",
    "Phase A-N": "Phase A-N",
    "Phase B-N": "Phase B-N",
    "Phase C-N": "Phase C-N",
    "Phase A-B": "Phase A-B",
    "Phase B-C": "Phase B-C",
    "Phase C-A": "Phase C-A",
    "String 1": "String 1",
    "String 2": "String 2",
    "PV Input": "PV",
    "Input 1": "Eingang 1",
    "Input 2": "Eingang 2",
    "Fan 1": "Lüfter 1",
    "Fan 2": "Lüfter 2",
    # Locations/Device types
    "Cabinet": "Schrank",
    "Booster": "Booster",
    "Inverter": "Wechselrichter",
    "Meter": "Zähler",
    "House": "Haus",
    "Grid": "Netz",
    "Ground": "Erde",
    "Battery": "Batterie",
    "Heatsink": "Kühlkörper",
    "Other": "Andere",
    "Shunt": "Shunt",
    "Sensor 1": "Sensor 1",
    "Bus Midpoint": "Bus Mittelpunkt",
    "Bulk Capacitor": "Bulk Kondensator",
    # States/Status
    "Status": "Status",
    "State": "Zustand",
    "Alarm Status": "Alarm Status",
    "Alarm State": "Alarm Zustand",
    "Global Status": "Globaler Status",
    "Inverter Status": "Wechselrichter Status",
    "Inverter State": "Wechselrichter Zustand",
    "Clock State": "Uhr Zustand",
    "Digital Input Status": "Digitaleingang Status",
    "DC Input 1 Status": "DC Eingang 1 Status",
    "DC Input 2 Status": "DC Eingang 2 Status",
    "DC Input 1 State": "DC Eingang 1 Zustand",
    "DC Input 2 State": "DC Eingang 2 Zustand",
    "Global operational state": "Globaler Betriebszustand",
    "State of Health": "Gesundheitszustand",
    "State of Charge": "Ladezustand",
    "Battery Control State": "Batteriesteuerung Zustand",
    "Grid External Control State": "Netz Externe Steuerung Zustand",
    "Fault Ride Through (FRT) status": "Fault Ride Through (FRT) Status",
    # Modes
    "Mode": "Modus",
    "Battery Mode": "Batterie Modus",
    "Input Mode": "Eingang Modus",
    "Digital Input 0 Mode": "Digitaleingang 0 Modus",
    "Digital Input 1 Mode": "Digitaleingang 1 Modus",
    "Stand Alone Mode": "Standalone Modus",
    # Time periods
    "Lifetime": "Gesamt",
    "Since Restart": "Seit Neustart",
    "Last 7 Days": "Letzte 7 Tage",
    "Last 30 Days": "Letzte 30 Tage",
    "Last Week": "Letzte Woche",
    "Last Month": "Letzter Monat",
    "Last Year": "Letztes Jahr",
    "Today": "Heute",
    # Operations
    "Produced": "Erzeugt",
    "Absorbed": "Aufgenommen",
    "Import": "Import",
    "Export": "Export",
    "Backup Output": "Backup Ausgang",
    "Consumption": "Verbrauch",
    "Home PV": "PV Haus",
    "from": "vom",
    # Battery terms
    "Battery Charge": "Batterieladung",
    "Battery Discharge": "Batterieentladung",
    "Battery Total": "Batterie Gesamt",
    "Battery Cycles": "Batteriezyklen",
    "Battery Cell Max": "Batteriezelle Max",
    "Battery Cell Min": "Batteriezelle Min",
    # Power terms
    "Peak": "Spitze",
    "Rating": "Nennwert",
    "Power Factor": "Leistungsfaktor",
    "Apparent": "Scheinleistung",
    "Reactive": "Blindleistung",
    "AC Power Derating Flags": "AC Leistung Derating Flags",
    "Reactive Power Derating": "Blindleistung Derating",
    "Apparent Power Derating": "Scheinleistung Derating",
    # Energy terms
    "Self-consumed energy": "Selbst verbrauchte Energie",
    "Total energy from direct transducer (DT)": "Gesamtenergie vom Direktwandler (DT)",
    "Total energy from current transformer (CT)": "Gesamtenergie vom Stromwandler (CT)",
    # Measurements
    "Leakage DC-AC": "Leckstrom DC-AC",
    "Leakage DC-DC": "Leckstrom DC-DC",
    "Leakage": "Leckstrom",
    "Insulation": "Isolierung",
    "Resistance": "Widerstand",
    "Load": "Last",
    "Input Total": "Eingang Gesamt",
    "House Load Total": "Hauslast Gesamt",
    # Device info
    "Manufacturer name": "Herstellername",
    "Model identifier": "Modellkennung",
    "Configuration options": "Konfigurationsoptionen",
    "Firmware version": "Firmware Version",
    "Firmware Version": "Firmware Version",
    "Firmware Build Date": "Firmware Build Datum",
    "Firmware Build Hash": "Firmware Build Hash",
    "Firmware Revision": "Firmware Revision",
    "Serial number": "Seriennummer",
    "Serial Number": "Seriennummer",
    "Modbus address": "Modbus Adresse",
    "Product number": "Produktnummer",
    "Part Number": "Teilenummer",
    "Manufacturing Week/Year": "Fertigungswoche/Jahr",
    "Model Type": "Modelltyp",
    "Model Description": "Modellbeschreibung",
    "Device 2 Name": "Gerät 2 Name",
    "Device 2 Type": "Gerät 2 Typ",
    "Type": "Typ",
    # System
    "System Time": "Systemzeit",
    "System Uptime": "System Betriebszeit",
    "System load average": "System Durchschnittslast",
    "Available flash storage": "Verfügbarer Flash-Speicher",
    "Flash storage used": "Verwendeter Flash-Speicher",
    "Available RAM": "Verfügbares RAM",
    "Detected Battery Number": "Erkannte Batterienummer",
    "Number of battery cells or modules": "Anzahl Batteriezellen oder Module",
    # Settings
    "Country grid standard setting": "Landesnetz Standard Einstellung",
    "Split-phase configuration flag": "Split-Phase Konfiguration Flag",
    "Commissioning Freeze": "Inbetriebnahme Einfrieren",
    "Dynamic Feed In Ctrl": "Dynamische Einspeisung Steuerung",
    "Energy Policy": "Energiepolitik",
    "Battery Control Enabled": "Batteriesteuerung Aktiviert",
    "Grid External Control Enabled": "Netz Externe Steuerung Aktiviert",
    "Model 126 Enabled": "Modell 126 Aktiviert",
    "Model 132 Enabled": "Modell 132 Aktiviert",
    "Enabled": "Aktiviert",
    # Counters
    "Battery charge cycles counter": "Batterieladezyklen Zähler",
    "Battery discharge cycles counter": "Batterieentladezyklen Zähler",
    "Count": "Anzahl",
    "Channels": "Kanäle",
    # WiFi
    "WiFi Mode": "WiFi Modus",
    "WiFi SSID": "WiFi SSID",
    "WiFi Local IP": "WiFi Lokale IP",
    "WiFi link quality percentage": "WiFi Link Qualität Prozent",
    "WiFi FSM Status": "WiFi FSM Status",
    "WiFi Status": "WiFi Status",
    "WiFi AP Status": "WiFi AP Status",
    "WiFi DHCP State": "WiFi DHCP Zustand",
    "WiFi IP Address": "WiFi IP Adresse",
    "WiFi Netmask": "WiFi Netzmaske",
    "WiFi Broadcast": "WiFi Broadcast",
    "WiFi Gateway": "WiFi Gateway",
    "WiFi DNS Server": "WiFi DNS Server",
    # Logger
    "Logger Serial Number": "Logger Seriennummer",
    "Logger Board Model": "Logger Board Modell",
    "Logger Hostname": "Logger Hostname",
    "Logger ID": "Logger ID",
    # Other
    "Communication Protocol": "Kommunikationsprotokoll",
    "Inverter ID": "Wechselrichter ID",
    "Inverter Time": "Wechselrichter Zeit",
    "Central controller frequency": "Zentralsteuerung Frequenz",
    "Warning Flags": "Warnungs Flags",
    "Flags": "Flags",
    "Speed": "Geschwindigkeit",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Fw Version",
    "Connection": "Verbindung",
}


def translate(text: str) -> str:
    """Translate English text to German using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        german = TRANSLATIONS[english]
        result = result.replace(english, german)

    return result


def main():
    """Generate complete German translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, encoding="utf-8") as f:
        en_data = json.load(f)

    # Load current German (to preserve config/options sections which are already good)
    de_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/de.json")
    with open(de_file, encoding="utf-8") as f:
        de_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data["entity"]["sensor"].items():
        english_name = value["name"]
        german_name = translate(english_name)
        de_data["entity"]["sensor"][key] = {"name": german_name}

    # Save updated translations
    with open(de_file, "w", encoding="utf-8") as f:
        json.dump(de_data, f, ensure_ascii=False, indent=2)

    print("✓ German translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data["entity"]["sensor"].items())[:15]
    for key, value in samples:
        en_name = value["name"]
        de_name = de_data["entity"]["sensor"][key]["name"]
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    DE: {de_name}")


if __name__ == "__main__":
    main()
