"""Unit tests for employee lookup. Fixtures live in tests/mock_data/, copied per test."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from store.json import JsonStore
from tools import get_employee_info

_MOCK_DIR = Path(__file__).parent / "mock_data"


@pytest.fixture(autouse=True)
def employee_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Copy mock JSON into tmp_path and bind tools.staff / tools.inventory."""
    shutil.copytree(_MOCK_DIR, tmp_path, dirs_exist_ok=True)
    monkeypatch.setattr("tools.staff", JsonStore(tmp_path / "staff.json"))
    monkeypatch.setattr(
        "tools.inventory", JsonStore(tmp_path / "inventory.json")
    )
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
