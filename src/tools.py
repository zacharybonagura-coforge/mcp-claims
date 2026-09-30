"""Load mock fixtures and look up an employee with their equipment."""

from pathlib import Path
from typing import Any

from store.base import Store
from store.json import JsonStore

_DATA = Path(__file__).resolve().parents[1] / "data"

staff: Store = JsonStore(_DATA / "employees.json")
inventory: Store = JsonStore(_DATA / "inventory.json")


def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return every employee row for ``employee_id``, with equipment attached."""
    employees = staff.load()["employees"]
    assignments = inventory.load()["assignments"]

    equipment: list[dict[str, Any]] = []
    for assignment in assignments:
        if assignment["employee_id"] == employee_id:
            equipment.append(assignment)

    matches: list[dict[str, Any]] = []
    for row in employees:
        if row["employee_id"] == employee_id:
            matches.append({**row, "equipment": equipment})
    return matches
