"""Base specification class for business rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class Specification[T](ABC):
    """Base specification class implementing the Specification pattern."""

    @abstractmethod
    def is_satisfied_by(self, entity: T) -> bool:
        """Check if the entity satisfies this specification."""
        pass

    @abstractmethod
    def why_not_satisfied(self, entity: T) -> str | None:
        """Return reason why specification is not satisfied, or None if it is."""
        pass

    def and_(self, other: Specification[T]) -> Specification[T]:
        """Combine this specification with another using AND logic."""
        return AndSpecification(self, other)

    def or_(self, other: Specification[T]) -> Specification[T]:
        """Combine this specification with another using OR logic."""
        return OrSpecification(self, other)

    def not_(self) -> Specification[T]:
        """Negate this specification."""
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """Specification that combines two specifications with AND logic."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right

    def is_satisfied_by(self, entity: T) -> bool:
        """Check if both specifications are satisfied."""
        return self._left.is_satisfied_by(entity) and self._right.is_satisfied_by(entity)

    def why_not_satisfied(self, entity: T) -> str | None:
        """Return combined reason why specifications are not satisfied."""
        left_reason = self._left.why_not_satisfied(entity)
        right_reason = self._right.why_not_satisfied(entity)

        if left_reason and right_reason:
            return f"{left_reason} AND {right_reason}"
        elif left_reason:
            return left_reason
        elif right_reason:
            return right_reason
        else:
            return None


class OrSpecification(Specification[T]):
    """Specification that combines two specifications with OR logic."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right

    def is_satisfied_by(self, entity: T) -> bool:
        """Check if at least one specification is satisfied."""
        return self._left.is_satisfied_by(entity) or self._right.is_satisfied_by(entity)

    def why_not_satisfied(self, entity: T) -> str | None:
        """Return reason why neither specification is satisfied."""
        if self.is_satisfied_by(entity):
            return None

        left_reason = self._left.why_not_satisfied(entity)
        right_reason = self._right.why_not_satisfied(entity)

        return f"Neither condition satisfied: ({left_reason}) OR ({right_reason})"


class NotSpecification(Specification[T]):
    """Specification that negates another specification."""

    def __init__(self, spec: Specification[T]):
        self._spec = spec

    def is_satisfied_by(self, entity: T) -> bool:
        """Check if the negated specification is satisfied."""
        return not self._spec.is_satisfied_by(entity)

    def why_not_satisfied(self, entity: T) -> str | None:
        """Return reason why negated specification is not satisfied."""
        if self.is_satisfied_by(entity):
            return None

        return f"NOT ({self._spec.why_not_satisfied(entity) or 'satisfied'})"
