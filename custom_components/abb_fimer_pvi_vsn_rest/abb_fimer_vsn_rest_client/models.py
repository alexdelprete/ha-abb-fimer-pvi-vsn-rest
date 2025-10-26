"""Data models."""
from dataclasses import dataclass
from typing import Any


@dataclass
class VSNDevice:
    """VSN device."""

    device_id: str
    device_type: str
    serial_number: str
    manufacturer: str
    model: str
    points: dict[str, Any]
