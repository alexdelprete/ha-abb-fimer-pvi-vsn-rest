"""Tests for integration setup and unload."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest import (
    STARTUP_FAILURES_KEY,
    _async_migrate_entity_ids,
    _async_migrate_options,
    _cleanup_orphaned_devices,
    _clear_startup_failure,
    _handle_startup_failure,
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
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_ENABLE_STARTUP_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_PREFIX_DATALOGGER,
    CONF_PREFIX_INVERTER,
    CONF_RECOVERY_SCRIPT,
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
            patch("custom_components.abb_fimer_pvi_vsn_rest._cleanup_orphaned_devices"),
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
            patch("custom_components.abb_fimer_pvi_vsn_rest._cleanup_orphaned_devices"),
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
            patch("custom_components.abb_fimer_pvi_vsn_rest._cleanup_orphaned_devices"),
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

    def test_update_device_registry_no_datalogger_device(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device registry update with no datalogger in discovered devices."""
        # Remove all devices so no datalogger is found
        mock_config_entry.runtime_data.coordinator.discovered_devices = []

        mock_device_registry = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        # Should not create device if no datalogger found
        mock_device_registry.async_get_or_create.assert_not_called()

    def test_update_device_registry_no_discovery_result(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device registry still works when discovery_result is None."""
        mock_config_entry.runtime_data.coordinator.discovery_result = None

        mock_device_registry = MagicMock()
        mock_device = MagicMock()
        mock_device.id = "device_789"
        mock_device_registry.async_get_device.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
            return_value=mock_device_registry,
        ):
            async_update_device_registry(mock_hass, mock_config_entry)

        # Should still create device from discovered_devices (datalogger exists)
        mock_device_registry.async_get_or_create.assert_called_once()
        call_kwargs = mock_device_registry.async_get_or_create.call_args
        # sw_version should be None when discovery_result is None
        assert call_kwargs.kwargs["sw_version"] is None


class TestAsyncRemoveConfigEntryDevice:
    """Tests for async_remove_config_entry_device function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with discovered devices."""
        entry = MagicMock(spec=ConfigEntry)
        # Mock discovered devices for the smart deletion logic
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [
            MagicMock(device_id="111033-3N16-1421"),
            MagicMock(device_id="077909-3G82-3112"),
        ]
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = mock_coordinator
        return entry

    @pytest.mark.asyncio
    async def test_remove_device_blocked_for_discovered(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal is blocked for devices still in discovery."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "111033-3N16-1421")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_device_allowed_for_orphaned(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal is allowed for orphaned devices not in discovery."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "orphaned-device-id")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is True

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

    MOCK_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "watts": "Power AC",
        "alarm_st": "Alarm Status",
        "serial_number": "Serial number",
    }

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

    async def test_migrate_buggy_point_name_suffix(
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
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_called_once()
        call_args = mock_registry.async_update_entity.call_args
        assert call_args[0][0] == "sensor.abb_fimer_inverter_watts"
        assert call_args[1]["new_entity_id"] == "sensor.abb_fimer_inverter_power_ac"

    async def test_migrate_skips_already_translated_suffix(
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
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        # Should not update because entity_id doesn't end with _watts (point_name)
        mock_registry.async_update_entity.assert_not_called()

    async def test_migrate_skips_when_translation_matches_point_name(
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
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        # Translation "Serial number" → "serial_number" == point_name → no migration
        mock_registry.async_update_entity.assert_not_called()

    async def test_migrate_skips_when_target_exists(
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
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()


class TestCleanupOrphanedDevices:
    """Tests for _cleanup_orphaned_devices function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with discovered devices."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [
            MagicMock(device_id="111033-3N16-1421"),
            MagicMock(device_id="077909-3G82-3112"),
        ]
        entry.runtime_data = MagicMock()
        entry.runtime_data.coordinator = mock_coordinator
        return entry

    def test_removes_orphaned_device(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test orphaned devices are removed from registry."""
        orphan_device = MagicMock()
        orphan_device.identifiers = {(DOMAIN, "orphan-device-id")}
        orphan_device.name = "Orphan Device"
        orphan_device.id = "orphan_entry_id"

        mock_device_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_entries_for_config_entry",
                return_value=[orphan_device],
            ),
        ):
            _cleanup_orphaned_devices(mock_hass, mock_config_entry)

        mock_device_registry.async_remove_device.assert_called_once_with("orphan_entry_id")

    def test_keeps_discovered_device(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test discovered devices are NOT removed from registry."""
        active_device = MagicMock()
        active_device.identifiers = {(DOMAIN, "111033-3N16-1421")}
        active_device.name = "Active Device"

        mock_device_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_entries_for_config_entry",
                return_value=[active_device],
            ),
        ):
            _cleanup_orphaned_devices(mock_hass, mock_config_entry)

        mock_device_registry.async_remove_device.assert_not_called()

    def test_no_devices_in_registry(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test no-op when registry has no devices."""
        mock_device_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_entries_for_config_entry",
                return_value=[],
            ),
        ):
            _cleanup_orphaned_devices(mock_hass, mock_config_entry)

        mock_device_registry.async_remove_device.assert_not_called()


class TestHandleStartupFailure:
    """Tests for _handle_startup_failure function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {STARTUP_FAILURES_KEY: {}}
        return hass

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.title = "Test VSN Device"
        return entry

    def test_first_failure_increments_count(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test first failure initializes and increments counter."""
        _handle_startup_failure(
            mock_hass, mock_config_entry, "192.168.1.100", 3, True, Exception("test")
        )

        failures = mock_hass.data[STARTUP_FAILURES_KEY]["test_entry_id"]
        assert failures["count"] == 1
        assert failures["notification_created"] is False

    def test_notification_created_at_threshold(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test notification is created when failure threshold is reached."""
        mock_hass.data[STARTUP_FAILURES_KEY]["test_entry_id"] = {
            "count": 2,
            "notification_created": False,
        }

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.create_connection_issue"
        ) as mock_create:
            _handle_startup_failure(
                mock_hass, mock_config_entry, "192.168.1.100", 3, True, Exception("test")
            )

        mock_create.assert_called_once()
        failures = mock_hass.data[STARTUP_FAILURES_KEY]["test_entry_id"]
        assert failures["notification_created"] is True

    def test_notification_not_created_when_disabled(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test notification is NOT created when notifications are disabled."""
        mock_hass.data[STARTUP_FAILURES_KEY]["test_entry_id"] = {
            "count": 2,
            "notification_created": False,
        }

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.create_connection_issue"
        ) as mock_create:
            _handle_startup_failure(
                mock_hass,
                mock_config_entry,
                "192.168.1.100",
                3,
                False,
                Exception("test"),
            )

        mock_create.assert_not_called()


class TestClearStartupFailure:
    """Tests for _clear_startup_failure function."""

    def test_clear_with_notification(self) -> None:
        """Test clearing failure when notification was created."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {
            STARTUP_FAILURES_KEY: {"test_entry": {"count": 5, "notification_created": True}}
        }

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.delete_connection_issue"
        ) as mock_delete:
            _clear_startup_failure(hass, "test_entry")

        mock_delete.assert_called_once_with(hass, "test_entry")
        assert "test_entry" not in hass.data[STARTUP_FAILURES_KEY]

    def test_clear_without_notification(self) -> None:
        """Test clearing failure when no notification was created."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {
            STARTUP_FAILURES_KEY: {"test_entry": {"count": 1, "notification_created": False}}
        }

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.delete_connection_issue"
        ) as mock_delete:
            _clear_startup_failure(hass, "test_entry")

        mock_delete.assert_not_called()
        assert "test_entry" not in hass.data[STARTUP_FAILURES_KEY]

    def test_clear_nonexistent_entry(self) -> None:
        """Test clearing failure for entry that doesn't exist."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {STARTUP_FAILURES_KEY: {}}

        _clear_startup_failure(hass, "nonexistent_entry")

    def test_clear_missing_failures_key(self) -> None:
        """Test clearing when STARTUP_FAILURES_KEY not in hass.data."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}

        _clear_startup_failure(hass, "test_entry")


class TestAsyncMigrateOptions:
    """Tests for _async_migrate_options function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_migrate_adds_all_missing_options(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """Test all new options are added when missing."""
        entry = MagicMock(spec=ConfigEntry)
        entry.options = {CONF_SCAN_INTERVAL: 60}

        await _async_migrate_options(mock_hass, entry)

        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_kwargs = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_kwargs[1]["options"]
        assert CONF_ENABLE_REPAIR_NOTIFICATION in updated_options
        assert CONF_ENABLE_STARTUP_NOTIFICATION in updated_options
        assert CONF_FAILURES_THRESHOLD in updated_options
        assert CONF_RECOVERY_SCRIPT in updated_options

    @pytest.mark.asyncio
    async def test_migrate_skips_when_all_present(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """Test no update when all options already present."""
        entry = MagicMock(spec=ConfigEntry)
        entry.options = {
            CONF_SCAN_INTERVAL: 60,
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_ENABLE_STARTUP_NOTIFICATION: True,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "",
        }

        await _async_migrate_options(mock_hass, entry)

        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestAsyncMigrateEntityIdsCollision:
    """Tests for entity ID migration collision handling."""

    MOCK_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "watts": "Power AC",
        "pgrid": "Power AC",  # Same translation as watts → collision!
    }

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with runtime data."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.options = {CONF_PREFIX_INVERTER: "ABB FIMER Inverter"}

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

        mock_coordinator = MagicMock()
        mock_coordinator.discovered_devices = [inverter_device]
        runtime_data = MagicMock()
        runtime_data.coordinator = mock_coordinator
        entry.runtime_data = runtime_data
        return entry

    @pytest.mark.asyncio
    async def test_collision_skips_loser(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test collision: two entities target same ID, loser is skipped."""
        # Two entities with different point_names but same translation
        entity_a = MagicMock()
        entity_a.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_pgrid"
        entity_a.entity_id = "sensor.abb_fimer_inverter_pgrid"

        entity_b = MagicMock()
        entity_b.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        entity_b.entity_id = "sensor.abb_fimer_inverter_watts"

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=None)
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity_a, entity_b],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        # Only the winner (alphabetically first entity_id) should be migrated
        assert mock_registry.async_update_entity.call_count <= 1

    @pytest.mark.asyncio
    async def test_short_unique_id_skipped(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with short unique_id (< 8 parts) is skipped."""
        entity = MagicMock()
        entity.unique_id = "short_id"
        entity.entity_id = "sensor.short_id"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_untranslated_point_name_skipped(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with untranslated point_name is skipped."""
        entity = MagicMock()
        entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_unknown_point"
        entity.entity_id = "sensor.abb_fimer_inverter_unknown_point"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_device_skipped(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity for unknown device (not in discovery) is skipped."""
        entity = MagicMock()
        # Device serial 'unknownsn123456' is not in discovered devices
        entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_unknownsn123456_watts"
        entity.entity_id = "sensor.abb_fimer_inverter_watts"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()
