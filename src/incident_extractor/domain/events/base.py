"""Base domain event class."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytz


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for all domain events."""

    event_id: str
    occurred_at: datetime
    aggregate_id: str
    event_version: int = 1
    metadata: dict[str, Any] | None = None

    @classmethod
    def create(cls, aggregate_id: str, metadata: dict[str, Any] | None = None, **kwargs: Any) -> DomainEvent:
        """Create a new domain event instance."""
        return cls(
            event_id=str(uuid4()),
            occurred_at=datetime.now(pytz.timezone("America/Sao_Paulo")),
            aggregate_id=aggregate_id,
            metadata=metadata or {},
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "event_version": self.event_version,
            "metadata": self.metadata,
        }
