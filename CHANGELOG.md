# Changelog

## [Unreleased]

### Added
- VSN-SunSpec point mapping (259 mappings) in JSON format
- Mapping conversion script (`scripts/generate_mapping_json.py`)
- Data normalization in `vsn_client.py` standalone test script
- Normalization loads mapping from GitHub URL on-demand
- Comprehensive documentation for mapping format and normalization
- `docs/DEV_NOTES.md` - Development progress tracking
- `docs/MAPPING_FORMAT.md` - Mapping workflow documentation

### Changed
- `vsn_client.py` now performs 5 tests (added normalization)
- `vsn_client.py` creates up to 4 output files (added normalized JSON)
- Updated `VSN_CLIENT_README.md` with normalization documentation

### Technical
- Mapping format: Dual Excel/JSON workflow (Excel for editing, JSON for runtime)
- Normalization adds HA entity metadata (units, labels, device_class, state_class)
- Graceful degradation when mapping unavailable (requires internet)

## [1.0.0-beta.1] - 2025-10-26

### Added
- Initial beta release
- VSN300/VSN700 REST API client implementation
- HTTP Digest authentication for VSN300
- HTTP Basic authentication for VSN700
- Automatic device detection
- Support for `/v1/status`, `/v1/livedata`, and `/v1/feeds` endpoints
- Standalone `vsn_client.py` test script
- Comprehensive test coverage on real VSN300 device
