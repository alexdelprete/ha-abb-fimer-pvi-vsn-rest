#!/usr/bin/env python3
"""Generate complete Portuguese translations from English source."""

import json
from pathlib import Path

# Complete Portuguese translation mappings
# Preserving technical terms where appropriate (AC, DC, WiFi, MPPT, etc.)

TRANSLATIONS = {
    # Exact phrases (highest priority - complete sensor names)
    "Power AC": "Potência AC",
    "Reactive Power - Grid Connection": "Potência Reativa - Conexão Rede",
    "Frequency AC - Grid": "Frequência AC - Rede",
    "Current AC": "Corrente AC",
    "Power DC": "Potência DC",
    "Voltage DC": "Tensão DC",
    "Voltage AC": "Tensão AC",
    "Current DC": "Corrente DC",
    "DC energy": "Energia DC",
    "Energy AC": "Energia AC",
    "Energy DC": "Energia DC",
    "Energy": "Energia",
    "energy": "energia",
    "Power": "Potência",
    "Voltage": "Tensão",
    "Current": "Corrente",
    "Temperature": "Temperatura",
    "Frequency": "Frequência",
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
    "String 1": "String 1",
    "String 2": "String 2",
    "PV Input": "PV",
    "Input 1": "Entrada 1",
    "Input 2": "Entrada 2",
    "Fan 1": "Ventilador 1",
    "Fan 2": "Ventilador 2",
    # Locations/Device types
    "Cabinet": "Gabinete",
    "Booster": "Booster",
    "Inverter": "Inversor",
    "Meter": "Medidor",
    "House": "Casa",
    "Grid": "Rede",
    "Ground": "Terra",
    "Battery": "Bateria",
    "Heatsink": "Dissipador",
    "Other": "Outro",
    "Shunt": "Shunt",
    "Sensor 1": "Sensor 1",
    "Bus Midpoint": "Ponto Médio Bus",
    "Bulk Capacitor": "Condensador Bulk",
    # States/Status
    "Status": "Estado",
    "State": "Estado",
    "Alarm Status": "Estado Alarme",
    "Alarm State": "Estado Alarme",
    "Global Status": "Estado Global",
    "Inverter Status": "Estado Inversor",
    "Inverter State": "Estado Inversor",
    "Clock State": "Estado Relógio",
    "Digital Input Status": "Estado Entrada Digital",
    "DC Input 1 Status": "Estado Entrada DC 1",
    "DC Input 2 Status": "Estado Entrada DC 2",
    "DC Input 1 State": "Estado Entrada DC 1",
    "DC Input 2 State": "Estado Entrada DC 2",
    "Global operational state": "Estado operacional global",
    "State of Health": "Estado de Saúde",
    "State of Charge": "Estado de Carga",
    "Battery Control State": "Estado Controle Bateria",
    "Grid External Control State": "Estado Controle Externo Rede",
    "Fault Ride Through (FRT) status": "Estado Fault Ride Through (FRT)",
    # Modes
    "Mode": "Modo",
    "Battery Mode": "Modo Bateria",
    "Input Mode": "Modo Entrada",
    "Digital Input 0 Mode": "Modo Entrada Digital 0",
    "Digital Input 1 Mode": "Modo Entrada Digital 1",
    "Stand Alone Mode": "Modo Autónomo",
    # Time periods
    "Lifetime": "Total",
    "Since Restart": "Desde Reinício",
    "Last 7 Days": "Últimos 7 Dias",
    "Last 30 Days": "Últimos 30 Dias",
    "Last Week": "Última Semana",
    "Last Month": "Último Mês",
    "Last Year": "Último Ano",
    "Today": "Hoje",
    # Operations
    "Produced": "Produzida",
    "Absorbed": "Absorvida",
    "Import": "Importação",
    "Export": "Exportação",
    "Backup Output": "Saída Backup",
    "Consumption": "Consumo",
    "Home PV": "PV Casa",
    "from": "de",
    # Battery terms
    "Battery Charge": "Carga Bateria",
    "Battery Discharge": "Descarga Bateria",
    "Battery Total": "Total Bateria",
    "Battery Cycles": "Ciclos Bateria",
    "Battery Cell Max": "Célula Bateria Max",
    "Battery Cell Min": "Célula Bateria Min",
    # Power terms
    "Peak": "Pico",
    "Rating": "Nominal",
    "Power Factor": "Fator de Potência",
    "Apparent": "Aparente",
    "Reactive": "Reativa",
    "AC Power Derating Flags": "Flags Redução Potência AC",
    "Reactive Power Derating": "Redução Potência Reativa",
    "Apparent Power Derating": "Redução Potência Aparente",
    # Energy terms
    "Self-consumed energy": "Energia autoconsumida",
    "Total energy from direct transducer (DT)": "Energia total do transdutor direto (DT)",
    "Total energy from current transformer (CT)": "Energia total do transformador de corrente (CT)",
    # Measurements
    "Leakage DC-AC": "Fuga DC-AC",
    "Leakage DC-DC": "Fuga DC-DC",
    "Leakage": "Fuga",
    "Insulation": "Isolamento",
    "Resistance": "Resistência",
    "Load": "Carga",
    "Input Total": "Total Entrada",
    "House Load Total": "Carga Casa Total",
    # Device info
    "Manufacturer name": "Nome fabricante",
    "Model identifier": "Identificador modelo",
    "Configuration options": "Opções de configuração",
    "Firmware version": "Versão firmware",
    "Firmware Version": "Versão Firmware",
    "Firmware Build Date": "Data Build Firmware",
    "Firmware Build Hash": "Hash Build Firmware",
    "Firmware Revision": "Revisão Firmware",
    "Serial number": "Número de série",
    "Serial Number": "Número de Série",
    "Modbus address": "Endereço Modbus",
    "Product number": "Número produto",
    "Part Number": "Número Peça",
    "Manufacturing Week/Year": "Semana/Ano Produção",
    "Model Type": "Tipo Modelo",
    "Model Description": "Descrição Modelo",
    "Device 2 Name": "Nome Dispositivo 2",
    "Device 2 Type": "Tipo Dispositivo 2",
    "Type": "Tipo",
    # System
    "System Time": "Hora Sistema",
    "System Uptime": "Uptime Sistema",
    "System load average": "Carga média sistema",
    "Available flash storage": "Armazenamento flash disponível",
    "Flash storage used": "Armazenamento flash usado",
    "Available RAM": "RAM disponível",
    "Detected Battery Number": "Número Bateria Detectado",
    "Number of battery cells or modules": "Número células ou módulos bateria",
    # Settings
    "Country grid standard setting": "Configuração padrão rede país",
    "Split-phase configuration flag": "Flag configuração split-phase",
    "Commissioning Freeze": "Congelamento Comissionamento",
    "Dynamic Feed In Ctrl": "Controle Injeção Dinâmica",
    "Energy Policy": "Política Energética",
    "Battery Control Enabled": "Controle Bateria Ativado",
    "Grid External Control Enabled": "Controle Externo Rede Ativado",
    "Model 126 Enabled": "Modelo 126 Ativado",
    "Model 132 Enabled": "Modelo 132 Ativado",
    "Enabled": "Ativado",
    # Counters
    "Battery charge cycles counter": "Contador ciclos carga bateria",
    "Battery discharge cycles counter": "Contador ciclos descarga bateria",
    "Count": "Contagem",
    "Channels": "Canais",
    # WiFi
    "WiFi Mode": "Modo WiFi",
    "WiFi SSID": "SSID WiFi",
    "WiFi Local IP": "IP Local WiFi",
    "WiFi link quality percentage": "Porcentagem qualidade link WiFi",
    "WiFi FSM Status": "Estado FSM WiFi",
    "WiFi Status": "Estado WiFi",
    "WiFi AP Status": "Estado AP WiFi",
    "WiFi DHCP State": "Estado DHCP WiFi",
    "WiFi IP Address": "Endereço IP WiFi",
    "WiFi Netmask": "Máscara de Rede WiFi",
    "WiFi Broadcast": "Broadcast WiFi",
    "WiFi Gateway": "Gateway WiFi",
    "WiFi DNS Server": "Servidor DNS WiFi",
    # Logger
    "Logger Serial Number": "Número de Série Logger",
    "Logger Board Model": "Modelo Placa Logger",
    "Logger Hostname": "Hostname Logger",
    "Logger ID": "ID Logger",
    # Other
    "Communication Protocol": "Protocolo Comunicação",
    "Inverter ID": "ID Inversor",
    "Inverter Time": "Hora Inversor",
    "Central controller frequency": "Frequência controlador central",
    "Warning Flags": "Flags Aviso",
    "Flags": "Flags",
    "Speed": "Velocidade",
    "Max": "Max",
    "Min": "Min",
    "Fw Version": "Versão Fw",
    "Connection": "Conexão",
}


def translate(text: str) -> str:
    """Translate English text to Portuguese using the translation map."""
    result = text

    # Sort by length (longest first) to avoid partial replacements
    for english in sorted(TRANSLATIONS.keys(), key=len, reverse=True):
        portuguese = TRANSLATIONS[english]
        result = result.replace(english, portuguese)

    return result


def main():
    """Generate complete Portuguese translations from English."""

    # Load English translations
    en_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/en.json")
    with open(en_file, encoding="utf-8") as f:
        en_data = json.load(f)

    # Load current Portuguese (to preserve config/options sections which are already good)
    pt_file = Path("custom_components/abb_fimer_pvi_vsn_rest/translations/pt.json")
    with open(pt_file, encoding="utf-8") as f:
        pt_data = json.load(f)

    # Translate all sensors from English
    for key, value in en_data["entity"]["sensor"].items():
        english_name = value["name"]
        portuguese_name = translate(english_name)
        pt_data["entity"]["sensor"][key] = {"name": portuguese_name}

    # Save updated translations
    with open(pt_file, "w", encoding="utf-8") as f:
        json.dump(pt_data, f, ensure_ascii=False, indent=2)

    print("✓ Portuguese translations updated!")
    print(f"  Translated {len(en_data['entity']['sensor'])} sensors")

    # Show sample translations
    print("\nSample translations:")
    samples = list(en_data["entity"]["sensor"].items())[:15]
    for key, value in samples:
        en_name = value["name"]
        pt_name = pt_data["entity"]["sensor"][key]["name"]
        print(f"  {key}:")
        print(f"    EN: {en_name}")
        print(f"    PT: {pt_name}")


if __name__ == "__main__":
    main()
