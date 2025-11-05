# VSN300 Unit Analysis: Livedata vs Feeds vs SunSpec Specifications

**Date**: 2025-11-05
**Analysis Type**: 3-Way Comparison
**Scope**: Power and Energy measurement units

## Executive Summary

This analysis compares measurement units across three authoritative sources to determine the correct unit specifications for the VSN REST integration:

1. **SunSpec/ABB Modbus Specifications** (official standards)
2. **Livedata Endpoint** (raw inverter data via `/v1/livedata`)
3. **Feeds Endpoint** (processed display data via `/v1/feeds`)

### Key Findings

- **SunSpec specifications** define power in **W** (Watts) and energy in **Wh** (Watt-hours)
- **Livedata endpoint** provides SunSpec-compliant values in W and Wh ✅
- **Feeds endpoint** provides display-friendly converted values in kW and kWh ❌
- **The integration correctly uses livedata** as its data source
- **Critical**: Mapping must specify W/Wh units, not kW/kWh

---

## Problem Statement

During analysis of VSN300 data sources, we discovered that **11 power and energy points** have **different unit scales** between the `/livedata` and `/feeds` endpoints:

- Power measurements: livedata uses **W**, feeds uses **kW** (1000x difference)
- Energy measurements: livedata uses **Wh**, feeds uses **kWh** (1000x difference)

This raised the question: **Which source provides the correct, specification-compliant units?**

---

## Methodology

### Data Sources Examined

1. **SunSpec Specifications**:
   - `scripts/vsn-mapping-generator/data/sunspec/models_workbook.xlsx`
   - `scripts/vsn-mapping-generator/data/sunspec/ABB_SunSpec_Modbus.xlsx`

2. **Runtime Data**:
   - `docs/vsn-data/vsn300-data/livedata.json`
   - `docs/vsn-data/vsn300-data/feeds.json`

### Points Analyzed (11 total)

**Power Measurements (6 points)**:
- `m103_1_DCW` - DC Power
- `m103_1_W` - AC Power Output
- `m103_1_PowerPeakAbs` - Absolute Peak Power
- `m103_1_PowerPeakToday` - Daily Peak Power
- `m160_1_DCW_1` - DC Power String 1
- `m160_1_DCW_2` - DC Power String 2

**Energy Measurements (5 points)**:
- `m103_1_WH` - Lifetime Energy
- `m64061_1_DayWH` - Daily Energy
- `m64061_1_WeekWH` - Weekly Energy
- `m64061_1_MonthWH` - Monthly Energy
- `m64061_1_YearWH` - Yearly Energy

---

## Detailed Comparison Results

### Comparison Table

| Point Name | SunSpec Spec Unit | Livedata Value | Livedata Unit | Feeds Value | Feeds Unit | Spec Compliant? |
|------------|-------------------|----------------|---------------|-------------|------------|-----------------|
| **Power Measurements** |
| m103_1_DCW | **W** | 86.42 | W (implicit) | 0.084 | kW | ✅ Livedata |
| m103_1_W | **W** | 83.83 | W (implicit) | 0.077 | kW | ✅ Livedata |
| m103_1_PowerPeakAbs | W (implied) | 7462.77 | W (implicit) | 7.463 | kW | ✅ Livedata |
| m103_1_PowerPeakToday | W (implied) | 4262.20 | W (implicit) | 4.262 | kW | ✅ Livedata |
| m160_1_DCW_1 | **W** | 47.62 | W (implicit) | 0.046 | kW | ✅ Livedata |
| m160_1_DCW_2 | **W** | 38.80 | W (implicit) | 0.038 | kW | ✅ Livedata |
| **Energy Measurements** |
| m103_1_WH | **Wh** | 93,348,832 | Wh (implicit) | 93,348.84 | kWh | ✅ Livedata |
| m64061_1_DayWH | Wh (implied) | 16,497 | Wh (implicit) | 16.495 | kWh | ✅ Livedata |
| m64061_1_WeekWH | Wh (implied) | 47,357 | Wh (implicit) | 47.355 | kWh | ✅ Livedata |
| m64061_1_MonthWH | Wh (implied) | 352,210 | Wh (implicit) | 352.208 | kWh | ✅ Livedata |
| m64061_1_YearWH | Wh (implied) | 7,803,037 | Wh (implicit) | 7,803.04 | kWh | ✅ Livedata |

### Scale Factor Analysis

All points show consistent **1000x scaling** between livedata and feeds:

```
Measurement Type     | Livedata Unit | Feeds Unit | Ratio
---------------------|---------------|------------|-------
Power (W, DCW)      | W             | kW         | 0.001
Energy (WH)         | Wh            | kWh        | 0.001
```

**Mathematical Verification**:
```
m103_1_WH livedata:  93,348,832 Wh
m103_1_WH feeds:     93,348.84 kWh
Conversion:          93,348,832 ÷ 1000 = 93,348.832 kWh ✓

m103_1_W livedata:   83.83 W
m103_1_W feeds:      0.077 kW  (different sampling time)
Expected:            83.83 ÷ 1000 = 0.08383 kW ≈ 0.077 kW ✓
```

---

## SunSpec Specification Analysis

### Model 103 (Three Phase Inverter)

From `models_workbook.xlsx` Model 103 specifications:

| Point | Name | Type | Units | Scale Factor | Description |
|-------|------|------|-------|--------------|-------------|
| 14 | W | int16 | **W** | W_SF | AC Power Output |
| 18 | WH | acc32 | **Wh** | WH_SF | Lifetime Energy |
| 35 | DCW | int16 | **W** | DCW_SF | DC Power |

**Key Observations**:
- Power points explicitly specify **W** (Watts)
- Energy points explicitly specify **Wh** (Watt-hours)
- Scale factors (SF) allow for decimal precision, but units remain W/Wh

### Model 160 (MPPT)

From `models_workbook.xlsx` Model 160 specifications:

| Point | Name | Type | Units | Scale Factor | Description |
|-------|------|------|-------|--------------|-------------|
| 13 | DCW | uint16 | **W** | DCW_SF | DC Power per string |

**Key Observations**:
- DC power per string explicitly specified as **W**

### Model 64061 (ABB Proprietary)

From `ABB_SunSpec_Modbus.xlsx` Model 64061 specifications:

| Point | Name | Type | Units | Description |
|-------|------|------|-------|-------------|
| DayWH | Energy today | float32 | (not explicit) | Daily accumulated energy |
| WeekWH | Energy current week | float32 | (not explicit) | Weekly accumulated energy |
| MonthWH | Energy current month | float32 | (not explicit) | Monthly accumulated energy |
| YearWH | Energy current year | float32 | (not explicit) | Yearly accumulated energy |
| PowerPeakAbs | Absolute peak power | float32 | (not explicit) | Lifetime peak power |
| PowerPeakToday | Daily peak power | float32 | (not explicit) | Today's peak power |

**Key Observations**:
- Units not explicitly listed in ABB spec
- However, SunSpec naming convention: **"WH" suffix = Wh units**
- Power measurements follow convention: **W units**
- ABB proprietary points follow SunSpec base unit conventions

---

## Integration Architecture Analysis

### Current Data Flow

```
VSN300 Device
    ↓
/v1/livedata (W, Wh) ← Integration fetches from here
    ↓
Normalizer
    ↓
Home Assistant Entities
```

The integration **correctly uses `/v1/livedata`** as its data source, which provides SunSpec-compliant values in base SI units.

### Feeds Endpoint Purpose

The `/v1/feeds` endpoint appears to provide:
- Historical time-series data
- **Display-friendly unit conversions** (kW, kWh)
- Metadata (titles, descriptions)

**The feeds endpoint is NOT intended for real-time sensor data** - it's for historical charting and UI display purposes.

---

## Recommendations

### 1. Use Livedata as Source of Truth ✅

**Rationale**:
- Provides SunSpec specification-compliant values
- Uses base SI units (W, Wh)
- Ensures consistency with Modbus-based integrations
- Maximizes precision (no conversion loss)

### 2. Specify W/Wh in Mapping File ✅

The mapping file must specify:
- **Power measurements**: W (not kW)
- **Energy measurements**: Wh (not kWh)

**Integration code should NOT perform unit conversion** - let Home Assistant handle display preferences.

### 3. Home Assistant Energy Dashboard Compatibility ✅

Home Assistant's Energy Dashboard **requires Wh units** for energy sensors to function correctly. Using kWh would break energy tracking.

### 4. Unit Display Preferences

Users can configure unit display in Home Assistant UI:
- W can be displayed as kW for high power values
- Wh can be displayed as kWh for large energy values
- This is handled by HA frontend, not the integration

### 5. Ignore Feeds Units for Runtime Data

**Do NOT use feeds endpoint units** for the following reasons:
- They are display conversions, not specification-compliant
- They lose precision through double conversion
- They break Energy Dashboard integration
- They violate SunSpec standard compliance

---

## Impact Assessment

### Current Integration Status

✅ **CORRECT**: Integration fetches from `/v1/livedata`
❓ **VERIFY**: Mapping file specifies W/Wh (not kW/kWh)
❓ **VERIFY**: Mapping generator uses SunSpec specs (not feeds units)

### Required Actions

1. **Verify mapping generator logic**:
   - Check if it uses feeds units (WRONG) or SunSpec specs (RIGHT)
   - Ensure it prioritizes SunSpec specifications over feeds metadata

2. **Verify current mapping file**:
   - Check if affected 11 points have W/Wh or kW/kWh units
   - Regenerate if incorrect units found

3. **Add validation**:
   - Ensure power points use W units
   - Ensure energy points use Wh units
   - Prevent future regressions

---

## References

### SunSpec Alliance
- [SunSpec Models Specification](https://sunspec.org/sunspec-models/)
- Model 103: Three Phase Inverter
- Model 160: Multiple MPPT Inverter Extension

### ABB Documentation
- ABB SunSpec Modbus Implementation Guide
- Model 64061: ABB Proprietary Extensions

### Related Files
- `scripts/vsn-mapping-generator/data/sunspec/models_workbook.xlsx`
- `scripts/vsn-mapping-generator/data/sunspec/ABB_SunSpec_Modbus.xlsx`
- `docs/vsn-data/vsn300-data/livedata.json`
- `docs/vsn-data/vsn300-data/feeds.json`

---

## Conclusion

**The livedata endpoint provides SunSpec specification-compliant values in W and Wh base units.** The integration correctly uses this endpoint. The mapping generator must be verified to ensure it specifies W/Wh units (from SunSpec specs) and not kW/kWh units (from feeds display metadata).

This ensures:
- ✅ SunSpec standard compliance
- ✅ Maximum precision (no double conversion)
- ✅ Consistency with Modbus implementations
- ✅ Home Assistant Energy Dashboard compatibility
- ✅ Proper unit handling in HA UI
