"""Tests for integration setup and unload."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest import (
    STARTUP_FAILURES_KEY,
    _async_clear_stale_object_id_base_v6,
    _async_clear_stale_suggested_object_ids_v5,
    _async_fix_object_id_base_v7,
    _async_fix_original_names_v4,
    _async_migrate_entity_ids_v2,
    _async_migrate_options,
    _async_populate_known_devices_v8,
    _clear_startup_failure,
    _detect_missing_devices,
    _handle_startup_failure,
    _sync_known_devices,
    async_migrate_entry,
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
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.delete_partial_discovery_issue"),
        ):
            result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        assert mock_config_entry.runtime_data is not None
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_partial_discovery(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test setup entry creates repair issue when devices are missing."""
        # Config has known inverter, but discovery only finds datalogger
        mock_config_entry.data["known_devices"] = [
            {"device_id": "111033-3N16-1421", "device_type": "datalogger", "is_datalogger": True},
            {
                "device_id": "077909-3G82-3112",
                "device_type": "inverter_3phases",
                "is_datalogger": False,
            },
        ]

        # Discovery returns only datalogger
        partial_result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="111033-3N16-1421",
                    raw_device_id="111033-3N16-1421",
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
            ],
            status_data={},
        )

        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.vsn_model = "VSN300"
        mock_coordinator.discovery_result = partial_result

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.discover_vsn_device",
                new_callable=AsyncMock,
                return_value=partial_result,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerVSNRestClient",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.ABBFimerPVIVSNRestCoordinator",
                return_value=mock_coordinator,
            ),
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.create_partial_discovery_issue",
            ) as mock_create_issue,
        ):
            result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_create_issue.assert_called_once()

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
            patch("custom_components.abb_fimer_pvi_vsn_rest.delete_partial_discovery_issue"),
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
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.delete_partial_discovery_issue"),
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
            patch("custom_components.abb_fimer_pvi_vsn_rest.async_update_device_registry"),
            patch("custom_components.abb_fimer_pvi_vsn_rest.delete_partial_discovery_issue"),
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
        """Create mock config entry with known devices."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "known_devices": [
                {
                    "device_id": "111033-3N16-1421",
                    "device_type": "datalogger",
                    "is_datalogger": True,
                },
                {
                    "device_id": "077909-3G82-3112",
                    "device_type": "inverter_3phases",
                    "is_datalogger": False,
                },
            ],
        }
        entry.runtime_data = MagicMock()
        return entry

    @pytest.mark.asyncio
    async def test_remove_device_always_allowed(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal is always allowed (even for known devices)."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "077909-3G82-3112")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_device_syncs_known_devices(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal updates known_devices in config_entry.data."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "077909-3G82-3112")}

        await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        # Verify config entry was updated with device removed from known_devices
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_args = mock_hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        known = new_data.get("known_devices", [])
        assert len(known) == 1
        assert known[0]["device_id"] == "111033-3N16-1421"

    @pytest.mark.asyncio
    async def test_remove_device_other_domain(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device removal with other domain identifiers."""
        mock_device = MagicMock()
        mock_device.identifiers = {("other_domain", "device_123")}

        result = await async_remove_config_entry_device(mock_hass, mock_config_entry, mock_device)

        assert result is True
        # known_devices should not be updated
        mock_hass.config_entries.async_update_entry.assert_not_called()

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


class TestAsyncMigrateEntityIdsV2:
    """Tests for _async_migrate_entity_ids_v2 function."""

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
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.version = 1
        return entry

    @pytest.fixture
    def mock_device_entry(self) -> MagicMock:
        """Create mock device registry entry."""
        device = MagicMock()
        device.name = "ABB FIMER Inverter"
        return device

    async def test_migrate_entity_id_to_translated_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_device_entry: MagicMock,
    ) -> None:
        """Test entities get migrated to use translated display name suffix."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_watts"
        mock_entity.device_id = "device_123"

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=None)  # Target doesn't exist
        mock_registry.async_update_entity = MagicMock()

        mock_device_registry = MagicMock()
        mock_device_registry.async_get = MagicMock(return_value=mock_device_entry)

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_called_once()
        call_args = mock_registry.async_update_entity.call_args
        assert call_args[0][0] == "sensor.abb_fimer_inverter_watts"
        assert call_args[1]["new_entity_id"] == "sensor.abb_fimer_inverter_power_ac"

    async def test_migrate_skips_already_translated_suffix(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_device_entry: MagicMock,
    ) -> None:
        """Test entities already using translated suffix are skipped."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_power_ac"
        mock_entity.device_id = "device_123"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = mock_device_entry

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    async def test_migrate_skips_when_translation_matches_point_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_device_entry: MagicMock,
    ) -> None:
        """Test entities where slugified translation equals point_name are skipped."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_serial_number"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_serial_number"
        mock_entity.device_id = "device_123"

        mock_registry = MagicMock()
        mock_registry.async_update_entity = MagicMock()

        mock_device_registry = MagicMock()
        mock_device_registry.async_get = MagicMock(return_value=mock_device_entry)

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    async def test_migrate_skips_when_target_exists(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_device_entry: MagicMock,
    ) -> None:
        """Test collision guard: skip if target entity_id already exists."""
        mock_entity = MagicMock()
        mock_entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        mock_entity.entity_id = "sensor.abb_fimer_inverter_watts"
        mock_entity.device_id = "device_123"

        mock_registry = MagicMock()
        mock_registry.async_get = MagicMock(return_value=MagicMock())  # Target exists
        mock_registry.async_update_entity = MagicMock()

        mock_device_registry = MagicMock()
        mock_device_registry.async_get = MagicMock(return_value=mock_device_entry)

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()


class TestPopulateKnownDevicesV8:
    """Tests for _async_populate_known_devices_v8 migration function."""

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
        return entry

    def test_populates_known_devices_from_registry(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test known_devices is populated from device registry."""
        datalogger = MagicMock()
        datalogger.identifiers = {(DOMAIN, "1110333n161421")}
        datalogger.model = "VSN300"

        inverter = MagicMock()
        inverter.identifiers = {(DOMAIN, "0779093g823112")}
        inverter.model = "PVI-10.0-OUTD"

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_entries_for_config_entry",
                return_value=[datalogger, inverter],
            ),
        ):
            _async_populate_known_devices_v8(mock_hass, mock_config_entry)

        # Verify config entry was updated with known devices
        call_args = mock_hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        known = new_data.get("known_devices", [])
        assert len(known) == 2
        assert known[0]["device_id"] == "1110333n161421"
        assert known[0]["is_datalogger"] is True
        assert known[1]["device_id"] == "0779093g823112"
        assert known[1]["is_datalogger"] is False


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


class TestAsyncMigrateEntityIdsV2Collision:
    """Tests for entity ID migration v2 collision handling."""

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
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.version = 1
        return entry

    @pytest.fixture
    def mock_device_entry(self) -> MagicMock:
        """Create mock device registry entry."""
        device = MagicMock()
        device.name = "ABB FIMER Inverter"
        return device

    @pytest.mark.asyncio
    async def test_collision_second_entity_skipped(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_device_entry: MagicMock,
    ) -> None:
        """Test collision: first entity wins, second is skipped because target exists."""
        entity_a = MagicMock()
        entity_a.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_pgrid"
        entity_a.entity_id = "sensor.abb_fimer_inverter_pgrid"
        entity_a.device_id = "device_123"

        entity_b = MagicMock()
        entity_b.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        entity_b.entity_id = "sensor.abb_fimer_inverter_watts"
        entity_b.device_id = "device_123"

        mock_registry = MagicMock()
        # First call returns None (target free), subsequent calls return existing entity
        mock_registry.async_get = MagicMock(side_effect=[None, MagicMock()])
        mock_registry.async_update_entity = MagicMock()

        mock_device_registry = MagicMock()
        mock_device_registry.async_get = MagicMock(return_value=mock_device_entry)

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=mock_device_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        # Only the first entity should be migrated
        assert mock_registry.async_update_entity.call_count == 1

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
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

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
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_without_device_skipped(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity without device_id is skipped."""
        entity = MagicMock()
        entity.unique_id = "abb_fimer_pvi_vsn_rest_inverter_0779093g823112_watts"
        entity.entity_id = "sensor.abb_fimer_inverter_watts"
        entity.device_id = None

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
                "custom_components.abb_fimer_pvi_vsn_rest.dr.async_get",
                return_value=MagicMock(),
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.async_get_entity_translations",
                new_callable=AsyncMock,
                return_value=self.MOCK_TRANSLATIONS,
            ),
        ):
            await _async_migrate_entity_ids_v2(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()


class TestAsyncFixOriginalNamesV4:
    """Tests for _async_fix_original_names_v4 function."""

    MOCK_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "pn": "Product Number",
        "sn": "Serial Number",
        "watts": "Power AC",
    }

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.mark.asyncio
    async def test_fixes_stale_original_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test stale original_name is updated to match current translation."""
        entity = MagicMock()
        entity.unique_id = "abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_pn"
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.original_name = "Device - Product Number"

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
            await _async_fix_original_names_v4(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_called_once_with(
            "sensor.abb_fimer_datalogger_product_number",
            original_name="Product Number",
        )

    @pytest.mark.asyncio
    async def test_skips_already_correct_original_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with correct original_name is not updated."""
        entity = MagicMock()
        entity.unique_id = "abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_pn"
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.original_name = "Product Number"

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
            await _async_fix_original_names_v4(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_none_original_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with None original_name is not updated."""
        entity = MagicMock()
        entity.unique_id = "abb_fimer_pvi_vsn_rest_datalogger_1110333n161421_pn"
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.original_name = None

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
            await _async_fix_original_names_v4(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_short_unique_id(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with short unique_id (< 8 parts) is skipped."""
        entity = MagicMock()
        entity.unique_id = "short_id"
        entity.entity_id = "sensor.short_id"
        entity.original_name = "Old Name"

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
            await _async_fix_original_names_v4(mock_hass, mock_config_entry)

        mock_registry.async_update_entity.assert_not_called()


class TestAsyncClearStaleSuggestedObjectIdsV5:
    """Tests for _async_clear_stale_suggested_object_ids_v5 function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        return entry

    def test_clears_stale_suggested_object_id(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test stale suggested_object_id is cleared."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.suggested_object_id = "ABB FIMER Datalogger Device - Product Number"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_clear_stale_suggested_object_ids_v5(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_called_once_with(
            "sensor.abb_fimer_datalogger_product_number",
            suggested_object_id=None,
        )

    def test_skips_none_suggested_object_id(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with None suggested_object_id is skipped."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.suggested_object_id = None

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_clear_stale_suggested_object_ids_v5(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_not_called()

    def test_handles_value_error(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test ValueError during update is handled gracefully."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.suggested_object_id = "stale value"

        mock_registry = MagicMock()
        mock_registry._async_update_entity.side_effect = ValueError("test error")

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            # Should not raise
            _async_clear_stale_suggested_object_ids_v5(mock_hass, mock_config_entry)

    def test_clears_multiple_entities(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test multiple entities with stale suggested_object_id are all cleared."""
        entity1 = MagicMock()
        entity1.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity1.suggested_object_id = "stale value 1"

        entity2 = MagicMock()
        entity2.entity_id = "sensor.abb_fimer_datalogger_uptime"
        entity2.suggested_object_id = "stale value 2"

        entity3 = MagicMock()
        entity3.entity_id = "sensor.abb_fimer_datalogger_firmware"
        entity3.suggested_object_id = None  # Should be skipped

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity1, entity2, entity3],
            ),
        ):
            _async_clear_stale_suggested_object_ids_v5(mock_hass, mock_config_entry)

        assert mock_registry._async_update_entity.call_count == 2


class TestAsyncClearStaleObjectIdBaseV6:
    """Tests for _async_clear_stale_object_id_base_v6 function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        return entry

    def test_clears_stale_object_id_base(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test stale object_id_base is cleared when it differs from original_name."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.object_id_base = "Device - Product Number"
        entity.original_name = "Product Number"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_clear_stale_object_id_base_v6(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_called_once_with(
            "sensor.abb_fimer_datalogger_product_number",
            object_id_base=None,
        )

    def test_skips_matching_object_id_base(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity where object_id_base matches original_name is skipped."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.object_id_base = "Product Number"
        entity.original_name = "Product Number"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_clear_stale_object_id_base_v6(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_not_called()

    def test_skips_none_object_id_base(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with None object_id_base is skipped."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.object_id_base = None
        entity.original_name = "Product Number"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_clear_stale_object_id_base_v6(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_not_called()

    def test_clears_multiple_stale_entities(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test multiple stale entities are cleared, matching ones skipped."""
        entity1 = MagicMock()
        entity1.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity1.object_id_base = "Device - Product Number"
        entity1.original_name = "Product Number"

        entity2 = MagicMock()
        entity2.entity_id = "sensor.abb_fimer_datalogger_uptime"
        entity2.object_id_base = "System - Uptime"
        entity2.original_name = "Uptime"

        entity3 = MagicMock()
        entity3.entity_id = "sensor.abb_fimer_datalogger_firmware"
        entity3.object_id_base = "Firmware Version"
        entity3.original_name = "Firmware Version"  # Already matches

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity1, entity2, entity3],
            ),
        ):
            _async_clear_stale_object_id_base_v6(mock_hass, mock_config_entry)

        assert mock_registry._async_update_entity.call_count == 2


class TestAsyncFixObjectIdBaseV7:
    """Tests for _async_fix_object_id_base_v7 function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        return entry

    def test_sets_object_id_base_from_original_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test None object_id_base is set to original_name."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_product_number"
        entity.object_id_base = None
        entity.original_name = "Product Number"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_fix_object_id_base_v7(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_called_once_with(
            "sensor.abb_fimer_datalogger_product_number",
            object_id_base="Product Number",
        )

    def test_skips_non_none_object_id_base(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with existing object_id_base is skipped."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_power_ac"
        entity.object_id_base = "Power AC"
        entity.original_name = "Power AC"

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_fix_object_id_base_v7(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_not_called()

    def test_skips_empty_original_name(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test entity with no original_name is skipped."""
        entity = MagicMock()
        entity.entity_id = "sensor.abb_fimer_datalogger_something"
        entity.object_id_base = None
        entity.original_name = None

        mock_registry = MagicMock()

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_get",
                return_value=mock_registry,
            ),
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest.er.async_entries_for_config_entry",
                return_value=[entity],
            ),
        ):
            _async_fix_object_id_base_v7(mock_hass, mock_config_entry)

        mock_registry._async_update_entity.assert_not_called()


class TestAsyncMigrateEntry:
    """Tests for async_migrate_entry function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_migrate_version_1_to_8(self, mock_hass: MagicMock) -> None:
        """Test config entry migration from version 1 to 8 (runs all migrations)."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 1
        entry.entry_id = "test_entry_id"

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_migrate_entity_ids_v2",
                new_callable=AsyncMock,
            ) as mock_v2,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_fix_original_names_v4",
                new_callable=AsyncMock,
            ) as mock_v4,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_clear_stale_suggested_object_ids_v5",
            ) as mock_v5,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_clear_stale_object_id_base_v6",
            ) as mock_v6,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_fix_object_id_base_v7",
            ) as mock_v7,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_populate_known_devices_v8",
            ) as mock_v8,
        ):
            result = await async_migrate_entry(mock_hass, entry)

        assert result is True
        mock_v2.assert_called_once()
        mock_v4.assert_called_once()
        mock_v5.assert_called_once()
        mock_v6.assert_called_once()
        mock_v7.assert_called_once()
        mock_v8.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_version_7_to_8(self, mock_hass: MagicMock) -> None:
        """Test config entry migration from version 7 to 8 (only v8 migration)."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 7
        entry.entry_id = "test_entry_id"

        with (
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_migrate_entity_ids_v2",
                new_callable=AsyncMock,
            ) as mock_v2,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_fix_original_names_v4",
                new_callable=AsyncMock,
            ) as mock_v4,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_clear_stale_suggested_object_ids_v5",
            ) as mock_v5,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_clear_stale_object_id_base_v6",
            ) as mock_v6,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_fix_object_id_base_v7",
            ) as mock_v7,
            patch(
                "custom_components.abb_fimer_pvi_vsn_rest._async_populate_known_devices_v8",
            ) as mock_v8,
        ):
            result = await async_migrate_entry(mock_hass, entry)

        assert result is True
        mock_v2.assert_not_called()
        mock_v4.assert_not_called()
        mock_v5.assert_not_called()
        mock_v6.assert_not_called()
        mock_v7.assert_not_called()
        mock_v8.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_version_8_noop(self, mock_hass: MagicMock) -> None:
        """Test no migration needed when already at version 8."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 8

        result = await async_migrate_entry(mock_hass, entry)

        assert result is True
        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_future_version_fails(self, mock_hass: MagicMock) -> None:
        """Test downgrade from future version fails."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 9

        result = await async_migrate_entry(mock_hass, entry)

        assert result is False


class TestSyncKnownDevices:
    """Tests for _sync_known_devices helper function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create mock config entry with known devices."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {
            "known_devices": [
                {
                    "device_id": "111033-3N16-1421",
                    "device_type": "datalogger",
                    "is_datalogger": True,
                },
                {"device_id": "077909-3G82-3112", "device_type": "unknown", "is_datalogger": False},
            ],
        }
        return entry

    @pytest.fixture
    def mock_discovery_result(self) -> DiscoveryResult:
        """Create discovery result with both devices."""
        return DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="111033-3N16-1421",
                    raw_device_id="111033-3N16-1421",
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

    def test_updates_stale_device_type(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
        mock_discovery_result: DiscoveryResult,
    ) -> None:
        """Test that stale device_type is updated from discovery."""
        _sync_known_devices(mock_hass, mock_config_entry, mock_discovery_result)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        inverter = next(
            d for d in new_data["known_devices"] if d["device_id"] == "077909-3G82-3112"
        )
        assert inverter["device_type"] == "inverter_3phases"

    def test_adds_new_devices(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that newly discovered devices are added."""
        mock_config_entry.data = {"known_devices": []}
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="new-device",
                    raw_device_id="new-device",
                    device_type="meter",
                    device_model="Meter-1",
                    manufacturer="ABB",
                    firmware_version="1.0",
                    hardware_version=None,
                    is_datalogger=False,
                ),
            ],
            status_data={},
        )

        _sync_known_devices(mock_hass, mock_config_entry, result)

        call_args = mock_hass.config_entries.async_update_entry.call_args
        new_data = call_args.kwargs.get("data", call_args[1].get("data", {}))
        assert len(new_data["known_devices"]) == 1
        assert new_data["known_devices"][0]["device_id"] == "new-device"

    def test_no_update_when_unchanged(
        self,
        mock_hass: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test no config entry update when nothing changed."""
        # Set correct device_type so no update needed
        mock_config_entry.data["known_devices"][1]["device_type"] = "inverter_3phases"
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="111033-3N16-1421",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="111033-3N16-1421",
                    raw_device_id="111033-3N16-1421",
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

        _sync_known_devices(mock_hass, mock_config_entry, result)

        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestDetectMissingDevices:
    """Tests for _detect_missing_devices helper function."""

    def test_detects_missing_non_datalogger(self) -> None:
        """Test detection of missing non-datalogger devices."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "known_devices": [
                {"device_id": "logger-001", "device_type": "datalogger", "is_datalogger": True},
                {"device_id": "inv-001", "device_type": "inverter_3phases", "is_datalogger": False},
            ],
        }
        # Discovery only finds datalogger
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="logger-001",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="logger-001",
                    raw_device_id="logger-001",
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
            ],
            status_data={},
        )

        missing = _detect_missing_devices(entry, result)

        assert missing == {"inv-001"}

    def test_no_missing_when_all_found(self) -> None:
        """Test no missing devices when all are discovered."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "known_devices": [
                {"device_id": "logger-001", "device_type": "datalogger", "is_datalogger": True},
                {"device_id": "inv-001", "device_type": "inverter_3phases", "is_datalogger": False},
            ],
        }
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="logger-001",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[
                DiscoveredDevice(
                    device_id="logger-001",
                    raw_device_id="logger-001",
                    device_type="datalogger",
                    device_model="VSN300",
                    manufacturer="ABB",
                    firmware_version="1.9.2",
                    hardware_version=None,
                    is_datalogger=True,
                ),
                DiscoveredDevice(
                    device_id="inv-001",
                    raw_device_id="inv-001",
                    device_type="inverter_3phases",
                    device_model="PVI-10.0",
                    manufacturer="Power-One",
                    firmware_version="C008",
                    hardware_version=None,
                    is_datalogger=False,
                ),
            ],
            status_data={},
        )

        missing = _detect_missing_devices(entry, result)

        assert missing == set()

    def test_excludes_datalogger_from_missing(self) -> None:
        """Test that datalogger is never flagged as missing."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "known_devices": [
                {"device_id": "logger-001", "device_type": "datalogger", "is_datalogger": True},
            ],
        }
        # Empty discovery (shouldn't happen — discovery fails if datalogger is down)
        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="logger-001",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[],
            status_data={},
        )

        missing = _detect_missing_devices(entry, result)

        assert missing == set()

    def test_empty_known_devices(self) -> None:
        """Test no missing when known_devices is empty."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {"known_devices": []}

        result = DiscoveryResult(
            vsn_model="VSN300",
            requires_auth=True,
            logger_sn="logger-001",
            logger_model="VSN300",
            firmware_version="1.9.2",
            hostname=None,
            devices=[],
            status_data={},
        )

        missing = _detect_missing_devices(entry, result)

        assert missing == set()
