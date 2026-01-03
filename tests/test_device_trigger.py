"""Tests for ABB FIMER PVI VSN REST device triggers."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

from custom_components.abb_fimer_pvi_vsn_rest.const import DOMAIN
from custom_components.abb_fimer_pvi_vsn_rest.device_trigger import (
    TRIGGER_TYPES,
    async_get_triggers,
)
from homeassistant.helpers import device_registry as dr


async def test_trigger_types_defined() -> None:
    """Test that trigger types are properly defined."""
    assert "device_unreachable" in TRIGGER_TYPES
    assert "device_not_responding" in TRIGGER_TYPES
    assert "device_recovered" in TRIGGER_TYPES
    assert len(TRIGGER_TYPES) == 3


async def test_async_get_triggers(
    hass,
    mock_config_entry,
    mock_coordinator: MagicMock,
) -> None:
    """Test getting triggers for a device."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    # Create a mock device entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "test_device_id")},
        name="Test VSN Device",
    )

    triggers = await async_get_triggers(hass, device_entry.id)

    # Should return triggers for each type
    assert len(triggers) == len(TRIGGER_TYPES)

    # Verify trigger structure
    for trigger in triggers:
        assert trigger["platform"] == "device"
        assert trigger["domain"] == DOMAIN
        assert trigger["device_id"] == device_entry.id
        assert trigger["type"] in TRIGGER_TYPES


async def test_trigger_has_correct_metadata(
    hass,
    mock_config_entry,
    mock_coordinator: MagicMock,
) -> None:
    """Test that triggers have correct metadata."""
    mock_config_entry.add_to_hass(hass)

    # Setup runtime data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    # Create a mock device entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "test_device_id")},
        name="Test VSN Device",
    )

    triggers = await async_get_triggers(hass, device_entry.id)

    # Find the device_recovered trigger
    recovered_trigger = next((t for t in triggers if t["type"] == "device_recovered"), None)
    assert recovered_trigger is not None
    assert recovered_trigger["platform"] == "device"
    assert recovered_trigger["domain"] == DOMAIN
