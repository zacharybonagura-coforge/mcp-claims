"""Python functions used by the MCP tools."""

from pathlib import Path
from typing import Any

from models import Assignment, PolicyLimit, Staff
from store.base import Store
from store.json import JsonStore

_DATA = Path(__file__).resolve().parents[1] / "data"

staff: Store = JsonStore(_DATA / "staff.json")
inventory: Store = JsonStore(_DATA / "inventory.json")
policies: Store = JsonStore(_DATA / "policy_limits.json")


def _load_staff() -> list[Staff]:
    rows = []
    for raw in staff.load()["staff"]:
        rows.append(Staff.model_validate(raw))
    return rows


def _load_assignments() -> list[Assignment]:
    rows = []
    for raw in inventory.load()["assignments"]:
        rows.append(Assignment.model_validate(raw))
    return rows


def _load_limits() -> list[PolicyLimit]:
    rows = []
    for raw in policies.load()["limits"]:
        rows.append(PolicyLimit.model_validate(raw))
    return rows


def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return role, hire_date, and equipment for this employee id."""
    employees = _load_staff()
    assignments = _load_assignments()

    equipment: list[Assignment] = []
    # Collect assignments for this employee_id.
    for assignment in assignments:
        if assignment.employee_id == employee_id:
            equipment.append(assignment)

    matches: list[dict[str, Any]] = []
    # Attach that kit to every staff row with this id.
    for row in employees:
        if row.employee_id == employee_id:
            person = row.model_copy(update={"equipment": equipment})
            matches.append(person.model_dump(exclude_none=True))
    return matches


def get_policy_limits(role: str) -> dict[str, Any]:
    """Return per-category caps and refresh windows for ``role``.
    Unknown roles yield ``limits: []``.
    """
    payload = _load_limits()
    limits: list[dict[str, Any]] = []
    # Keep limit rows for this role only.
    for row in payload:
        if row.role == role:
            limits.append(row.model_dump(exclude_none=True))
    
    return {
        "role": role,
        "limits": limits,
    }