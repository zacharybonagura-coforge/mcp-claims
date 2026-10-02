"""Score one host run against data/golden/golden.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "golden.json"


def react_steps(row: dict) -> list[dict]:
    """Integer ReAct turns only. Skip reflect, flag, and max-steps."""
    return [step for step in row.get("steps") or [] if isinstance(step.get("step"), int)]


def tool_order(row: dict) -> list[str]:
    """Tools that actually ran, in order."""
    return [
        step["action"]
        for step in react_steps(row)
        if step.get("tool_ran") and step.get("action")
    ]


def parse_final(text: str) -> str:
    """First word after Final Answer, or empty."""
    for line in (text or "").splitlines():
        if line.startswith("Final Answer:"):
            return line.split(":", 1)[1].strip().lower().split()[0]
    return ""


def parse_eligible(observation: str):
    """eligible value from a tool Observation, or 'missing'."""
    for line in (observation or "").splitlines():
        if line.startswith("eligible:"):
            raw = line.split(":", 1)[1].strip().lower()
            if raw == "true":
                return True
            if raw == "false":
                return False
            if raw == "null":
                return None
    return "missing"


def eligibility_observation(row: dict) -> str:
    """Observation from the eligibility tool, if it ran."""
    for step in react_steps(row):
        action = step.get("action") or ""
        if step.get("tool_ran") and "eligib" in action:
            return step.get("observation") or ""
    return ""


def hit_max_steps(row: dict) -> bool:
    """True when the host used the max-steps prompt."""
    return any(step.get("step") == "max-steps" for step in row.get("steps") or [])


def reflect_pair(row: dict) -> tuple[str, str]:
    """Draft Final Answer and reflected Final Answer."""
    for step in row.get("steps") or []:
        if step.get("step") == "reflect":
            return parse_final(step.get("draft") or ""), parse_final(step.get("turn") or "")
    return parse_final(row.get("final") or ""), parse_final(row.get("final") or "")


def react_opened_ticket(row: dict) -> bool:
    """True when a review ticket appears before the host flag step."""
    return any(
        "review_ticket_id:" in (step.get("observation") or "")
        for step in react_steps(row)
    )


def score_row(row: dict, case: dict, gold: dict) -> dict:
    """Compare one run row to its golden case."""
    order = tool_order(row)
    steps = len(react_steps(row))
    observation = eligibility_observation(row)
    eligible = parse_eligible(observation)
    detail = case["expected_detail"]
    used_max = hit_max_steps(row)
    draft, reflected = reflect_pair(row)
    reflect_changed = bool(draft and reflected and draft != reflected)

    decision_ok = (
        row.get("final") == case["expected"]
        and bool(row.get("flagged")) == bool(case["expected_flagged"])
    )
    order_ok = order == gold["react_tool_order"]
    steps_ok = steps == gold["react_steps"]
    eligible_ok = eligible == case["expected_eligible"]
    max_steps_ok = used_max == gold["max_steps"]
    reflect_ok = reflect_changed == gold["expected_reflect_changed"]
    react_flag_ok = not react_opened_ticket(row)
    return {
        "label": case["label"],
        "expected": case["expected"],
        "final": row.get("final"),
        "flagged": bool(row.get("flagged")),
        "tool_order": order,
        "react_steps": steps,
        "eligible": eligible,
        "detail": detail,
        "max_steps": used_max,
        "draft": draft,
        "reflected": reflected,
        "reflect_changed": reflect_changed,
        "decision_ok": decision_ok,
        "order_ok": order_ok,
        "steps_ok": steps_ok,
        "eligible_ok": eligible_ok,
        "max_steps_ok": max_steps_ok,
        "reflect_ok": reflect_ok,
        "react_flag_ok": react_flag_ok,
    }


def missing_row(case: dict) -> dict:
    """Golden case that is not in the run file."""
    return {
        "label": case["label"],
        "expected": case["expected"],
        "final": None,
        "flagged": False,
        "tool_order": [],
        "react_steps": 0,
        "eligible": "missing",
        "detail": case["expected_detail"],
        "max_steps": False,
        "draft": "",
        "reflected": "",
        "reflect_changed": False,
        "decision_ok": False,
        "order_ok": False,
        "steps_ok": False,
        "eligible_ok": False,
        "max_steps_ok": False,
        "reflect_ok": False,
        "react_flag_ok": False,
        "missing": True,
    }


def score_run(run_path: Path) -> dict:
    """Load golden + run and score every golden case."""
    gold = json.loads(GOLDEN.read_text())
    rows = {row["label"]: row for row in json.loads(run_path.read_text())}
    cases = []
    for case in gold["cases"]:
        row = rows.get(case["label"])
        cases.append(missing_row(case) if row is None else score_row(row, case, gold))

    n = len(cases) or 1

    def rate(key: str) -> float:
        return sum(c[key] for c in cases) / n

    return {
        "run": str(run_path),
        "decision_accuracy": rate("decision_ok"),
        "tool_order_accuracy": rate("order_ok"),
        "step_count_accuracy": rate("steps_ok"),
        "eligible_accuracy": rate("eligible_ok"),
        "max_steps_accuracy": rate("max_steps_ok"),
        "reflect_accuracy": rate("reflect_ok"),
        "react_flag_accuracy": rate("react_flag_ok"),
        "cases": cases,
    }


def failed(cases: list[dict], key: str) -> str:
    """Comma-separated labels that failed one check."""
    return ", ".join(c["label"] for c in cases if not c[key]) or "none"


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 src/score_run.py runs/YYYYMMDDTHHMMSSZ.json", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.is_file():
        path = ROOT / path
    report = score_run(path)
    print(json.dumps(report, indent=2))
    print(
        "decision:",
        f"{report['decision_accuracy']:.0%} |",
        "tool_order:",
        f"{report['tool_order_accuracy']:.0%} |",
        "steps:",
        f"{report['step_count_accuracy']:.0%} |",
        "eligible:",
        f"{report['eligible_accuracy']:.0%} |",
        "max_steps:",
        f"{report['max_steps_accuracy']:.0%} |",
        "reflect stayed same:",
        f"{report['reflect_accuracy']:.0%} |",
        "premature flag:",
        f"{report['react_flag_accuracy']:.0%} |",
    )
    cases = report["cases"]
    print("failed decision:", failed(cases, "decision_ok"))
    print("failed tool order:", failed(cases, "order_ok"))
    print("failed steps:", failed(cases, "steps_ok"))
    print("failed eligible:", failed(cases, "eligible_ok"))
    print("failed max_steps:", failed(cases, "max_steps_ok"))
    changed = [c["label"] for c in cases if c.get("reflect_changed")]
    print("reflect changed final answer:", ", ".join(changed) or "none")
    print("failed premature flag:", failed(cases, "react_flag_ok"))

if __name__ == "__main__":
    main()