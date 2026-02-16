"""Tests for integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest import (
    _async_migrate_entity_ids,
    async_remove_config_entry_device,
    async_setup_entry,
    async_unload_entry,
    async_update_device_registry,
)
from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.discovery import (
    DiscoveredDevice,
    DiscoveryResult,
)
from custom_components.abb_fimer_pvi_vsn_rest.const import (
    CONF_PREFIX_DATALOGGER,
    CONF_PREFIX_INVERTER,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "host": "192.168.1.100",
            "username": "guest",
            "password": "",
        }
        entry.options = {
            CONF_SCAN_INTERVAL: 60,
        }
        entry.entry_id = "test_entry_id"
        entry.runtime_data = None
        return entry

    @pytest.fixture
    def mock_discovery_result(self) -> DiscoveryResult:
        """Create mock discovery result."""
        return DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="WIFI LOGGER CARD",
            firmware_version="1.9.2",
            hostname="ABB-077909-3G82-3112.local",
            devices=[
                DiscoveredDevice(
                    device_id="111033-3N16-1421",
                    raw_device_id="a4:06:e9:7f:42:49",
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
                DiscoveredDevice(
                    device_id="077909-3G82-3112",
                    raw_device_id="077909-3G82-3112",
                    device_type="inverter_3phases",
                    device_model="PVI-10.0-OUTD",
                    manufacturer="Power-One",
                    firmware_version="C008",
                    hardware_version=None,
                    is_datalogger=False,
                ),
            ],
            status_data={},
        )

    @pytest.mark.asyncio
    async def test_setup_entry_success(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_discovery_result: DiscoveryResult,
    ) -> None:
        """Test successful setup entry."""
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.vsn_model = "VSN300"
        mock_coordinator.discovery_result = mock_discovery_result

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerPVIVSNRestCoordinator",
                return_value=mock_coordinator,
            ),
            patch("custom_components.abb_fimer_pvi_vsn_rest._async_migrate_entity_ids"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
        ):
            result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        assert mock_config_entry.runtime_data is not None
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_discovery_failure(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test setup entry fails when discovery fails."""
        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                side_effect=Exception("Connection failed"),
            ),
            pytest.raises(ConfigEntryNotReady, match="Discovery failed"),
        ):
            await async_setup_entry(mock_hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_first_refresh_failure(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_discovery_result: DiscoveryResult,
    ) -> None:
        """Test setup entry fails when first refresh fails."""
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=Exception("Fetch failed")
        )

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerPVIVSNRestCoordinator",
                return_value=mock_coordinator,
            ),
            pytest.raises(ConfigEntryNotReady, match="Failed to fetch data"),
        ):
            await async_setup_entry(mock_hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_with_http_prefix(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_discovery_result: DiscoveryResult,
    ) -> None:
        """Test setup entry with http:// prefix in host."""
        mock_config_entry.data["host"] = "http://192.168.1.100"

        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.vsn_model = "VSN300"
        mock_coordinator.discovery_result = mock_discovery_result

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerPVIVSNRestCoordinator",
                return_value=mock_coordinator,
            ),
            patch("custom_components.abb_fimer_pvi_vsn_rest._async_migrate_entity_ids"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
        ):
            result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_setup_entry_logs_startup_once(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_discovery_result: DiscoveryResult,
    ) -> None:
        """Test startup message is logged only once."""
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.vsn_model = "VSN300"
        mock_coordinator.discovery_result = mock_discovery_result

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=mock_discovery_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerPVIVSNRestCoordinator",
                return_value=mock_coordinator,
            ),
            patch("custom_components.abb_fimer_pvi_vsn_rest._async_migrate_entity_ids"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
        ):
            # First call - startup message should be logged
            await async_setup_entry(mock_hass, mock_config_entry)
            assert f"{DOMAIN}_startup_logged" in mock_hass.data

            # Second call - startup message should not be logged again
            await async_setup_entry(mock_hass, mock_config_entry)


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        return hass

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with runtime data."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"

        # Create mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_shutdown = AsyncMock()

        # Create runtime data with coordinator
        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        return entry

    @pytest.mark.asyncio
    async def test_unload_entry_success(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test successful unload entry."""
        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_config_entry.runtime_data.coordinator.async_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_entry_failure(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test unload entry when platform unload fails."""
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is False
        # Shutdown should not be called if unload fails
        mock_config_entry.runtime_data.coordinator.async_shutdown.assert_not_called()


class TestAsyncUpdateDeviceRegistry:
    """Tests for async_update_device_registry function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {"host": "192.168.1.100"}
        entry.options = {}

        # Create mock discovery result
        mock_discovery = MagicMock()
        mock_discovery.logger_sn = "111033-3N16-1421"
        mock_discovery.logger_model = "WIFI LOGGER CARD"
        mock_discovery.firmware_version = "1.9.2"

        # Create mock datalogger DiscoveredDevice
        datalogger_device = DiscoveredDevice(
            device_id="111033-3N16-1421",
            raw_device_id="111033-3N16-1421",
            device_type="datalogger",
            device_model="VSN300",
            manufacturer="ABB",
            firmware_version="1.9.2",
            hardware_version=None,
            is_datalogger=True,
        )

        # Create mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.discovery_result = mock_discovery
        mock_coordinator.vsn_model = "VSN300"
        mock_coordinator.device_id = None
        mock_coordinator.discovered_devices = [datalogger_device]

        # Create runtime data
        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        return entry

    def test_update_device_registry_success(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test successful device registry update with correct metadata."""
        mock_device_registry = MagicMock()
        mock_device = MagicMock()
        mock_device.id = "device_123"
        mock_device_registry.async_get_device.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        mock_device_registry.async_get_or_create.assert_called_once()
        assert mock_config_entry.runtime_data.coordinator.device_id == "device_123"

        # Verify correct manufacturer and device name
        call_kwargs = mock_device_registry.async_get_or_create.call_args
        assert call_kwargs.kwargs["manufacturer"] == "ABB"
        assert call_kwargs.kwargs["model"] == "VSN300"
        assert call_kwargs.kwargs["name"] == "ABB Datalogger VSN300 (111033-3N16-1421)"

    def test_update_device_registry_with_custom_prefix(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device registry uses custom prefix when configured."""
        mock_config_entry.options = {CONF_PREFIX_DATALOGGER: "ABB FIMER Datalogger"}

        mock_device_registry = MagicMock()
        mock_device = MagicMock()
        mock_device.id = "device_456"
        mock_device_registry.async_get_device.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        call_kwargs = mock_device_registry.async_get_or_create.call_args
        assert call_kwargs.kwargs["name"] == "ABB FIMER Datalogger"
        assert call_kwargs.kwargs["manufacturer"] == "ABB"

    def test_update_device_registry_no_logger_sn(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device registry update with no logger serial number."""
        mock_config_entry.runtime_data.coordinator.discovery_result.logger_sn = None

        mock_device_registry = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        # Should not create device if no logger_sn
        mock_device_registry.async_get_or_create.assert_not_called()

    def test_update_device_registry_no_discovery_result(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device registry update with no discovery result."""
        mock_config_entry.runtime_data.coordinator.discovery_result = None

        mock_device_registry = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        # Should not create device if no discovery_result
        mock_device_registry.async_get_or_create.assert_not_called()


class TestAsyncRemoveConfigEntryDevice:
    """Tests for async_remove_config_entry_device function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        return MagicMock(spec=ConfigEntry)

    @pytest.mark.asyncio
    async def test_remove_device_blocked_for_domain(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal is blocked for domain devices."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "111033-3N16-1421")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_device_allowed_for_other_domain(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal is allowed for other domain devices."""
        mock_device = MagicMock()
        mock_device.identifiers = {("other_domain", "device_123")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_device_empty_identifiers(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal with empty identifiers."""
        mock_device = MagicMock()
        mock_device.identifiers = set()

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is True


class TestAsyncMigrateEntityIds:
    """Tests for _async_migrate_entity_ids function."""

    MOCK_TRANSLATIONS_JSON = (
        '{"entity":{"sensor":{'
        '"watts":{"name":"Power AC"},'
        '"alarm_st":{"name":"Alarm Status"},'
        '"serial_number":{"name":"Serial number"}'
        "}}}"
    )

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with runtime data and discovered devices."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.options = {CONF_PREFIX_INVERTER: "ABB FIMER Inverter"}

        # Create discovered device
        inverter_device = DiscoveredDevice(
            device_id="077909-3G82-3112",
            raw_device_id="077909-3G82-3112",
            device_type="inverter_3phases",
            device_model="PVI-10.0-OUTD",
            manufacturer="Power-One",
            firmware_version="C008",
            hardware_version=None,
            is_datalogger=False,
        )

        # Create coordinator mock
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [inverter_device]

        # Create runtime data
        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data

        return entry

    def test_migrate_buggy_point_name_suffix(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entities with buggy point_name suffix get migrated to translated name."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_watts"

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=None)  # Target doesn't exist
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.Path.read_text",
                return_value=self.MOCK_TRANSLATIONS_JSON,
            ),
        ):
            _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_called_once()
        call_args = mock_registry.async_update_entity.call_args
        assert call_args[0][0] == "sensor.abb_fimer_inverter_watts"
        assert call_args[1]["new_entity_id"] == "sensor.abb_fimer_inverter_power_ac"

    def test_migrate_skips_already_translated_suffix(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entities already using translated suffix are skipped."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        # Already has translated suffix
        mock_entity.entity_id = "sensor.abb_fimer_inverter_power_ac"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.Path.read_text",
                return_value=self.MOCK_TRANSLATIONS_JSON,
            ),
        ):
            _async_migrate_entity_ids(mock_hass, mock_config_entry)

        # Should not update because entity_id doesn't end with _watts (point_name)
        mock_registry.async_update_entity.assert_not_called()

    def test_migrate_skips_when_translation_matches_point_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entities where slugified translation equals point_name are skipped."""
        mock_entity = MagicMock()
        # "serial_number" translates to "Serial number" → slugify = "serial_number"
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_serial_number"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_serial_number"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.Path.read_text",
                return_value=self.MOCK_TRANSLATIONS_JSON,
            ),
        ):
            _async_migrate_entity_ids(mock_hass, mock_config_entry)

        # Translation "Serial number" → "serial_number" == point_name → no migration
        mock_registry.async_update_entity.assert_not_called()

    def test_migrate_skips_when_target_exists(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test collision guard: skip if target entity_id already exists."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_watts"

        mock_registry = MagicMock()
        # Target entity_id already exists
        mock_registry.async_get = MagicMock(return_value=MagicMock())
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[mock_entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.Path.read_text",
                return_value=self.MOCK_TRANSLATIONS_JSON,
            ),
        ):
            _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()
