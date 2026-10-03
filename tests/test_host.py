"""Unit tests for the ReAct host helpers and loop."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import host


def listed(*names: str) -> SimpleNamespace:
    tools = []
    for name in names:
        tools.append(
            SimpleNamespace(
                name=name,
                description=f"{name} tool",
                input_schema={"properties": {"employee_id": {"type": "string"}}},
            )
        )
    return SimpleNamespace(tools=tools)


REQUEST = {
    "label": "allow-x",
    "employee_id": "E-1003",
    "item": "monitor",
    "reason": "need a screen",
}


class ScriptedAdapter:
    def __init__(self, turns: list[str]) -> None:
        self.turns = list(turns)

    def generate(self, prompt: str) -> str:
        return self.turns.pop(0)


def test_format_tools_renders_and_skips_used() -> None:
    text = host.format_tools(listed("get_employee_info", "get_policy_limits"))
    assert "get_employee_info" in text
    assert "employee_id: string" in text
    leftover = host.format_tools(
        listed("get_employee_info", "get_policy_limits"),
        {"get_employee_info"},
    )
    assert "get_employee_info" not in leftover
    assert "get_policy_limits" in leftover


def test_format_tools_empty_when_all_used() -> None:
    assert host.format_tools(listed("only"), {"only"}) == "(none; write Final Answer)"


def test_format_observation_shapes() -> None:
    assert host.format_observation(None) == "null"
    assert host.format_observation({"result": {"eligible": True}}) == "eligible: True"
    assert host.format_observation([]) == "(empty)"
    assert host.format_observation([{"a": 1}]) == "a: 1"
    records = host.format_observation([{"a": 1}, {"b": None}])
    assert "record 1:" in records
    assert "b: null" in records
    nested = host.format_observation({"limits": [{"role": "employee"}]})
    assert "limits:" in nested
    assert host.format_observation(3) == "3"


def test_fill_prompt_and_ticket_id() -> None:
    assert host.fill_prompt("hi {{name}}", name="Ada") == "hi Ada"
    assert host.ticket_id("nope") == ""
    assert host.ticket_id("review_ticket_id: REV-0009\nmore") == "REV-0009"


def test_parse_action_happy_and_failures() -> None:
    tools = listed("get_employee_info")
    text = (
        "Thought: go\n"
        "Action: get_employee_info\n"
        'Action Input: {"employee_id": "E-1"}'
    )
    name, args = host.parse_action(text, tools)
    assert name == "get_employee_info"
    assert args == {"employee_id": "E-1"}

    assert host.parse_action("Action: nope\nAction Input: {}", tools) == ("nope", {})
    assert host.parse_action(
        "Action: get_employee_info\nAction Input: not-json", tools
    ) == ("get_employee_info", {})
    assert host.parse_action(
        "Action: get_employee_info\nAction Input: [1]", tools
    ) == ("get_employee_info", {})


def test_one_turn_keeps_one_action_or_strips_extra_thought() -> None:
    kept = host.one_turn(
        "Thought: a\nAction: get_employee_info\n"
        'Action Input: {"employee_id": "E-1"}\nThought: extra'
    )
    assert "Thought: extra" not in kept
    assert "Action Input:" in kept
    assert host.one_turn("Thought: only\nAction: get_employee_info").endswith(
        "Action: get_employee_info"
    )


def test_parse_final_and_expected_of() -> None:
    assert host.parse_final(
        "Final Answer: Allow\nRationale: under cap"
    ) == ("allow", "under cap")
    assert host.expected_of({"label": "allow-x"}) == "allow"
    assert host.expected_of({"label": "deny-x"}) == "deny"
    assert host.expected_of({"label": "escalate-x"}) == "escalate"


def test_build_prompts_fill_request() -> None:
    tools = listed("get_employee_info")
    plan = host.build_plan_prompt(tools, REQUEST)
    assert "E-1003" in plan
    react = host.build_react_prompt(tools, REQUEST, "plan text", "trace", set())
    assert "plan text" in react
    assert "trace" in react
    reflect = host.build_reflect_prompt(REQUEST, "draft", "trace")
    assert "draft" in reflect
    flag = host.build_flag_prompt(tools, REQUEST, "why")
    assert "why" in flag


def test_run_react_allow_happy_path() -> None:
    tools = listed(
        "get_employee_info", "get_policy_limits", "check_request_eligibility"
    )
    adapter = ScriptedAdapter(
        [
            (
                "Thought: e\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            (
                "Thought: p\nAction: get_policy_limits\n"
                'Action Input: {"role": "manager"}'
            ),
            (
                "Thought: c\nAction: check_request_eligibility\n"
                'Action Input: {"employee_id": "E-1003", "item": "monitor"}'
            ),
            "Thought: done\nFinal Answer: allow\nRationale: under cap",
            "Thought: eligible is true\nFinal Answer: allow\nRationale: under cap",
        ]
    )
    session = AsyncMock()

    async def fake_call(session, name, args):
        return {"eligible": True} if "eligib" in name else {"ok": name}

    with patch("host.call_tool", side_effect=fake_call):
        result = asyncio.run(
            host.run_react(adapter, session, tools, REQUEST, "plan")
        )

    assert result["final"] == "allow"
    assert result["ok"] is True
    assert result["flagged"] is False
    assert [s["action"] for s in result["steps"] if s.get("tool_ran")] == [
        "get_employee_info",
        "get_policy_limits",
        "check_request_eligibility",
    ]


def test_run_react_no_action_goes_to_max_steps() -> None:
    tools = listed("get_employee_info")
    adapter = ScriptedAdapter(
        [
            "Thought: stuck",
            (
                "Thought: no decision after max steps\n"
                "Final Answer: escalate\nRationale: max_steps"
            ),
            "Thought: eligible is null\nFinal Answer: escalate\nRationale: max_steps",
            "Thought: flag\nAction: missing\nAction Input: {}",
        ]
    )
    result = asyncio.run(
        host.run_react(adapter, AsyncMock(), tools, REQUEST, "plan")
    )
    assert result["steps"][0]["observation"] == "no Action in this turn"
    assert any(s["step"] == "max-steps" for s in result["steps"])
    assert result["final"] == "escalate"


def test_run_react_unknown_and_repeat_tool() -> None:
    tools = listed("get_employee_info")
    adapter = ScriptedAdapter(
        [
            "Thought: a\nAction: nope\nAction Input: {}",
            (
                "Thought: b\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            (
                "Thought: c\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            "Thought: d\nFinal Answer: allow\nRationale: under cap",
            "Thought: ok\nFinal Answer: allow\nRationale: under cap",
        ]
    )

    async def fake_call(session, name, args):
        return {"employee_id": "E-1003"}

    with patch("host.call_tool", side_effect=fake_call):
        result = asyncio.run(
            host.run_react(adapter, AsyncMock(), tools, REQUEST, "plan")
        )

    notes = [s["observation"] for s in result["steps"] if s.get("observation")]
    assert any(o and o.startswith("unknown tool") for o in notes)
    assert any(o and "already called" in o for o in notes)


def test_run_react_escalate_flags_and_appends_ticket() -> None:
    req = {**REQUEST, "label": "escalate-x"}
    tools = listed("get_employee_info", "flag_for_human_review")
    adapter = ScriptedAdapter(
        [
            (
                "Thought: a\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            "Thought: e\nFinal Answer: escalate\nRationale: unknown",
            "Thought: r\nFinal Answer: escalate\nRationale: unknown",
            (
                "Thought: f\nAction: flag_for_human_review\n"
                'Action Input: {"employee_id": "E-1003", "request": "monitor", '
                '"reason": "unknown"}'
            ),
        ]
    )

    async def fake_call(session, name, args):
        if name == "flag_for_human_review":
            return {"review_ticket_id": "REV-0007"}
        return {"employee_id": "E-1003"}

    with patch("host.call_tool", side_effect=fake_call):
        result = asyncio.run(
            host.run_react(adapter, AsyncMock(), tools, req, "plan")
        )

    assert result["final"] == "escalate"
    assert result["flagged"] is True
    assert result["review_ticket_id"] == "REV-0007"
    assert "REV-0007" in result["rationale"]
    assert result["ok"] is True


def test_run_react_escalate_unknown_flag_tool() -> None:
    req = {**REQUEST, "label": "escalate-x"}
    tools = listed("get_employee_info")
    adapter = ScriptedAdapter(
        [
            (
                "Thought: a\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            "Thought: e\nFinal Answer: escalate\nRationale: unknown",
            "Thought: r\nFinal Answer: escalate\nRationale: unknown",
            "Thought: f\nAction: not_a_tool\nAction Input: {}",
        ]
    )

    async def fake_call(session, name, args):
        return {"employee_id": "E-1003"}

    with patch("host.call_tool", side_effect=fake_call):
        result = asyncio.run(
            host.run_react(adapter, AsyncMock(), tools, req, "plan")
        )

    flag = result["steps"][-1]
    assert flag["step"] == "flag"
    assert "unknown tool" in flag["observation"]
    assert result["flagged"] is False
    assert result["ok"] is False


def test_main_writes_run_file(tmp_path, monkeypatch) -> None:
    tools = listed("get_employee_info")
    adapter = ScriptedAdapter(
        [
            "plan",
            (
                "Thought: a\nAction: get_employee_info\n"
                'Action Input: {"employee_id": "E-1003"}'
            ),
            "Thought: d\nFinal Answer: allow\nRationale: under cap",
            "Thought: r\nFinal Answer: allow\nRationale: under cap",
        ]
    )
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=tools)
    stdio_cm = AsyncMock()
    stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
    stdio_cm.__aexit__.return_value = False
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = False

    monkeypatch.setattr(host, "REQUESTS", [REQUEST])
    monkeypatch.setattr(host, "RUNS", tmp_path)
    monkeypatch.setattr(host, "OllamaAdapter", lambda *a, **k: adapter)

    async def fake_call(session, name, args):
        return {"employee_id": "E-1003"}

    with (
        patch("host.stdio_client", return_value=stdio_cm),
        patch("host.ClientSession", return_value=session_cm),
        patch("host.call_tool", side_effect=fake_call),
    ):
        asyncio.run(host.main())

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload[0]["label"] == "allow-x"
    assert payload[0]["final"] == "allow"


def test_one_turn_stops_on_action_input_without_action() -> None:
    kept = host.one_turn("Thought: leftover\nAction Input: {\"employee_id\": \"E-1\"}\nmore")
    assert kept == 'Thought: leftover\nAction Input: {"employee_id": "E-1"}'
    assert "more" not in kept