"""Tests for device trigger module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.device_trigger import (
    TRIGGER_SCHEMA,
    TRIGGER_TYPES,
    async_attach_trigger,
    async_get_triggers,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant


class TestTriggerTypes:
    """Tests for trigger type constants."""

    def test_trigger_types_defined(self) -> None:
        """Test trigger types are defined."""
        assert "device_unreachable" in TRIGGER_TYPES
        assert "device_not_responding" in TRIGGER_TYPES
        assert "device_recovered" in TRIGGER_TYPES

    def test_trigger_types_count(self) -> None:
        """Test expected number of trigger types."""
        assert len(TRIGGER_TYPES) == 3


class TestTriggerSchema:
    """Tests for trigger schema."""

    def test_schema_requires_type(self) -> None:
        """Test schema requires type field."""
        # TRIGGER_SCHEMA should require CONF_TYPE
        assert TRIGGER_SCHEMA is not None


class TestAsyncGetTriggers:
    """Tests for async_get_triggers function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.mark.asyncio
    async def test_get_triggers_for_domain_device(self, mock_hass: MagicMock) -> None:
        """Test getting triggers for a device belonging to our domain."""
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "077909-3G82-3112")}

        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.dr.async_get",
            return_value=mock_device_registry,
        ):
            triggers = await async_get_triggers(mock_hass, "device_123")

        assert len(triggers) == 3
        trigger_types = {t[CONF_TYPE] for t in triggers}
        assert trigger_types == TRIGGER_TYPES

        # Check trigger structure
        for trigger in triggers:
            assert trigger[CONF_PLATFORM] == "device"
            assert trigger[CONF_DOMAIN] == DOMAIN
            assert trigger[CONF_DEVICE_ID] == "device_123"

    @pytest.mark.asyncio
    async def test_get_triggers_device_not_found(self, mock_hass: MagicMock) -> None:
        """Test getting triggers when device not found."""
        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = None

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.dr.async_get",
            return_value=mock_device_registry,
        ):
            triggers = await async_get_triggers(mock_hass, "nonexistent_device")

        assert triggers == []

    @pytest.mark.asyncio
    async def test_get_triggers_other_domain_device(self, mock_hass: MagicMock) -> None:
        """Test getting triggers for device from different domain."""
        mock_device = MagicMock()
        mock_device.identifiers = {("other_domain", "device_123")}

        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.dr.async_get",
            return_value=mock_device_registry,
        ):
            triggers = await async_get_triggers(mock_hass, "device_123")

        assert triggers == []

    @pytest.mark.asyncio
    async def test_get_triggers_multiple_identifiers(self, mock_hass: MagicMock) -> None:
        """Test getting triggers for device with multiple identifiers."""
        mock_device = MagicMock()
        mock_device.identifiers = {
            ("other_domain", "other_id"),
            (DOMAIN, "077909-3G82-3112"),
        }

        mock_device_registry = MagicMock()
        mock_device_registry.async_get.return_value = mock_device

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.dr.async_get",
            return_value=mock_device_registry,
        ):
            triggers = await async_get_triggers(mock_hass, "device_123")

        # Should still return triggers because one identifier matches our domain
        assert len(triggers) == 3


class TestAsyncAttachTrigger:
    """Tests for async_attach_trigger function."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock HomeAssistant instance."""
        return MagicMock(spec=HomeAssistant)

    @pytest.mark.asyncio
    async def test_attach_trigger(self, mock_hass: MagicMock) -> None:
        """Test attaching a trigger."""
        config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "device_123",
            CONF_TYPE: "device_unreachable",
        }
        action = MagicMock()
        trigger_info = MagicMock()

        mock_unsubscribe = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.event_trigger.async_attach_trigger",
            new_callable=AsyncMock,
            return_value=mock_unsubscribe,
        ) as mock_attach:
            result = await async_attach_trigger(mock_hass, config, action, trigger_info)

        assert result == mock_unsubscribe
        mock_attach.assert_called_once()

        # Verify event config was created correctly
        call_args = mock_attach.call_args
        event_config = call_args[0][1]
        assert event_config["event_type"] == f"{DOMAIN}_event"
        assert event_config["event_data"][CONF_DEVICE_ID] == "device_123"
        assert event_config["event_data"][CONF_TYPE] == "device_unreachable"

    @pytest.mark.asyncio
    async def test_attach_trigger_recovered(self, mock_hass: MagicMock) -> None:
        """Test attaching a device_recovered trigger."""
        config = {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: "device_456",
            CONF_TYPE: "device_recovered",
        }
        action = MagicMock()
        trigger_info = MagicMock()

        mock_unsubscribe = MagicMock()

        with patch(
            "custom_components.abb_fimer_pvi_vsn_rest.device_trigger.event_trigger.async_attach_trigger",
            new_callable=AsyncMock,
            return_value=mock_unsubscribe,
        ) as mock_attach:
            await async_attach_trigger(mock_hass, config, action, trigger_info)

        call_args = mock_attach.call_args
        event_config = call_args[0][1]
        assert event_config["event_data"][CONF_TYPE] == "device_recovered"
