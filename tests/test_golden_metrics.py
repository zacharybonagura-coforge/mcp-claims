"""Live golden eval: run the host, then score the temp JSON against golden."""

from __future__ import annotations

import asyncio

import httpx
import pytest

import host
from config import Settings
from score_run import failed, score_run

pytestmark = pytest.mark.integration


OLLAMA = Settings.from_env().ollama_host

GOLDEN_CASES = 15

MIN_DECISION = 1.00
MIN_TOOL_ORDER = 1.00
MIN_STEPS = 0.80
MIN_ELIGIBLE = 1.00
MIN_MAX_STEPS = 1.00
MIN_REACT_FLAG = 1.00


def _ollama_up() -> bool:
    try:
        response = httpx.get(f"{OLLAMA}/api/tags", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.is_success


@pytest.fixture(scope="module")
def scored(tmp_path_factory) -> dict:
    if not _ollama_up():
        pytest.skip(f"Ollama is not reachable at {OLLAMA}")
    out = tmp_path_factory.mktemp("eval-run")
    previous = host.RUNS
    host.RUNS = out
    try:
        asyncio.run(host.main())
        written = list(out.glob("*.json"))
        assert written, f"host wrote no JSON under {out}"
        report = score_run(written[0])
        assert len(report["cases"]) >= GOLDEN_CASES
        return report
    finally:
        host.RUNS = previous


def test_decision_accuracy(scored: dict) -> None:
    missed = failed(scored["cases"], "decision_ok")
    assert scored["decision_accuracy"] >= MIN_DECISION, (
        f"decision={scored['decision_accuracy']:.2f} failed={missed}"
    )


def test_tool_order_accuracy(scored: dict) -> None:
    missed = failed(scored["cases"], "order_ok")
    assert scored["tool_order_accuracy"] >= MIN_TOOL_ORDER, (
        f"tool_order={scored['tool_order_accuracy']:.2f} failed={missed}"
    )


def test_step_count_accuracy(scored: dict) -> None:
    missed = failed(scored["cases"], "steps_ok")
    assert scored["step_count_accuracy"] >= MIN_STEPS, (
        f"steps={scored['step_count_accuracy']:.2f} failed={missed}"
    )


def test_eligible_accuracy(scored: dict) -> None:
    missed = failed(scored["cases"], "eligible_ok")
    assert scored["eligible_accuracy"] >= MIN_ELIGIBLE, (
        f"eligible={scored['eligible_accuracy']:.2f} failed={missed}"
    )


def test_max_steps_accuracy(scored: dict) -> None:
    missed = failed(scored["cases"], "max_steps_ok")
    assert scored["max_steps_accuracy"] >= MIN_MAX_STEPS, (
        f"max_steps={scored['max_steps_accuracy']:.2f} failed={missed}"
    )


def test_no_premature_flag(scored: dict) -> None:
    missed = failed(scored["cases"], "react_flag_ok")
    assert scored["react_flag_accuracy"] >= MIN_REACT_FLAG, (
        f"premature_flag={scored['react_flag_accuracy']:.2f} failed={missed}"
    )