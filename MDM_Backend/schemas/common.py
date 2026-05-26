"""
signalmdm/schemas/common.py
----------------------------
Shared Pydantic v2 response envelopes and base utilities.

Every API endpoint returns a `StandardResponse` so clients always deal
with a consistent JSON structure regardless of endpoint.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class StandardResponse(BaseModel, Generic[DataT]):
    """
    Uniform API response envelope.

    Example success::

        {"success": true, "message": "Source registered", "data": {...}, "errors": []}

    Example error::

        {"success": false, "message": "Validation failed", "data": null, "errors": ["field X required"]}
    """

    success: bool = True
    message: str = ""
    data: Optional[DataT] = None
    errors: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


def ok(data: Any = None, message: str = "OK") -> dict:
    """Shorthand for a successful response dict."""
    return {"success": True, "message": message, "data": data, "errors": []}


def err(message: str = "Error", errors: list[str] | None = None) -> dict:
    """Shorthand for an error response dict."""
    return {"success": False, "message": message, "data": None, "errors": errors or []}
