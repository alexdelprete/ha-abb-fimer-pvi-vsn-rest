#!/usr/bin/env python3
"""Generate complete Italian translations from English source."""

import json
import re
from pathlib import Path

# Complete Italian translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Potenza AC",
    "Reactive Power - Grid Connection": "Potenza Reattiva - Connessione Rete",
    "Frequency AC - Grid": "Frequenza AC - Rete",
    "Current AC": "Corrente AC",
    "Power DC": "Potenza DC",
    "Voltage DC": "Tensione DC",
    "Voltage AC": "Tensione AC",
    "Current DC": "Corrente DC",
    "Current": "Corrente",
    "Temperature": "Temperatura",
    "Energy AC": "Energia AC",
    "Energy DC": "Energia DC",
    "DC energy": "Energia DC",
    "Energy": "Energia",
    "energy": "energia",
    "Power": "Potenza",
    "Voltage": "Tensione",
    "Frequency": "Frequenza",

    # Components
    "Phase A": "Fase A",
    "Phase B": "Fase B",
    "Phase C": "Fase C",
    "Phase A-N": "Fase A-N",
    "Phase B-N": "Fase B-N",
    "Phase C-N": "Fase C-N",
    "Phase A-B": "Fase A-B",
    "Phase B-C": "Fase B-C",
    "Phase C-A": "Fase C-A",
    "String 1": "Stringa 1",
    "String 2": "Stringa 2",
    "PV Input": "PV",
    "Input 1": "Ingresso 1",
    "Input 2": "Ingresso 2",
    "Fan 1": "Ventola 1",
    "Fan 2": "Ventola 2",

    # Locations/Device types
    "Cabinet": "Armadio",
    "Booster": "Booster",
    "Inverter": "Inverter",
    "Meter": "Contatore",
    "House": "Casa",
    "Grid": "Rete",
    "Ground": "Terra",
    "Battery": "Batteria",
    "Heatsink": "Dissipatore",
    "Other": "Altro",
    "Shunt": "Shunt",
    "Sensor 1": "Sensore 1",
    "Bus Midpoint": "Punto Medio Bus",
    "Bulk Capacitor": "Condensatore Bulk",

    # States/Status
    "Status": "Stato",
    "State": "Stato",
    "Alarm Status": "Stato Allarme",
    "Alarm State": "Stato Allarme",
    "Global Status": "Stato Globale",
    "Inverter Status": "Stato Inverter",
    "Inverter State": "Stato Inverter",
    "Clock State": "Stato Orologio",
    "Digital Input Status": "Stato Ingresso Digitale",
    "DC Input 1 Status": "Stato Ingresso DC 1",
    "DC Input 2 Status": "Stato Ingresso DC 2",
    "DC Input 1 State": "Stato Ingresso DC 1",
    "DC Input 2 State": "Stato Ingresso DC 2",
    "Global operational state": "Stato operativo globale",
    "State of Health": "Stato di Salute",
    "State of Charge": "Stato di Carica",
    "Battery Control State": "Stato Controllo Batteria",
    "Grid External Control State": "Stato Controllo Esterno Rete",
    "Fault Ride Through (FRT) status": "Stato Fault Ride Through (FRT)",

    # Modes
    "Mode": "Modalità",
    "Battery Mode": "Modalità Batteria",
    "Input Mode": "Modalità Ingresso",
    "Digital Input 0 Mode": "Modalità Ingresso Digitale 0",
    "Digital Input 1 Mode": "Modalità Ingresso Digitale 1",
    "Stand Alone Mode": "Modalità Stand Alone",

    # Time periods
    "Lifetime": "Totale",
    "Since Restart": "Dal Riavvio",
    "Last 7 Days": "Ultimi 7 Giorni",
    "Last 30 Days": "Ultimi 30 Giorni",
    "Last Week": "Settimana Scorsa",
    "Last Month": "Mese Scorso",
    "Last Year": "Anno Scorso",
    "Today": "Oggi",

    # Operations
    "Produced": "Prodotta",
    "Absorbed": "Assorbita",
    "Import": "Importazione",
    "Export": "Esportazione",
    "Backup Output": "Uscita Backup",
    "Consumption": "Consumo",
    "Home PV": "PV Casa",
    "from": "da",

    # Battery terms
    "Battery Charge": "Carica Batteria",
    "Battery Discharge": "Scarica Batteria",
    "Battery Total": "Totale Batteria",
    "Battery Cycles": "Cicli Batteria",
    "Battery Cell Max": "Cella Batteria Max",
    "Battery Cell Min": "Cella Batteria Min",

    # Power terms
    "Peak": "Picco",
    "Rating": "Nominale",
    "Power Factor": "Fattore di Potenza",
    "Apparent": "Apparente",
    "Reactive": "Reattiva",
    "AC Power Derating Flags": "Flag Riduzione Potenza AC",
    "Reactive Power Derating": "Riduzione Potenza Reattiva",
    "Apparent Power Derating": "Riduzione Potenza Apparente",

    # Energy terms
    "Self-consumed energy": "Energia autoconsumata",
    "Total energy from direct transducer (DT)": "Energia totale da trasduttore diretto (DT)",
    "Total energy from current transformer (CT)": "Energia totale da trasformatore di corrente (CT)",

    # Measurements
    "Leakage DC-AC": "Perdita DC-AC",
    "Leakage DC-DC": "Perdita DC-DC",
    "Leakage": "Perdita",
    "Insulation": "Isolamento",
    "Resistance": "Resistenza",
    "Load": "Carico",
    "Input Total": "Totale Ingresso",
    "House Load Total": "Totale Carico Casa",

    # Device info
    "Manufacturer name": "Nome produttore",
    "Model identifier": "Identificatore modello",
    "Configuration options": "Opzioni di configurazione",
    "Firmware version": "Versione firmware",
    "Firmware Version": "Versione Firmware",
    "Firmware Build Date": "Data Build Firmware",
    "Firmware Build Hash": "Hash Build Firmware",
    "Firmware Revision": "Revisione Firmware",
    "Serial number": "Numero di serie",
    "Serial Number": "Numero di Serie",
    "Modbus address": "Indirizzo Modbus",
    "Product number": "Codice prodotto",
    "Part Number": "Codice Parte",
    "Manufacturing Week/Year": "Settimana/Anno Produzione",
    "Model Type": "Tipo Modello",
    "Model Description": "Descrizione Modello",
    "Device 2 Name": "Nome Dispositivo 2",
    "Device 2 Type": "Tipo Dispositivo 2",
    "Type": "Tipo",

    # System
    "System Time": "Ora Sistema",
    "System Uptime": "Uptime Sistema",
    "System load average": "Carico medio sistema",
    "Available flash storage": "Memoria flash disponibile",
    "Flash storage used": "Memoria flash utilizzata",
    "Available RAM": "RAM disponibile",
    "Detected Battery Number": "Numero Batteria Rilevato",
    "Number of battery cells or modules": "Numero celle o moduli batteria",

    # Settings
    "Country grid standard setting": "Impostazione standard rete paese",
    "Split-phase configuration flag": "Flag configurazione split-phase",
    "Commissioning Freeze": "Blocco Messa in Servizio",
    "Dynamic Feed In Ctrl": "Controllo Immissione Dinamica",
    "Energy Policy": "Politica Energetica",
    "Battery Control Enabled": "Controllo Batteria Abilitato",
    "Grid External Control Enabled": "Controllo Esterno Rete Abilitato",
    "Model 126 Enabled": "Modello 126 Abilitato",
    "Model 132 Enabled": "Modello 132 Abilitato",
    "Enabled": "Abilitato",

    # Counters
    "Battery charge cycles counter": "Contatore cicli carica batteria",
    "Battery discharge cycles counter": "Contatore cicli scarica batteria",
    "Count": "Conteggio",
    "Channels": "Canali",

    # WiFi
    "WiFi Mode": "Modalità WiFi",
    "WiFi SSID": "SSID WiFi",
    "WiFi Local IP": "IP Locale WiFi",
    "WiFi link quality percentage": "Percentuale qualità link WiFi",
    "WiFi FSM Status": "Stato FSM WiFi",
    "WiFi Status": "Stato WiFi",
    "WiFi AP Status": "Stato AP WiFi",
    "WiFi DHCP State": "Stato DHCP WiFi",
    "WiFi IP Address": "Indirizzo IP WiFi",
    "WiFi Netmask": "Maschera di Rete WiFi",
    "WiFi Broadcast": "Broadcast WiFi",
    "WiFi Gateway": "Gateway WiFi",
    "WiFi DNS Server": "Server DNS WiFi",

    # Logger
    "Logger Serial Number": "Numero di Serie Logger",
    "Logger Board Model": "Modello Scheda Logger",
    "Logger Hostname": "Hostname Logger",
    "Logger ID": "ID Logger",

    # Other
    "Communication Protocol": "Protocollo Comunicazione",
    "Inverter ID": "ID Inverter",
    "Inverter Time": "Ora Inverter",
    "Central controller frequency": "Frequenza controller centrale",
    "Warning Flags": "Flag Avviso",
    "Flags": "Flag",
    "Speed": "Velocità",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Versione Fw",
}

def translate(text: str) -> str:
    """Translate English text to Italian using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        italian = TRANSLATIONS[english]
        result = result.replace(english, italian)

    return result

def main():
    """Generate complete Italian translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Load current Italian (to preserve config/options sections which are already good)
    it_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/it.json")
    with open(it_file, 'r', encoding='utf-8') as f:
        it_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data['entity']['sensor'].items():
        english_name = value['name']
        italian_name = translate(english_name)
        it_data['entity']['sensor'][key] = {"name": italian_name}

    # Save updated translations
    with open(it_file, 'w', encoding='utf-8') as f:
        json.dump(it_data, f, ensure_ascii=False, indent=2)

    print("✓ Italian translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data['entity']['sensor'].items())[:15]
    for key, value in samples:
        en_name = value['name']
        it_name = it_data['entity']['sensor'][key]['name']
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    IT: {it_name}")

if __name__ == "__main__":
    main()
