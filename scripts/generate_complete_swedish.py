#!/usr/bin/env python3
"""Generate complete Swedish translations from English source."""

import json
from pathlib import Path

# Complete Swedish translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Effekt AC",
    "Reactive Power - Grid Connection": "Reaktiv effekt - Nätanslutning",
    "Frequency AC - Grid": "Frekvens AC - Nät",
    "Current AC": "Ström AC",
    "Power DC": "Effekt DC",
    "Voltage DC": "Spänning DC",
    "Voltage AC": "Spänning AC",
    "Current DC": "Ström DC",
    "DC energy": "Energi DC",
    "Energy AC": "Energi AC",
    "Energy DC": "Energi DC",
    "Energy": "Energi",
    "energy": "energi",
    "Power": "Effekt",
    "Voltage": "Spänning",
    "Current": "Ström",
    "Temperature": "Temperatur",
    "Frequency": "Frekvens",
    # Components
    "Phase A": "Fas A",
    "Phase B": "Fas B",
    "Phase C": "Fas C",
    "Phase A-N": "Fas A-N",
    "Phase B-N": "Fas B-N",
    "Phase C-N": "Fas C-N",
    "Phase A-B": "Fas A-B",
    "Phase B-C": "Fas B-C",
    "Phase C-A": "Fas C-A",
    "String 1": "Sträng 1",
    "String 2": "Sträng 2",
    "PV Input": "PV",
    "Input 1": "Ingång 1",
    "Input 2": "Ingång 2",
    "Fan 1": "Fläkt 1",
    "Fan 2": "Fläkt 2",
    # Locations/Device types
    "Cabinet": "Skåp",
    "Booster": "Booster",
    "Inverter": "Växelriktare",
    "Meter": "Mätare",
    "House": "Hus",
    "Grid": "Nät",
    "Ground": "Jord",
    "Battery": "Batteri",
    "Heatsink": "Kylflänsar",
    "Other": "Annan",
    "Shunt": "Shunt",
    "Sensor 1": "Sensor 1",
    "Bus Midpoint": "Buss Mittpunkt",
    "Bulk Capacitor": "Bulk Kondensator",
    # States/Status
    "Status": "Status",
    "State": "Tillstånd",
    "Alarm Status": "Larm Status",
    "Alarm State": "Larm Tillstånd",
    "Global Status": "Global Status",
    "Inverter Status": "Växelriktare Status",
    "Inverter State": "Växelriktare Tillstånd",
    "Clock State": "Klocka Tillstånd",
    "Digital Input Status": "Digital Ingång Status",
    "DC Input 1 Status": "DC Ingång 1 Status",
    "DC Input 2 Status": "DC Ingång 2 Status",
    "DC Input 1 State": "DC Ingång 1 Tillstånd",
    "DC Input 2 State": "DC Ingång 2 Tillstånd",
    "Global operational state": "Globalt drifttillstånd",
    "State of Health": "Hälsotillstånd",
    "State of Charge": "Laddningstillstånd",
    "Battery Control State": "Batteristyrning Tillstånd",
    "Grid External Control State": "Nät Extern Styrning Tillstånd",
    "Fault Ride Through (FRT) status": "Fault Ride Through (FRT) Status",
    # Modes
    "Mode": "Läge",
    "Battery Mode": "Batteriläge",
    "Input Mode": "Ingångsläge",
    "Digital Input 0 Mode": "Digital Ingång 0 Läge",
    "Digital Input 1 Mode": "Digital Ingång 1 Läge",
    "Stand Alone Mode": "Fristående Läge",
    # Time periods
    "Lifetime": "Total",
    "Since Restart": "Sedan Omstart",
    "Last 7 Days": "Senaste 7 Dagarna",
    "Last 30 Days": "Senaste 30 Dagarna",
    "Last Week": "Senaste Veckan",
    "Last Month": "Senaste Månaden",
    "Last Year": "Senaste Året",
    "Today": "Idag",
    # Operations
    "Produced": "Producerad",
    "Absorbed": "Absorberad",
    "Import": "Import",
    "Export": "Export",
    "Backup Output": "Backup Utgång",
    "Consumption": "Förbrukning",
    "Home PV": "PV Hem",
    "from": "från",
    # Battery terms
    "Battery Charge": "Batteriladdning",
    "Battery Discharge": "Batteriurladdning",
    "Battery Total": "Batteri Total",
    "Battery Cycles": "Battericykler",
    "Battery Cell Max": "Battericell Max",
    "Battery Cell Min": "Battericell Min",
    # Power terms
    "Peak": "Topp",
    "Rating": "Märkvärde",
    "Power Factor": "Effektfaktor",
    "Apparent": "Skenbar",
    "Reactive": "Reaktiv",
    "AC Power Derating Flags": "AC Effekt Derating Flaggor",
    "Reactive Power Derating": "Reaktiv Effekt Derating",
    "Apparent Power Derating": "Skenbar Effekt Derating",
    # Energy terms
    "Self-consumed energy": "Själv förbrukad energi",
    "Total energy from direct transducer (DT)": "Total energi från direkt givare (DT)",
    "Total energy from current transformer (CT)": "Total energi från strömtransformator (CT)",
    # Measurements
    "Leakage DC-AC": "Läckage DC-AC",
    "Leakage DC-DC": "Läckage DC-DC",
    "Leakage": "Läckage",
    "Insulation": "Isolering",
    "Resistance": "Motstånd",
    "Load": "Last",
    "Input Total": "Ingång Total",
    "House Load Total": "Huslast Total",
    # Device info
    "Manufacturer name": "Tillverkarnamn",
    "Model identifier": "Modellidentifierare",
    "Configuration options": "Konfigurationsalternativ",
    "Firmware version": "Firmware version",
    "Firmware Version": "Firmware Version",
    "Firmware Build Date": "Firmware Build Datum",
    "Firmware Build Hash": "Firmware Build Hash",
    "Firmware Revision": "Firmware Revision",
    "Serial number": "Serienummer",
    "Serial Number": "Serienummer",
    "Modbus address": "Modbus adress",
    "Product number": "Produktnummer",
    "Part Number": "Delnummer",
    "Manufacturing Week/Year": "Tillverkningsvecka/År",
    "Model Type": "Modelltyp",
    "Model Description": "Modellbeskrivning",
    "Device 2 Name": "Enhet 2 Namn",
    "Device 2 Type": "Enhet 2 Typ",
    "Type": "Typ",
    # System
    "System Time": "Systemtid",
    "System Uptime": "System Drifttid",
    "System load average": "System genomsnittlig last",
    "Available flash storage": "Tillgängligt flash-minne",
    "Flash storage used": "Använt flash-minne",
    "Available RAM": "Tillgängligt RAM",
    "Detected Battery Number": "Detekterat Batterinummer",
    "Number of battery cells or modules": "Antal battericeller eller moduler",
    # Settings
    "Country grid standard setting": "Landsnät standard inställning",
    "Split-phase configuration flag": "Split-fas konfigurationsflagga",
    "Commissioning Freeze": "Driftsättning Frys",
    "Dynamic Feed In Ctrl": "Dynamisk Inmatning Styrning",
    "Energy Policy": "Energipolicy",
    "Battery Control Enabled": "Batteristyrning Aktiverad",
    "Grid External Control Enabled": "Nät Extern Styrning Aktiverad",
    "Model 126 Enabled": "Modell 126 Aktiverad",
    "Model 132 Enabled": "Modell 132 Aktiverad",
    "Enabled": "Aktiverad",
    # Counters
    "Battery charge cycles counter": "Batteriladdningscykler räknare",
    "Battery discharge cycles counter": "Batteriurladdningscykler räknare",
    "Count": "Antal",
    "Channels": "Kanaler",
    # WiFi
    "WiFi Mode": "WiFi Läge",
    "WiFi SSID": "WiFi SSID",
    "WiFi Local IP": "WiFi Lokal IP",
    "WiFi link quality percentage": "WiFi länk kvalitet procent",
    "WiFi FSM Status": "WiFi FSM Status",
    "WiFi Status": "WiFi Status",
    "WiFi AP Status": "WiFi AP Status",
    "WiFi DHCP State": "WiFi DHCP Tillstånd",
    "WiFi IP Address": "WiFi IP Adress",
    "WiFi Netmask": "WiFi Nätmask",
    "WiFi Broadcast": "WiFi Broadcast",
    "WiFi Gateway": "WiFi Gateway",
    "WiFi DNS Server": "WiFi DNS Server",
    # Logger
    "Logger Serial Number": "Logger Serienummer",
    "Logger Board Model": "Logger Kort Modell",
    "Logger Hostname": "Logger Hostname",
    "Logger ID": "Logger ID",
    # Other
    "Communication Protocol": "Kommunikationsprotokoll",
    "Inverter ID": "Växelriktare ID",
    "Inverter Time": "Växelriktare Tid",
    "Central controller frequency": "Central styrenhet frekvens",
    "Warning Flags": "Varningsflaggor",
    "Flags": "Flaggor",
    "Speed": "Hastighet",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Fw Version",
    "Connection": "Anslutning",
}


def translate(text: str) -> str:
    """Translate English text to Swedish using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        swedish = TRANSLATIONS[english]
        result = result.replace(english, swedish)

    return result


def main():
    """Generate complete Swedish translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, encoding="utf-8") as f:
        en_data = json.load(f)

    # Load current Swedish (to preserve config/options sections which are already good)
    sv_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/sv.json")
    with open(sv_file, encoding="utf-8") as f:
        sv_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data["entity"]["sensor"].items():
        english_name = value["name"]
        swedish_name = translate(english_name)
        sv_data["entity"]["sensor"][key] = {"name": swedish_name}

    # Save updated translations
    with open(sv_file, "w", encoding="utf-8") as f:
        json.dump(sv_data, f, ensure_ascii=False, indent=2)

    print("✓ Swedish translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data["entity"]["sensor"].items())[:15]
    for key, value in samples:
        en_name = value["name"]
        sv_name = sv_data["entity"]["sensor"][key]["name"]
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    SV: {sv_name}")


if __name__ == "__main__":
    main()
