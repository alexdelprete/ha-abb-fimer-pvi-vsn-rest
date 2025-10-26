# SunSpec Models

This directory contains SunSpec model JSON definitions from <https://github.com/sunspec/models>

These models are used to normalize VSN REST API data to SunSpec schema.

## Contents

### JSON Models (`json/` directory)

- model_1.json - Common Model
- model_101.json - Inverter (Single Phase)
- model_103.json - Inverter (Three Phase)
- model_120.json - Nameplate Ratings
- model_124.json - Basic Storage Controls
- model_160.json - Multiple MPPT Inverter Extension
- model_201.json - Meter (Single Phase)
- model_203.json - Meter (Three Phase)
- model_204.json - Meter (Three Phase WYE)
- model_802.json - Lithium-Ion Battery Bank Model
- model_803.json - Lithium-Ion Battery String Model
- model_804.json - Lithium-Ion Battery Module Model

### Metadata Files

- **NOTICE** - Apache 2.0 license attribution
- **NAMESPACE** - Upstream source, git ref, and download timestamp

## License

These model definitions are copyright SunSpec Alliance and licensed under Apache License 2.0.
See NOTICE file for details.

## Updating Models

To update to a newer version from upstream:

```bash
# Clone the models repo
git clone https://github.com/sunspec/models.git /tmp/sunspec-models

# Copy required models
cd /tmp/sunspec-models/json
cp model_*.json /path/to/this/directory/json/

# Update NAMESPACE file with new git ref and date
git log -1 --format="%H %ci" > ../NAMESPACE.info

# Clean up
rm -rf /tmp/sunspec-models
```
