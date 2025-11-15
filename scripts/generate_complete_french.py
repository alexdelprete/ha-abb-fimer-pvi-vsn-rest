#!/usr/bin/env python3
"""Generate complete French translations from English source."""

import json
from pathlib import Path

# Complete French translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Puissance AC",
    "Reactive Power - Grid Connection": "Puissance Réactive - Connexion Réseau",
    "Frequency AC - Grid": "Fréquence AC - Réseau",
    "Current AC": "Courant AC",
    "Power DC": "Puissance DC",
    "Voltage DC": "Tension DC",
    "Voltage AC": "Tension AC",
    "Current DC": "Courant DC",
    "DC energy": "Énergie DC",
    "Energy AC": "Énergie AC",
    "Energy DC": "Énergie DC",
    "Energy": "Énergie",
    "energy": "énergie",
    "Power": "Puissance",
    "Voltage": "Tension",
    "Current": "Courant",
    "Temperature": "Température",
    "Frequency": "Fréquence",
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
    "String 1": "Chaîne 1",
    "String 2": "Chaîne 2",
    "PV Input": "PV",
    "Input 1": "Entrée 1",
    "Input 2": "Entrée 2",
    "Fan 1": "Ventilateur 1",
    "Fan 2": "Ventilateur 2",
    # Locations/Device types
    "Cabinet": "Armoire",
    "Booster": "Booster",
    "Inverter": "Onduleur",
    "Meter": "Compteur",
    "House": "Maison",
    "Grid": "Réseau",
    "Ground": "Terre",
    "Battery": "Batterie",
    "Heatsink": "Dissipateur",
    "Other": "Autre",
    "Shunt": "Shunt",
    "Sensor 1": "Capteur 1",
    "Bus Midpoint": "Point Milieu Bus",
    "Bulk Capacitor": "Condensateur Bulk",
    # States/Status
    "Status": "État",
    "State": "État",
    "Alarm Status": "État Alarme",
    "Alarm State": "État Alarme",
    "Global Status": "État Global",
    "Inverter Status": "État Onduleur",
    "Inverter State": "État Onduleur",
    "Clock State": "État Horloge",
    "Digital Input Status": "État Entrée Numérique",
    "DC Input 1 Status": "État Entrée DC 1",
    "DC Input 2 Status": "État Entrée DC 2",
    "DC Input 1 State": "État Entrée DC 1",
    "DC Input 2 State": "État Entrée DC 2",
    "Global operational state": "État opérationnel global",
    "State of Health": "État de Santé",
    "State of Charge": "État de Charge",
    "Battery Control State": "État Contrôle Batterie",
    "Grid External Control State": "État Contrôle Externe Réseau",
    "Fault Ride Through (FRT) status": "État Fault Ride Through (FRT)",
    # Modes
    "Mode": "Mode",
    "Battery Mode": "Mode Batterie",
    "Input Mode": "Mode Entrée",
    "Digital Input 0 Mode": "Mode Entrée Numérique 0",
    "Digital Input 1 Mode": "Mode Entrée Numérique 1",
    "Stand Alone Mode": "Mode Autonome",
    # Time periods
    "Lifetime": "Total",
    "Since Restart": "Depuis Redémarrage",
    "Last 7 Days": "7 Derniers Jours",
    "Last 30 Days": "30 Derniers Jours",
    "Last Week": "Semaine Dernière",
    "Last Month": "Mois Dernier",
    "Last Year": "Année Dernière",
    "Today": "Aujourd'hui",
    # Operations
    "Produced": "Produite",
    "Absorbed": "Absorbée",
    "Import": "Importation",
    "Export": "Exportation",
    "Backup Output": "Sortie Secours",
    "Consumption": "Consommation",
    "Home PV": "PV Maison",
    "from": "depuis",
    # Battery terms
    "Battery Charge": "Charge Batterie",
    "Battery Discharge": "Décharge Batterie",
    "Battery Total": "Total Batterie",
    "Battery Cycles": "Cycles Batterie",
    "Battery Cell Max": "Cellule Batterie Max",
    "Battery Cell Min": "Cellule Batterie Min",
    # Power terms
    "Peak": "Crête",
    "Rating": "Nominal",
    "Power Factor": "Facteur de Puissance",
    "Apparent": "Apparente",
    "Reactive": "Réactive",
    "AC Power Derating Flags": "Flags Réduction Puissance AC",
    "Reactive Power Derating": "Réduction Puissance Réactive",
    "Apparent Power Derating": "Réduction Puissance Apparente",
    # Energy terms
    "Self-consumed energy": "Énergie autoconsommée",
    "Total energy from direct transducer (DT)": "Énergie totale du transducteur direct (DT)",
    "Total energy from current transformer (CT)": "Énergie totale du transformateur de courant (CT)",
    # Measurements
    "Leakage DC-AC": "Fuite DC-AC",
    "Leakage DC-DC": "Fuite DC-DC",
    "Leakage": "Fuite",
    "Insulation": "Isolation",
    "Resistance": "Résistance",
    "Load": "Charge",
    "Input Total": "Total Entrée",
    "House Load Total": "Charge Maison Totale",
    # Device info
    "Manufacturer name": "Nom fabricant",
    "Model identifier": "Identifiant modèle",
    "Configuration options": "Options de configuration",
    "Firmware version": "Version firmware",
    "Firmware Version": "Version Firmware",
    "Firmware Build Date": "Date Build Firmware",
    "Firmware Build Hash": "Hash Build Firmware",
    "Firmware Revision": "Révision Firmware",
    "Serial number": "Numéro de série",
    "Serial Number": "Numéro de Série",
    "Modbus address": "Adresse Modbus",
    "Product number": "Numéro produit",
    "Part Number": "Numéro Pièce",
    "Manufacturing Week/Year": "Semaine/Année Production",
    "Model Type": "Type Modèle",
    "Model Description": "Description Modèle",
    "Device 2 Name": "Nom Appareil 2",
    "Device 2 Type": "Type Appareil 2",
    "Type": "Type",
    # System
    "System Time": "Heure Système",
    "System Uptime": "Uptime Système",
    "System load average": "Charge moyenne système",
    "Available flash storage": "Stockage flash disponible",
    "Flash storage used": "Stockage flash utilisé",
    "Available RAM": "RAM disponible",
    "Detected Battery Number": "Numéro Batterie Détecté",
    "Number of battery cells or modules": "Nombre cellules ou modules batterie",
    # Settings
    "Country grid standard setting": "Paramètre standard réseau pays",
    "Split-phase configuration flag": "Flag configuration split-phase",
    "Commissioning Freeze": "Gel Mise en Service",
    "Dynamic Feed In Ctrl": "Contrôle Injection Dynamique",
    "Energy Policy": "Politique Énergétique",
    "Battery Control Enabled": "Contrôle Batterie Activé",
    "Grid External Control Enabled": "Contrôle Externe Réseau Activé",
    "Model 126 Enabled": "Modèle 126 Activé",
    "Model 132 Enabled": "Modèle 132 Activé",
    "Enabled": "Activé",
    # Counters
    "Battery charge cycles counter": "Compteur cycles charge batterie",
    "Battery discharge cycles counter": "Compteur cycles décharge batterie",
    "Count": "Compte",
    "Channels": "Canaux",
    # WiFi
    "WiFi Mode": "Mode WiFi",
    "WiFi SSID": "SSID WiFi",
    "WiFi Local IP": "IP Local WiFi",
    "WiFi link quality percentage": "Pourcentage qualité lien WiFi",
    "WiFi FSM Status": "État FSM WiFi",
    "WiFi Status": "État WiFi",
    "WiFi AP Status": "État AP WiFi",
    "WiFi DHCP State": "État DHCP WiFi",
    "WiFi IP Address": "Adresse IP WiFi",
    "WiFi Netmask": "Masque Réseau WiFi",
    "WiFi Broadcast": "Broadcast WiFi",
    "WiFi Gateway": "Passerelle WiFi",
    "WiFi DNS Server": "Serveur DNS WiFi",
    # Logger
    "Logger Serial Number": "Numéro de Série Logger",
    "Logger Board Model": "Modèle Carte Logger",
    "Logger Hostname": "Hostname Logger",
    "Logger ID": "ID Logger",
    # Other
    "Communication Protocol": "Protocole Communication",
    "Inverter ID": "ID Onduleur",
    "Inverter Time": "Heure Onduleur",
    "Central controller frequency": "Fréquence contrôleur central",
    "Warning Flags": "Flags Avertissement",
    "Flags": "Flags",
    "Speed": "Vitesse",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Version Fw",
    "Connection": "Connexion",
}


def translate(text: str) -> str:
    """Translate English text to French using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        french = TRANSLATIONS[english]
        result = result.replace(english, french)

    return result


def main():
    """Generate complete French translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, encoding="utf-8") as f:
        en_data = json.load(f)

    # Load current French (to preserve config/options sections which are already good)
    fr_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/fr.json")
    with open(fr_file, encoding="utf-8") as f:
        fr_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data["entity"]["sensor"].items():
        english_name = value["name"]
        french_name = translate(english_name)
        fr_data["entity"]["sensor"][key] = {"name": french_name}

    # Save updated translations
    with open(fr_file, "w", encoding="utf-8") as f:
        json.dump(fr_data, f, ensure_ascii=False, indent=2)

    print("✓ French translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data["entity"]["sensor"].items())[:15]
    for key, value in samples:
        en_name = value["name"]
        fr_name = fr_data["entity"]["sensor"][key]["name"]
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    FR: {fr_name}")


if __name__ == "__main__":
    main()
