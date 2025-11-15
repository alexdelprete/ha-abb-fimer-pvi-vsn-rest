#!/usr/bin/env python3
"""Generate complete Spanish translations from English source."""

import json
from pathlib import Path

# Complete Spanish translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Potencia AC",
    "Reactive Power - Grid Connection": "Potencia Reactiva - Conexión Red",
    "Frequency AC - Grid": "Frecuencia AC - Red",
    "Current AC": "Corriente AC",
    "Power DC": "Potencia DC",
    "Voltage DC": "Tensión DC",
    "Voltage AC": "Tensión AC",
    "Current DC": "Corriente DC",
    "DC energy": "Energía DC",
    "Energy AC": "Energía AC",
    "Energy DC": "Energía DC",
    "Energy": "Energía",
    "energy": "energía",
    "Power": "Potencia",
    "Voltage": "Tensión",
    "Current": "Corriente",
    "Temperature": "Temperatura",
    "Frequency": "Frecuencia",

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
    "String 1": "Cadena 1",
    "String 2": "Cadena 2",
    "PV Input": "PV",
    "Input 1": "Entrada 1",
    "Input 2": "Entrada 2",
    "Fan 1": "Ventilador 1",
    "Fan 2": "Ventilador 2",

    # Locations/Device types
    "Cabinet": "Gabinete",
    "Booster": "Booster",
    "Inverter": "Inversor",
    "Meter": "Contador",
    "House": "Casa",
    "Grid": "Red",
    "Ground": "Tierra",
    "Battery": "Batería",
    "Heatsink": "Disipador",
    "Other": "Otro",
    "Shunt": "Shunt",
    "Sensor 1": "Sensor 1",
    "Bus Midpoint": "Punto Medio Bus",
    "Bulk Capacitor": "Condensador Bulk",

    # States/Status
    "Status": "Estado",
    "State": "Estado",
    "Alarm Status": "Estado Alarma",
    "Alarm State": "Estado Alarma",
    "Global Status": "Estado Global",
    "Inverter Status": "Estado Inversor",
    "Inverter State": "Estado Inversor",
    "Clock State": "Estado Reloj",
    "Digital Input Status": "Estado Entrada Digital",
    "DC Input 1 Status": "Estado Entrada DC 1",
    "DC Input 2 Status": "Estado Entrada DC 2",
    "DC Input 1 State": "Estado Entrada DC 1",
    "DC Input 2 State": "Estado Entrada DC 2",
    "Global operational state": "Estado operativo global",
    "State of Health": "Estado de Salud",
    "State of Charge": "Estado de Carga",
    "Battery Control State": "Estado Control Batería",
    "Grid External Control State": "Estado Control Externo Red",
    "Fault Ride Through (FRT) status": "Estado Fault Ride Through (FRT)",

    # Modes
    "Mode": "Modo",
    "Battery Mode": "Modo Batería",
    "Input Mode": "Modo Entrada",
    "Digital Input 0 Mode": "Modo Entrada Digital 0",
    "Digital Input 1 Mode": "Modo Entrada Digital 1",
    "Stand Alone Mode": "Modo Autónomo",

    # Time periods
    "Lifetime": "Total",
    "Since Restart": "Desde Reinicio",
    "Last 7 Days": "Últimos 7 Días",
    "Last 30 Days": "Últimos 30 Días",
    "Last Week": "Última Semana",
    "Last Month": "Último Mes",
    "Last Year": "Último Año",
    "Today": "Hoy",

    # Operations
    "Produced": "Producida",
    "Absorbed": "Absorbida",
    "Import": "Importación",
    "Export": "Exportación",
    "Backup Output": "Salida Respaldo",
    "Consumption": "Consumo",
    "Home PV": "PV Casa",
    "from": "desde",

    # Battery terms
    "Battery Charge": "Carga Batería",
    "Battery Discharge": "Descarga Batería",
    "Battery Total": "Total Batería",
    "Battery Cycles": "Ciclos Batería",
    "Battery Cell Max": "Celda Batería Max",
    "Battery Cell Min": "Celda Batería Min",

    # Power terms
    "Peak": "Pico",
    "Rating": "Nominal",
    "Power Factor": "Factor de Potencia",
    "Apparent": "Aparente",
    "Reactive": "Reactiva",
    "AC Power Derating Flags": "Flags Reducción Potencia AC",
    "Reactive Power Derating": "Reducción Potencia Reactiva",
    "Apparent Power Derating": "Reducción Potencia Aparente",

    # Energy terms
    "Self-consumed energy": "Energía autoconsumida",
    "Total energy from direct transducer (DT)": "Energía total de transductor directo (DT)",
    "Total energy from current transformer (CT)": "Energía total de transformador de corriente (CT)",

    # Measurements
    "Leakage DC-AC": "Fuga DC-AC",
    "Leakage DC-DC": "Fuga DC-DC",
    "Leakage": "Fuga",
    "Insulation": "Aislamiento",
    "Resistance": "Resistencia",
    "Load": "Carga",
    "Input Total": "Total Entrada",
    "House Load Total": "Carga Casa Total",

    # Device info
    "Manufacturer name": "Nombre fabricante",
    "Model identifier": "Identificador modelo",
    "Configuration options": "Opciones de configuración",
    "Firmware version": "Versión firmware",
    "Firmware Version": "Versión Firmware",
    "Firmware Build Date": "Fecha Build Firmware",
    "Firmware Build Hash": "Hash Build Firmware",
    "Firmware Revision": "Revisión Firmware",
    "Serial number": "Número de serie",
    "Serial Number": "Número de Serie",
    "Modbus address": "Dirección Modbus",
    "Product number": "Número producto",
    "Part Number": "Número Pieza",
    "Manufacturing Week/Year": "Semana/Año Producción",
    "Model Type": "Tipo Modelo",
    "Model Description": "Descripción Modelo",
    "Device 2 Name": "Nombre Dispositivo 2",
    "Device 2 Type": "Tipo Dispositivo 2",
    "Type": "Tipo",

    # System
    "System Time": "Hora Sistema",
    "System Uptime": "Uptime Sistema",
    "System load average": "Carga promedio sistema",
    "Available flash storage": "Almacenamiento flash disponible",
    "Flash storage used": "Almacenamiento flash usado",
    "Available RAM": "RAM disponible",
    "Detected Battery Number": "Número Batería Detectado",
    "Number of battery cells or modules": "Número celdas o módulos batería",

    # Settings
    "Country grid standard setting": "Configuración estándar red país",
    "Split-phase configuration flag": "Flag configuración split-phase",
    "Commissioning Freeze": "Congelación Puesta en Marcha",
    "Dynamic Feed In Ctrl": "Control Inyección Dinámica",
    "Energy Policy": "Política Energética",
    "Battery Control Enabled": "Control Batería Habilitado",
    "Grid External Control Enabled": "Control Externo Red Habilitado",
    "Model 126 Enabled": "Modelo 126 Habilitado",
    "Model 132 Enabled": "Modelo 132 Habilitado",
    "Enabled": "Habilitado",

    # Counters
    "Battery charge cycles counter": "Contador ciclos carga batería",
    "Battery discharge cycles counter": "Contador ciclos descarga batería",
    "Count": "Cuenta",
    "Channels": "Canales",

    # WiFi
    "WiFi Mode": "Modo WiFi",
    "WiFi SSID": "SSID WiFi",
    "WiFi Local IP": "IP Local WiFi",
    "WiFi link quality percentage": "Porcentaje calidad enlace WiFi",
    "WiFi FSM Status": "Estado FSM WiFi",
    "WiFi Status": "Estado WiFi",
    "WiFi AP Status": "Estado AP WiFi",
    "WiFi DHCP State": "Estado DHCP WiFi",
    "WiFi IP Address": "Dirección IP WiFi",
    "WiFi Netmask": "Máscara de Red WiFi",
    "WiFi Broadcast": "Broadcast WiFi",
    "WiFi Gateway": "Puerta de Enlace WiFi",
    "WiFi DNS Server": "Servidor DNS WiFi",

    # Logger
    "Logger Serial Number": "Número de Serie Logger",
    "Logger Board Model": "Modelo Placa Logger",
    "Logger Hostname": "Hostname Logger",
    "Logger ID": "ID Logger",

    # Other
    "Communication Protocol": "Protocolo Comunicación",
    "Inverter ID": "ID Inversor",
    "Inverter Time": "Hora Inversor",
    "Central controller frequency": "Frecuencia controlador central",
    "Warning Flags": "Flags Advertencia",
    "Flags": "Flags",
    "Speed": "Velocidad",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Versión Fw",
    "Connection": "Conexión",
}

def translate(text: str) -> str:
    """Translate English text to Spanish using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        spanish = TRANSLATIONS[english]
        result = result.replace(english, spanish)

    return result

def main():
    """Generate complete Spanish translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Load current Spanish (to preserve config/options sections which are already good)
    es_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/es.json")
    with open(es_file, 'r', encoding='utf-8') as f:
        es_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data['entity']['sensor'].items():
        english_name = value['name']
        spanish_name = translate(english_name)
        es_data['entity']['sensor'][key] = {"name": spanish_name}

    # Save updated translations
    with open(es_file, 'w', encoding='utf-8') as f:
        json.dump(es_data, f, ensure_ascii=False, indent=2)

    print("✓ Spanish translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data['entity']['sensor'].items())[:15]
    for key, value in samples:
        en_name = value['name']
        es_name = es_data['entity']['sensor'][key]['name']
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    ES: {es_name}")

if __name__ == "__main__":
    main()
