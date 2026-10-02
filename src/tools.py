"""Python functions used by the MCP tools."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

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


def _get_employee_by_id(employee_id: str) -> list[Staff]:
    employees = _load_staff()
    assignments = _load_assignments()

    equipment: list[Assignment] = []
    # Collect assignments for this employee_id.
    for assignment in assignments:
        if assignment.employee_id == employee_id:
            equipment.append(assignment)

    matches: list[Staff] = []
    # Attach that kit to every staff row with this id.
    for row in employees:
        if row.employee_id == employee_id:
            matches.append(row.model_copy(update={"equipment": equipment}))
    return matches

def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return role, hire_date, and equipment for this employee id."""
    matches: list[dict[str, Any]] = []
    # Attach that kit to every staff row with this id.
    for person in _get_employee_by_id(employee_id):
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




COVERED_CATEGORIES = (
    "monitor",
    "laptop",
    "dock",
    "headset",
    "keyboard",
    "mouse",
)

def check_request_eligibility(employee_id: str, item: str) -> dict[str, Any]:
    """Return whether ``item`` is within cap/refresh for this employee."""
    try:
        people = _get_employee_by_id(employee_id)
        limits = _load_limits()
    except ValidationError:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": False,
            "policy_rule": None,
            "detail": "parse_error",
        }
    if len(people) != 1:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": None,
            "policy_rule": None,
            "detail": "identity",
        }
    person = people[0]

    text = item.lower()
    found: list[str] = []
    # Every covered category named in the item. More than one is a decline.
    for name in COVERED_CATEGORIES:
        if name in text:
            found.append(name)

    if len(found) == 0:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": None,
            "policy_rule": None,
            "detail": "unmapped_item",
        }
    if len(found) > 1:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": False,
            "policy_rule": None,
            "detail": "mixed_items",
        }
    category = found[0]

    # Units already assigned in that category.
    matching_equipment: list[Assignment] = []
    for unit in person.equipment or []:
        if unit.category == category:
            matching_equipment.append(unit)

    limit = None
    # One policy row for role + category.
    for row in limits:
        if row.role == person.role and row.category == category:
            limit = row
            break
    
    if limit is None:
        return {
            "employee_id": employee_id,
            "item": item,
            "category": category,
            "eligible": None,
            "policy_rule": None,
            "detail": "policy_gap",
        }

    active = 0
    # Count active units toward the cap.
    for unit in matching_equipment:
        # Cap is unknown if any matching unit has no status.
        if unit.status is None:
            return {
                "employee_id": employee_id,
                "item": item,
                "category": category,
                "eligible": None,
                "policy_rule": limit.policy_rule,
                "detail": "incomplete_inventory",
            }
        if unit.status == "active":
            active += 1

    cap = limit.cap_active
    under_cap = active < cap
    if under_cap:
        return {
            "employee_id": employee_id,
            "item": item,
            "category": category,
            "eligible": under_cap,
            "policy_rule": limit.policy_rule,
            "detail": "within_cap",
            "active": active,
            "cap_active": cap,
        }

    # Refresh age is unknown if any matching unit has no assigned_on.
    for unit in matching_equipment:
        if unit.assigned_on is None:
            return {
                "employee_id": employee_id,
                "item": item,
                "category": category,
                "eligible": None,
                "policy_rule": limit.policy_rule,
                "detail": "incomplete_inventory",
                "active": active,
                "cap_active": cap,
            }

    refresh_years = limit.refresh_years
    # If there is no refresh window, request is not eligible.
    if refresh_years is None:
        return {
            "employee_id": employee_id,
            "item": item,
            "category": category,
            "eligible": False,
            "policy_rule": limit.policy_rule,
            "detail": "refresh_too_soon",
            "active": active,
            "cap_active": cap,
        }

    today = datetime.now(tz=timezone.utc).date()
    oldest = None
    oldest_assigned = None
    # Oldest dated unit is the first candidate to replace.
    for unit in matching_equipment:
        if unit.assigned_on is None:
            continue
        if oldest_assigned is None or unit.assigned_on < oldest_assigned:
            oldest = unit
            oldest_assigned = unit.assigned_on

    replace_unit = None
    if oldest_assigned is not None:
        age_years = (today - oldest_assigned).days / 365.25
        if age_years >= refresh_years:
            replace_unit = oldest

    due = replace_unit is not None
    payload = {
        "employee_id": employee_id,
        "item": item,
        "category": category,
        "eligible": due,
        "policy_rule": limit.policy_rule,
        "detail": "refresh_ok" if due else "refresh_too_soon",
        "active": active,
        "cap_active": cap,
    }

    if due and replace_unit is not None:
        payload["replace_unit"] = replace_unit.model_dump(exclude_none=True)
    return payload
