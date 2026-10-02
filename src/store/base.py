"""Store port: load fixture data without tying callers to a file format."""


from collections.abc import Mapping
from typing import Any, Protocol


class Store(Protocol):
    """Source of HR, inventory, or policy data."""

    def load(self) -> Mapping[str, Any]: 
        """Return the store payload as a mapping.
        Callers treat the result as immutable. Identity lookups and
        joins live on the directory, not on the store.
        """
        ...
    
    def save(self, payload: Mapping[str, Any]) -> None:
        """Save payload with ``payload``.
        Callers pass a full mapping, not a single row.
        """
        ...
