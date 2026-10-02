"""Unit tests for scoring a host run against golden.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import score_run

GOLD = {
    "react_tool_order": [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ],
    "react_steps": 4,
    "max_steps": False,
    "expected_reflect_changed": False,
}

CASE = {
    "label": "allow-x",
    "expected": "allow",
    "expected_eligible": True,
    "expected_detail": "under cap",
    "expected_flagged": False,
}


def _tool(step: int, action: str, observation: str, ran: bool = True) -> dict:
    return {
        "step": step,
        "action": action,
        "tool_ran": ran,
        "observation": observation,
    }


def perfect_row(**overrides: object) -> dict:
    row = {
        "final": "allow",
        "flagged": False,
        "steps": [
            _tool(1, "get_employee_info", "role: manager"),
            _tool(2, "get_policy_limits", "role: manager"),
            _tool(3, "check_request_eligibility", "eligible: True\ndetail: under cap"),
            {
                "step": 4,
                "action": None,
                "tool_ran": False,
                "observation": None,
                "turn": "Final Answer: allow",
            },
            {
                "step": "reflect",
                "draft": "Final Answer: allow",
                "turn": "Final Answer: allow",
            },
            {
                "step": "flag",
                "observation": "review_ticket_id: REV-0001",
            },
        ],
    }
    row.update(overrides)
    return row


def test_parse_final_reads_first_word() -> None:
    assert score_run.parse_final("Final Answer: Allow now") == "allow"


def test_parse_final_empty_when_missing() -> None:
    assert score_run.parse_final("Thought: nope") == ""
    assert score_run.parse_final("") == ""


def test_parse_eligible_true_false_null() -> None:
    assert score_run.parse_eligible("eligible: True") is True
    assert score_run.parse_eligible("eligible: False") is False
    assert score_run.parse_eligible("eligible: null") is None


def test_parse_eligible_missing() -> None:
    assert score_run.parse_eligible("detail: under cap") == "missing"
    assert score_run.parse_eligible("") == "missing"


def test_react_steps_skips_named_phases() -> None:
    steps = score_run.react_steps(perfect_row())
    assert [s["step"] for s in steps] == [1, 2, 3, 4]


def test_tool_order_only_tools_that_ran() -> None:
    row = perfect_row()
    row["steps"].insert(
        3, _tool(3, "check_request_eligibility", "already called", ran=False)
    )
    assert score_run.tool_order(row) == GOLD["react_tool_order"]


def test_eligibility_observation_empty_when_tool_did_not_run() -> None:
    assert score_run.eligibility_observation({"steps": []}) == ""


def test_reflect_pair_falls_back_to_final() -> None:
    assert score_run.reflect_pair({"final": "Final Answer: deny"}) == ("deny", "deny")


def test_react_opened_ticket_ignores_host_flag_step() -> None:
    assert score_run.react_opened_ticket(perfect_row()) is False


def test_score_row_happy_path() -> None:
    result = score_run.score_row(perfect_row(), CASE, GOLD)

    assert result["decision_ok"] is True
    assert result["order_ok"] is True
    assert result["steps_ok"] is True
    assert result["eligible_ok"] is True
    assert result["max_steps_ok"] is True
    assert result["reflect_ok"] is True
    assert result["react_flag_ok"] is True
    assert result["eligible"] is True
    assert result["reflect_changed"] is False


def test_score_row_wrong_decision() -> None:
    result = score_run.score_row(perfect_row(final="deny"), CASE, GOLD)
    assert result["decision_ok"] is False


def test_score_row_wrong_tool_order() -> None:
    row = perfect_row()
    row["steps"][0]["action"] = "get_policy_limits"
    result = score_run.score_row(row, CASE, GOLD)
    assert result["order_ok"] is False


def test_score_row_extra_react_step() -> None:
    row = perfect_row()
    row["steps"].insert(3, _tool(99, "get_employee_info", "again", ran=False))
    result = score_run.score_row(row, CASE, GOLD)
    assert result["steps_ok"] is False
    assert result["react_steps"] == 5


def test_score_row_wrong_eligible() -> None:
    row = perfect_row()
    row["steps"][2]["observation"] = "eligible: False\ndetail: refresh window"
    result = score_run.score_row(row, CASE, GOLD)
    assert result["eligible_ok"] is False
    assert result["eligible"] is False


def test_score_row_max_steps() -> None:
    row = perfect_row()
    row["steps"].append({"step": "max-steps", "turn": "Final Answer: escalate"})
    result = score_run.score_row(row, CASE, GOLD)
    assert result["max_steps"] is True
    assert result["max_steps_ok"] is False


def test_score_row_reflect_changed() -> None:
    row = perfect_row()
    row["steps"][4]["draft"] = "Final Answer: deny"
    row["steps"][4]["turn"] = "Final Answer: allow"
    result = score_run.score_row(row, CASE, GOLD)
    assert result["reflect_changed"] is True
    assert result["reflect_ok"] is False


def test_score_row_premature_flag() -> None:
    row = perfect_row()
    row["steps"][2]["observation"] = (
        "eligible: True\nreview_ticket_id: REV-0001"
    )
    result = score_run.score_row(row, CASE, GOLD)
    assert result["react_flag_ok"] is False


def test_failed_lists_labels_or_none() -> None:
    assert score_run.failed([{"label": "a", "decision_ok": False}], "decision_ok") == "a"
    assert score_run.failed([{"label": "a", "decision_ok": True}], "decision_ok") == "none"


def test_score_run_scores_present_and_missing_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = {
        **GOLD,
        "cases": [
            CASE,
            {
                "label": "deny-y",
                "expected": "deny",
                "expected_eligible": False,
                "expected_detail": "refresh window",
                "expected_flagged": False,
            },
        ],
    }
    gold_path = tmp_path / "golden.json"
    gold_path.write_text(json.dumps(golden))
    monkeypatch.setattr(score_run, "GOLDEN", gold_path)

    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps([{**perfect_row(), "label": "allow-x"}]))

    report = score_run.score_run(run_path)

    by_label = {c["label"]: c for c in report["cases"]}
    assert by_label["allow-x"]["decision_ok"] is True
    assert by_label["deny-y"]["missing"] is True
    assert report["decision_accuracy"] == 0.5


def test_main_exits_without_run_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(score_run.sys, "argv", ["score_run.py"])
    with pytest.raises(SystemExit) as exc:
        score_run.main()
    assert exc.value.code == 2


def test_main_prints_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    golden = {**GOLD, "cases": [CASE]}
    gold_path = tmp_path / "golden.json"
    gold_path.write_text(json.dumps(golden))
    monkeypatch.setattr(score_run, "GOLDEN", gold_path)

    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps([{**perfect_row(), "label": "allow-x"}]))
    monkeypatch.setattr(score_run.sys, "argv", ["score_run.py", str(run_path)])

    score_run.main()
    out = capsys.readouterr().out
    assert "decision:" in out
    assert "failed decision: none" in out
    assert "failed premature flag: none" in out


def test_main_resolves_relative_path_against_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "golden.json").write_text(json.dumps({**GOLD, "cases": [CASE]}))
    (tmp_path / "rel.json").write_text(
        json.dumps([{**perfect_row(), "label": "allow-x"}])
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(score_run, "GOLDEN", tmp_path / "golden.json")
    monkeypatch.setattr(score_run, "ROOT", tmp_path)
    monkeypatch.setattr(score_run.sys, "argv", ["score_run.py", "rel.json"])
    monkeypatch.chdir(elsewhere)

    score_run.main()
    assert "decision:" in capsys.readouterr().out
