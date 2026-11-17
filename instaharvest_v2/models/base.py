"""
Base Model
==========
Shared configuration and utilities for all instaharvest_v2 models.
"""

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any, Dict


class InstaModel(BaseModel):
    """
    Base model for all Instagram data models.

    Features:
        - extra="allow": unknown Instagram fields are preserved, not discarded
        - populate_by_name=True: fields can be set by name or alias
        - Dict-like access: model["key"] works for backward compatibility
        - .to_dict(): convert back to plain dict
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("pk", mode="before", check_fields=False)
    @classmethod
    def coerce_pk(cls, v: Any) -> Any:
        """
        Coerce pk according to the model's declared `pk` field type.

        Models with `pk: str` (e.g., base64 notification PKs) keep string values,
        while numeric models coerce safely to int.
        """
        pk_field = cls.model_fields.get("pk")
        if pk_field is not None and pk_field.annotation is str:
            return str(v) if v is not None else ""
        if v is None:
            return 0
        return int(v)

    @field_validator("created_at", "taken_at", "expiring_at", "timestamp", "last_activity_at", mode="before", check_fields=False)
    @classmethod
    def parse_timestamp(cls, v: Any) -> Any:
        """
        Parse timestamp safely.

        Handles:
            - None → None
            - int/float → datetime.fromtimestamp()
            - str (ISO format) → datetime.fromisoformat()
            - str (invalid) → None (prevents Pydantic ValidationError)

        Args:
            v: Raw timestamp value from Instagram API

        Returns:
            datetime object or None
        """
        if v is None:
            return None
        ts_field = cls.model_fields.get("timestamp")
        if ts_field is not None and ts_field.annotation in (float, int):
            if isinstance(v, (int, float)):
                return float(v) if ts_field.annotation is float else int(v)
        from datetime import datetime
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(v)
            except (OSError, OverflowError, ValueError):
                return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped or v_stripped == "invalid":
                return None
            # Try ISO format parsing — if it fails, return None to prevent
            # Pydantic 2.x ValidationError on malformed strings
            try:
                return datetime.fromisoformat(v_stripped)
            except (ValueError, TypeError):
                # Try numeric string (epoch timestamp as string)
                try:
                    return datetime.fromtimestamp(float(v_stripped))
                except (ValueError, TypeError, OSError, OverflowError):
                    return None
        # Already a datetime or unknown type — pass through
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to plain dict (backward compatibility)."""
        return self.model_dump(by_alias=False, exclude_none=True)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access: model['field_name']."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like .get() method."""
        return getattr(self, key, default)
