"""JSON file adapter for :class:`store.base.Store`."""

import json
from pathlib import Path
from typing import Any


class JsonStore:
    """Load one JSON object from disk into a dict.
    Each instance maps to a single file (employees, inventory, or
    policy limits). Parsing stops at JSON; it does not validate keys
    or join records.
    """

    def __init__(self, path: Path) -> None:
        """Bind this store to ``path``."""
        self._path = path

    def load(self) -> dict[str, Any]:
        """Read the file and return the decoded JSON object."""
        return json.loads(self._path.read_text())
