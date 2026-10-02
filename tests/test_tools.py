"""Unit tests for python functions used as MCP tools

Fixtures live in tests/mock_data/ and are copied into tmp_path per test.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from models import ReviewStatus
from store.json import JsonStore
from tools import (
    check_request_eligibility,
    flag_for_human_review,
    get_employee_info,
    get_policy_limits,
)

_MOCK_DIR = Path(__file__).parent / "mock_data"


@pytest.fixture(autouse=True)
def employee_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Copy mock JSON into tmp_path and bind staff, inventory, and policies stores."""
    shutil.copytree(_MOCK_DIR, tmp_path, dirs_exist_ok=True)
    monkeypatch.setattr("tools.staff", JsonStore(tmp_path / "staff.json"))
    monkeypatch.setattr(
        "tools.inventory", JsonStore(tmp_path / "inventory.json")
    )
    monkeypatch.setattr("tools.policies", JsonStore(tmp_path / "policy_limits.json"))
    monkeypatch.setattr("tools.reviews", JsonStore(tmp_path / "reviews.json"))
    return tmp_path


def test_one_employee_with_equipment() -> None:
    result = get_employee_info("E-1")

    assert len(result) == 1
    assert result[0]["name"] == "Ada"
    assert result[0]["role"] == "employee"
    assert len(result[0]["equipment"]) == 2
    categories = [item["category"] for item in result[0]["equipment"]]
    assert categories == ["monitor", "laptop"]


def test_employee_with_no_assignments() -> None:
    result = get_employee_info("E-2")

    assert len(result) == 1
    assert result[0]["name"] == "Bea"
    assert result[0]["equipment"] == []


def test_unknown_employee_returns_empty() -> None:
    assert get_employee_info("E-9999") == []


def test_duplicate_employee_id_returns_both_rows() -> None:
    result = get_employee_info("E-DUP")

    assert len(result) == 2
    assert result[0]["name"] == "Casey"
    assert result[1]["name"] == "Casey (duplicate)"
    assert result[0]["equipment"] == []
    assert result[1]["equipment"] == []


def test_contractor_is_still_returned() -> None:
    result = get_employee_info("E-CONTRACTOR")

    assert len(result) == 1
    assert result[0]["role"] == "contractor"
    assert result[0]["equipment"] == []


def test_does_not_attach_other_employees_assignments() -> None:
    result = get_employee_info("E-1")

    assert len(result[0]["equipment"]) == 2
    for item in result[0]["equipment"]:
        assert item["employee_id"] == "E-1"


def test_incomplete_assignment_is_still_returned() -> None:
    result = get_employee_info("E-INCOMPLETE")

    assert len(result) == 1
    by_tag = {item["asset_tag"]: item for item in result[0]["equipment"]}
    assert "assigned_on" not in by_tag["LAP-X"]
    assert "status" not in by_tag["KBD-X"]


def test_missing_assignments_key_raises(tmp_path: Path) -> None:
    (tmp_path / "inventory.json").write_text("{}")

    with pytest.raises(KeyError):
        get_employee_info("E-1")


def test_employee_limits_include_happy_path_and_edges() -> None:
    result = get_policy_limits("employee")

    assert result["role"] == "employee"
    rules = [row["policy_rule"] for row in result["limits"] if "policy_rule" in row]
    assert "R-EMP-MON" in rules
    assert "R-EMP-MON-DUP" in rules
    assert "R-EMP-LAP" in rules
    assert "R-EMP-GPU" in rules
    assert "R-EMP-MOU-CASE" not in rules
    assert all(row["role"] == "employee" for row in result["limits"])


def test_employee_monitor_duplicate_rows() -> None:
    result = get_policy_limits("employee")
    monitors = [row for row in result["limits"] if row["category"] == "monitor"]

    assert len(monitors) == 2
    assert {row["policy_rule"] for row in monitors} == {
        "R-EMP-MON",
        "R-EMP-MON-DUP",
    }


def test_employee_incomplete_keyboard_row() -> None:
    result = get_policy_limits("employee")
    keyboards = [row for row in result["limits"] if row["category"] == "keyboard"]

    assert len(keyboards) == 1
    assert keyboards[0]["cap_active"] == 1
    assert "refresh_years" not in keyboards[0]
    assert "policy_rule" not in keyboards[0]


def test_employee_has_no_dock_row() -> None:
    result = get_policy_limits("employee")
    docks = [row for row in result["limits"] if row.get("category") == "dock"]

    assert docks == []


def test_manager_monitor_cap_differs_from_employee() -> None:
    employee = get_policy_limits("employee")
    manager = get_policy_limits("manager")

    emp_mon = next(r for r in employee["limits"] if r["policy_rule"] == "R-EMP-MON")
    mgr_mon = next(r for r in manager["limits"] if r["policy_rule"] == "R-MGR-MON")
    mgr_lap = next(r for r in manager["limits"] if r["policy_rule"] == "R-MGR-LAP")

    assert emp_mon["cap_active"] == 1
    assert mgr_mon["cap_active"] == 2
    assert mgr_lap["refresh_years"] == 2
    assert len(manager["limits"]) == 2


def test_contractor_has_no_limits() -> None:
    result = get_policy_limits("contractor")

    assert result["role"] == "contractor"
    assert result["limits"] == []


def test_intern_is_not_a_covered_role_but_has_a_row() -> None:
    result = get_policy_limits("intern")

    assert len(result["limits"]) == 1
    assert result["limits"][0]["policy_rule"] == "R-INT-HEAD"


def test_capitalized_employee_role_is_a_different_key() -> None:
    lower = get_policy_limits("employee")
    upper = get_policy_limits("Employee")

    assert "R-EMP-MOU-CASE" not in [
        row.get("policy_rule") for row in lower["limits"]
    ]
    assert len(upper["limits"]) == 1
    assert upper["limits"][0]["policy_rule"] == "R-EMP-MOU-CASE"


def test_missing_limits_key_raises(tmp_path: Path) -> None:
    (tmp_path / "policy_limits.json").write_text("{}")

    with pytest.raises(KeyError):
        get_policy_limits("employee")


def test_eligibility_under_cap_is_eligible() -> None:
    result = check_request_eligibility("E-2", "27 inch Monitor")

    assert result["eligible"] is True
    assert result["detail"] == "within_cap"
    assert result["category"] == "monitor"
    assert result["policy_rule"] == "R-MGR-MON"
    assert result["active"] == 0
    assert result["cap_active"] == 2


def test_eligibility_open_keyboard_slot() -> None:
    result = check_request_eligibility("E-1", "keyboard")

    assert result["eligible"] is True
    assert result["detail"] == "within_cap"
    assert result["category"] == "keyboard"
    assert result["policy_rule"] is None
    assert result["active"] == 0
    assert result["cap_active"] == 1


def test_eligibility_refresh_due_replaces_oldest_unit() -> None:
    result = check_request_eligibility("E-REFRESH", "laptop")

    assert result["eligible"] is True
    assert result["detail"] == "refresh_ok"
    assert result["policy_rule"] == "R-EMP-LAP"
    assert result["active"] == 2
    assert result["cap_active"] == 1
    assert result["replace_unit"]["asset_tag"] == "LAP-OLD"


def test_eligibility_retired_unit_does_not_count_toward_cap() -> None:
    result = check_request_eligibility("E-RETIRED", "monitor")

    assert result["eligible"] is True
    assert result["detail"] == "within_cap"
    assert result["active"] == 0
    assert result["cap_active"] == 1


def test_eligibility_at_cap_and_too_new_is_not_eligible() -> None:
    result = check_request_eligibility("E-1", "monitor")

    assert result["eligible"] is False
    assert result["detail"] == "refresh_too_soon"
    assert result["policy_rule"] == "R-EMP-MON"
    assert result["active"] == 1
    assert result["cap_active"] == 1
    assert "replace_unit" not in result


def test_eligibility_uses_first_duplicate_policy_row() -> None:
    result = check_request_eligibility("E-1", "monitor")

    assert result["policy_rule"] == "R-EMP-MON"


def test_eligibility_no_refresh_window_at_cap_is_not_eligible() -> None:
    result = check_request_eligibility("E-KBD", "keyboard")

    assert result["eligible"] is False
    assert result["detail"] == "refresh_too_soon"
    assert result["policy_rule"] is None


def test_eligibility_unknown_employee_is_identity() -> None:
    result = check_request_eligibility("E-9999", "laptop")

    assert result["eligible"] is None
    assert result["detail"] == "identity"


def test_eligibility_duplicate_employee_is_identity() -> None:
    result = check_request_eligibility("E-DUP", "laptop")

    assert result["eligible"] is None
    assert result["detail"] == "identity"


def test_eligibility_unmapped_item() -> None:
    result = check_request_eligibility("E-1", "gpu")

    assert result["eligible"] is None
    assert result["detail"] == "unmapped_item"
    assert "category" not in result


def test_eligibility_mixed_items_is_decline() -> None:
    result = check_request_eligibility("E-1", "laptop and monitor")

    assert result["eligible"] is False
    assert result["detail"] == "mixed_items"


def test_eligibility_contractor_has_policy_gap() -> None:
    result = check_request_eligibility("E-CONTRACTOR", "monitor")

    assert result["eligible"] is None
    assert result["detail"] == "policy_gap"
    assert result["category"] == "monitor"


def test_eligibility_employee_dock_is_policy_gap() -> None:
    result = check_request_eligibility("E-1", "dock")

    assert result["eligible"] is None
    assert result["detail"] == "policy_gap"


def test_eligibility_missing_status_is_incomplete() -> None:
    result = check_request_eligibility("E-INCOMPLETE", "keyboard")

    assert result["eligible"] is None
    assert result["detail"] == "incomplete_inventory"
    assert result["policy_rule"] is None


def test_eligibility_missing_assigned_on_is_incomplete() -> None:
    result = check_request_eligibility("E-INCOMPLETE", "laptop")

    assert result["eligible"] is None
    assert result["detail"] == "incomplete_inventory"
    assert result["policy_rule"] == "R-EMP-LAP"
    assert result["active"] == 1
    assert result["cap_active"] == 1


def test_eligibility_ignores_incomplete_units_in_other_categories() -> None:
    result = check_request_eligibility("E-INCOMPLETE", "monitor")

    assert result["eligible"] is True
    assert result["detail"] == "within_cap"


def test_eligibility_parse_error_is_ineligible(tmp_path: Path) -> None:
    (tmp_path / "staff.json").write_text(
        '{"staff":[{"employee_id":"E-1","name":"Ada","role":"employee",'
        '"hire_date":"2022-03-01","department":"Engineering","notes":"nope"}]}'
    )

    result = check_request_eligibility("E-1", "laptop")

    assert result["eligible"] is False
    assert result["detail"] == "parse_error"


def test_eligibility_missing_staff_key_still_raises(tmp_path: Path) -> None:
    (tmp_path / "staff.json").write_text("{}")

    with pytest.raises(KeyError):
        check_request_eligibility("E-1", "laptop")


def test_flag_first_ticket_is_persisted(tmp_path: Path) -> None:
    result = flag_for_human_review("E-1", "second monitor", "identity")

    assert result == {"review_ticket_id": "REV-0001"}
    payload = JsonStore(tmp_path / "reviews.json").load()
    assert payload["tickets"] == [
        {
            "review_ticket_id": "REV-0001",
            "employee_id": "E-1",
            "request": "second monitor",
            "reason": "identity",
            "status": ReviewStatus.OPEN
        }
    ]


def test_flag_second_ticket_increments_id(tmp_path: Path) -> None:
    first = flag_for_human_review("E-1", "laptop", "incomplete_inventory")
    second = flag_for_human_review("E-9999", "standing desk", "unmapped_item")

    assert first["review_ticket_id"] == "REV-0001"
    assert second["review_ticket_id"] == "REV-0002"
    payload = JsonStore(tmp_path / "reviews.json").load()
    assert len(payload["tickets"]) == 2
    assert payload["tickets"][1]["employee_id"] == "E-9999"
    assert payload["tickets"][1]["reason"] == "unmapped_item"


def test_flag_continues_from_highest_existing_id(tmp_path: Path) -> None:
    (tmp_path / "reviews.json").write_text(
        '{"tickets":['
        '{"review_ticket_id":"REV-0001","employee_id":"E-1","request":"a","reason":"x"},'
        '{"review_ticket_id":"REV-0005","employee_id":"E-2","request":"b","reason":"y"}'
        "]}"
    )

    result = flag_for_human_review("E-2", "monitor", "policy_gap")

    assert result["review_ticket_id"] == "REV-0006"


def test_flag_skips_non_numeric_ticket_ids(tmp_path: Path) -> None:
    (tmp_path / "reviews.json").write_text(
        '{"tickets":['
        '{"review_ticket_id":"REV-ABC","employee_id":"E-1","request":"a","reason":"x"}'
        "]}"
    )

    result = flag_for_human_review("E-1", "laptop", "identity")

    assert result["review_ticket_id"] == "REV-0001"


def test_flag_missing_tickets_key_raises(tmp_path: Path) -> None:
    (tmp_path / "reviews.json").write_text("{}")

    with pytest.raises(KeyError):
        flag_for_human_review("E-1", "laptop", "identity")


def test_flag_extra_field_on_existing_ticket_raises(tmp_path: Path) -> None:
    (tmp_path / "reviews.json").write_text(
        '{"tickets":['
        '{"review_ticket_id":"REV-0001","employee_id":"E-1",'
        '"request":"a","reason":"x","notes":"nope"}'
        "]}"
    )

    with pytest.raises(ValidationError):
        flag_for_human_review("E-1", "laptop", "identity")
