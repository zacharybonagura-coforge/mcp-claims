"""Load mock fixtures and look up an employee with their equipment."""

from pathlib import Path
from typing import Any

from store.base import Store
from store.json import JsonStore

_DATA = Path(__file__).resolve().parents[1] / "data"

staff: Store = JsonStore(_DATA / "staff.json")
inventory: Store = JsonStore(_DATA / "inventory.json")
policies: Store = JsonStore(_DATA / "policy_limits.json")


def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return role, hire_date, and equipment for this employee id."""
    employees = staff.load()["staff"]
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


def get_policy_limits(role: str) -> dict[str, Any]:
    """Return new-hire rules and per-category caps/refresh windows for ``role``.
    Unknown roles yield ``limits: []``.
    """
    payload = policies.load()
    limits: list[dict[str, Any]] = []
    for row in payload["limits"]:
        if row["role"] == role:
            limits.append(row)
    return {
        "role": role,
        "limits": limits,
    }
