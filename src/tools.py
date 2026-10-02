"""Python functions used by the MCP tools."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from models import Assignment, PolicyLimit, ReviewStatus, ReviewTicket, Staff
from store.base import Store
from store.json import JsonStore

_DATA = Path(__file__).resolve().parents[1] / "data"

staff: Store = JsonStore(_DATA / "staff.json")
inventory: Store = JsonStore(_DATA / "inventory.json")
policies: Store = JsonStore(_DATA / "policy_limits.json")
reviews: Store = JsonStore(_DATA / "reviews.json")

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


def _load_reviews() -> list[ReviewTicket]:
    rows = []
    for raw in reviews.load()["tickets"]:
        rows.append(ReviewTicket.model_validate(raw))
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
            "eligible": None,
            "policy_rule": None,
            "detail": (
                f"staff or inventory JSON failed validation; "
                f"cannot check {item!r} for {employee_id}"
            ),
        }
    n = len(people)
    if n == 0:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": None,
            "policy_rule": None,
            "detail": (
                f"no staff row for employee_id {employee_id}; "
                "identity is unknown, cannot allow or deny"
            ),
        }
    if n > 1:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": None,
            "policy_rule": None,
            "detail": (
                f"{n} staff rows share employee_id {employee_id}; "
                "duplicate identity, do not pick a row"
            ),
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
            "detail": (
                f"{item!r} matches no covered category "
                f"({', '.join(COVERED_CATEGORIES)}); unmapped item"
            ),
        }
    if len(found) > 1:
        return {
            "employee_id": employee_id,
            "item": item,
            "eligible": None,
            "policy_rule": None,
            "detail": (
                f"{item!r} names more than one covered category "
                f"({', '.join(found)}); mixed request, cannot score as one item"
            ),
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
            "detail": (
                f"no policy row for role {person.role!r} and category {category!r}; "
                "policy gap, cannot allow or deny"
            ),
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
                "detail": (
                    f"{category} assignment {unit.assignment_id} "
                    f"(asset_tag {unit.asset_tag}) has no status; "
                    "cannot count active units toward the cap"
                ),
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
            "detail": (
                f"{person.role} {category} is under cap: "
                f"{active} active, cap {cap}, room for more"
            ),
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
                "detail": (
                    f"{category} assignment {unit.assignment_id} "
                    f"(asset_tag {unit.asset_tag}) has no assigned_on; "
                    f"at cap ({active}/{cap}) so refresh age cannot be computed"
                ),
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
            "detail": (
                f"{person.role} {category} is at cap ({active}/{cap}) "
                "and this policy row has no refresh_years; cannot replace"
            ),
            "active": active,
            "cap_active": cap,
        }

    today = datetime.now(tz=UTC).date()
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
        "detail": (
            (
                f"{person.role} {category} is at cap ({active}/{cap}); "
                f"oldest unit assigned {oldest_assigned} is due for refresh "
                f"(window {refresh_years} years)"
            )
            if due
            else (
                f"{person.role} {category} is at cap ({active}/{cap}); "
                f"oldest unit assigned {oldest_assigned} is still inside the "
                f"{refresh_years}-year refresh window"
            )
        ),
        "active": active,
        "cap_active": cap,
    }

    if due and replace_unit is not None:
        payload["replace_unit"] = replace_unit.model_dump(exclude_none=True)
    return payload


def _next_review_id(tickets: list[ReviewTicket]) -> str:
    highest = 0
    for ticket in tickets:
        raw = ticket.review_ticket_id.removeprefix("REV-")
        try:
            n = int(raw)
        except ValueError:
            continue
        highest = max(highest, n)
    return f"REV-{highest + 1:04d}"


def flag_for_human_review(
    employee_id: str, request: str, reason: str
) -> dict[str, Any]:
    """Escalate a request and return a review ticket id."""
    tickets: list[ReviewTicket] = _load_reviews()

    ticket = ReviewTicket(
        review_ticket_id=_next_review_id(tickets),
        employee_id=employee_id,
        request=request,
        reason=reason,
        status=ReviewStatus.OPEN
    )
    tickets.append(ticket)

    saved: list[dict[str, Any]] = []
    for row in tickets:
        saved.append(row.model_dump())
    reviews.save({"tickets": saved})
    return {"review_ticket_id": ticket.review_ticket_id}
