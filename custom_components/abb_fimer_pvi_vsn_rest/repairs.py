"""Repair issues for ABB/FIMER PVI VSN REST integration.

https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.helpers import issue_registry as ir

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Issue IDs
ISSUE_CONNECTION_FAILED = "connection_failed"
ISSUE_RECOVERY_SUCCESS = "recovery_success"


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow to fix a repair issue.

    This is called by Home Assistant when user clicks on a fixable repair issue.
    For recovery notifications, we use ConfirmRepairFlow which shows the issue
    description and a simple "Submit" button to acknowledge/dismiss.
    """
    # Recovery notifications just need acknowledgment - use ConfirmRepairFlow
    return ConfirmRepairFlow()


def create_connection_issue(
    hass: HomeAssistant,
    entry_id: str,
    device_name: str,
    host: str,
) -> None:
    """Create a repair issue for connection failure.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device
        host: Device host/IP

    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_CONNECTION_FAILED}_{entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_CONNECTION_FAILED,
        translation_placeholders={
            "device_name": device_name,
            "host": host,
        },
    )
    _LOGGER.debug("Created repair issue for connection failure: %s", device_name)


def delete_connection_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the connection failure repair issue.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID

    """
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_CONNECTION_FAILED}_{entry_id}")
    _LOGGER.debug("Deleted repair issue for entry: %s", entry_id)


def create_recovery_notification(
    hass: HomeAssistant,
    entry_id: str,
    device_name: str,
    started_at: str,
    ended_at: str,
    downtime: str,
) -> None:
    """Create a persistent notification for device recovery.

    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID
        device_name: Name of the device
        started_at: Time when failure started (locale-aware format)
        ended_at: Time when device recovered (locale-aware format)
        downtime: Total downtime in compact format (e.g., "5m 23s")

    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_RECOVERY_SUCCESS}_{entry_id}",
        is_fixable=True,  # User can dismiss by clicking "Mark as resolved"
        is_persistent=True,  # Survives HA restart, requires user acknowledgment
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_RECOVERY_SUCCESS,
        translation_placeholders={
            "device_name": device_name,
            "started_at": started_at,
            "ended_at": ended_at,
            "downtime": downtime,
        },
    )
    _LOGGER.debug(
        "Created recovery notification for %s (started: %s, ended: %s, downtime: %s)",
        device_name,
        started_at,
        ended_at,
        downtime,
    )
