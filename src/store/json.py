"""JSON file adapter for :class:`store.base.Store`."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class JsonStore:
    """Load or replace one JSON object on disk.
    Each instance maps to a single file (staff, inventory, policy
    limits, or reviews). Parsing stops at JSON; it does not validate
    keys or join records.
    """

    def __init__(self, path: Path) -> None:
        """Bind this store to ``path``."""
        self._path = path

    def load(self) -> dict[str, Any]:
        """Read the file and return the decoded JSON object."""
        return json.loads(self._path.read_text())

    def save(self, payload: Mapping[str, Any]) -> None:
        """Write ``payload`` as JSON to this store's file."""
        self._path.write_text(json.dumps(payload, indent=2) + "\n")
