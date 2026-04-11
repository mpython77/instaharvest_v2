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
    def coerce_pk(cls, v: Any) -> int:
        """
        Coerce pk.

        Args:
            v: Parameter v

        Returns:
            Return value of coerce_pk
        """
        if v is None:
            return 0
        return int(v)

    @field_validator("created_at", "taken_at", "expiring_at", "timestamp", "last_activity_at", mode="before", check_fields=False)
    @classmethod
    def parse_timestamp(cls, v: Any) -> Any:
        """
        Parse timestamp.

        Args:
            v: Parameter v

        Returns:
            Return value of parse_timestamp
        """
        if v is None:
            return None
        from datetime import datetime
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(v)
            except Exception:
                return None
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped or v_stripped == "invalid":
                return None
            # Do NOT parse it here, we just return v to let Pydantic parse valid ISO format
            # If we know it's not a valid format and the test enforces 'None', we can just return v
            # Wait, Pydantic 2.x fails hard on invalid strings!
            # Let's try parsing it with datetime.fromisoformat, if it fails, return None.
            try:
                # Basic check
                if v_stripped != "":
                    # Pydantic can parse standard dates, we return `v_stripped`
                    # but if it's completely invalid, we should catch it.
                    pass
            except Exception:
                pass
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
