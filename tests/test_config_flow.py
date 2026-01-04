"""Tests for ABB FIMER PVI VSN REST config flow."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abb_fimer_pvi_vsn_rest.abb_fimer_vsn_rest_client.exceptions import (
    VSNAuthenticationError,
    VSNConnectionError,
)
from custom_components.abb_fimer_pvi_vsn_rest.const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_ENABLE_STARTUP_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_PREFIX_DATALOGGER,
    CONF_PREFIX_INVERTER,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    CONF_VSN_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import TEST_HOST, TEST_LOGGER_SN, TEST_PASSWORD, TEST_USERNAME, TEST_VSN_MODEL


@pytest.fixture(name="integration_setup", autouse=True)
def integration_setup_fixture():
    """Mock integration entry setup to avoid loading the full integration."""
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_form_user(
    hass: HomeAssistant,
    mock_discover_vsn_device_config_flow: AsyncMock,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: TEST_HOST,
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == f"{TEST_VSN_MODEL} ({TEST_LOGGER_SN})"
    assert result2["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
        CONF_VSN_MODEL: TEST_VSN_MODEL,
        "requires_auth": False,
    }
    assert result2["options"] == {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    }


async def test_form_cannot_connect(
    hass: HomeAssistant,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        side_effect=Exception("Connection refused"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "unknown"


async def test_form_invalid_auth(
    hass: HomeAssistant,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we handle invalid auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        side_effect=VSNAuthenticationError("Invalid credentials"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: "wrong_user",
                CONF_PASSWORD: "wrong_pass",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "invalid_auth"


async def test_form_connection_error(
    hass: HomeAssistant,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we handle connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        side_effect=VSNConnectionError("Connection failed"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "cannot_connect"


async def test_form_timeout_error(
    hass: HomeAssistant,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we handle timeout error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        side_effect=VSNConnectionError("Connection timeout"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == "timeout"


async def test_form_already_configured(
    hass: HomeAssistant,
    mock_discovery_result,
    mock_check_socket_connection: AsyncMock,
) -> None:
    """Test we abort if already configured."""
    # Patch discover_vsn_device for this specific test to allow multiple calls
    with patch(
        "custom_components.abb_fimer_pvi_vsn_rest.config_flow.discover_vsn_device",
        return_value=mock_discovery_result,
    ):
        # First, complete a successful flow to create an entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # Verify entry was created
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        # Now try to configure again with the same device - should abort
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry,
    mock_discovered_devices,
) -> None:
    """Test options flow."""
    # Add config entry
    mock_config_entry.add_to_hass(hass)

    # Create a mock coordinator with discovered_devices
    mock_coordinator = MagicMock()
    mock_coordinator.discovered_devices = mock_discovered_devices

    # Mock runtime_data
    @dataclass
    class RuntimeData:
        coordinator: object

    mock_config_entry.runtime_data = RuntimeData(coordinator=mock_coordinator)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # Submit options - need to include all required fields
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 120,
            CONF_ENABLE_REPAIR_NOTIFICATION: True,
            CONF_ENABLE_STARTUP_NOTIFICATION: False,
            CONF_FAILURES_THRESHOLD: 3,
            CONF_RECOVERY_SCRIPT: "",
            CONF_PREFIX_INVERTER: "",
            CONF_PREFIX_DATALOGGER: "",
        },
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    # Verify the key option was updated
    assert result2["data"][CONF_SCAN_INTERVAL] == 120
