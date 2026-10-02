"""Host: one MCP session, list tools, one hardcoded lookup."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from client import server_params
from generation.ollama import OllamaAdapter
from client import call_tool, server_params
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"

MAX_TURNS = 10

REQUESTS = [
    # --- 5 allow (eligible true) ---
    {
        "label": "allow-manager-second-monitor",
        "employee_id": "E-1003",
        "item": "second monitor",
        "reason": "need an extra screen for design reviews",
    },
    {
        "label": "allow-new-hire-laptop",
        "employee_id": "E-1005",
        "item": "laptop",
        "reason": "starting Monday, need a laptop",
    },
    {
        "label": "allow-retired-monitor",
        "employee_id": "E-1006",
        "item": "monitor",
        "reason": "old panel is retired, need one on the desk",
    },
    {
        "label": "allow-laptop-refresh-due",
        "employee_id": "E-1002",
        "item": "laptop",
        "reason": "current laptop is past refresh",
    },
    {
        "label": "allow-first-monitor",
        "employee_id": "E-1002",
        "item": "monitor",
        "reason": "no external display on file",
    },
    # --- 5 deny (eligible false, facts complete) ---
    {
        "label": "deny-employee-second-monitor",
        "employee_id": "E-1001",
        "item": "second monitor",
        "reason": "need an extra screen for design work",
    },
    {
        "label": "deny-laptop-too-new",
        "employee_id": "E-1001",
        "item": "laptop",
        "reason": "want a newer laptop",
    },
    {
        "label": "deny-headset-too-new",
        "employee_id": "E-1007",
        "item": "headset",
        "reason": "want a nicer headset",
    },
    {
        "label": "deny-manager-at-monitor-cap",
        "employee_id": "E-1004",
        "item": "third monitor",
        "reason": "want another screen",
    },
    {
        "label": "deny-second-laptop-too-new",
        "employee_id": "E-1001",
        "item": "second laptop",
        "reason": "need a travel laptop",
    },
    # --- 10 escalate (eligible null) ---
    {
        "label": "escalate-duplicate-id",
        "employee_id": "E-1011",
        "item": "laptop",
        "reason": "current laptop is slow",
    },
    {
        "label": "escalate-unknown-id",
        "employee_id": "E-9999",
        "item": "laptop",
        "reason": "new hire kit",
    },
    {
        "label": "escalate-contractor",
        "employee_id": "E-1009",
        "item": "monitor",
        "reason": "no external display",
    },
    {
        "label": "escalate-unmapped-desk",
        "employee_id": "E-1001",
        "item": "standing desk",
        "reason": "back pain",
    },
    {
        "label": "escalate-unmapped-gpu",
        "employee_id": "E-1002",
        "item": "GPU",
        "reason": "video work",
    },
    {
        "label": "escalate-unmapped-stipend",
        "employee_id": "E-1003",
        "item": "office stipend",
        "reason": "buy my own gear",
    },
    {
        "label": "escalate-unmapped-setup",
        "employee_id": "E-1005",
        "item": "full setup",
        "reason": "whatever the standard kit is",
    },
    {
        "label": "escalate-incomplete-date",
        "employee_id": "E-1008",
        "item": "laptop",
        "reason": "replace current laptop",
    },
    {
        "label": "escalate-incomplete-status",
        "employee_id": "E-1010",
        "item": "keyboard",
        "reason": "keys sticking",
    },
    {
        "label": "escalate-mixed",
        "employee_id": "E-1001",
        "item": "laptop and monitor",
        "reason": "refresh both",
    },
]

PROMPTS = Path(__file__).resolve().parent / "prompts"


def format_tools(listed, used: set[str] | None = None) -> str:
    """Render remaining MCP tools for the prompt."""
    lines = []
    for tool in listed.tools:
        if used and tool.name in used:
            continue
        props = (tool.input_schema or {}).get("properties") or {}
        params = ", ".join(
            f"{name}: {spec.get('type', 'string')}"
            for name, spec in props.items()
        )
        lines.append(f"- {tool.name}: {tool.description}\n  parameters: {params}")
    return "\n".join(lines) or "(none; write Final Answer)"


def format_observation(data: object) -> str:
    """Turn a tool result into key/value lines for the scratchpad."""
    if data is None:
        return "null"
    if isinstance(data, dict) and set(data) == {"result"}:
        return format_observation(data["result"])
    if isinstance(data, list):
        if not data:
            return "(empty)"
        if len(data) == 1:
            return format_observation(data[0])
        return "\n".join(
            f"record {i}:\n{format_observation(item)}\n"
            for i, item in enumerate(data, 1)
        )
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{key}:\n{format_observation(value)}")
            elif value is None:
                lines.append(f"{key}: null")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    return str(data)


def fill_prompt(template: str, **values: str) -> str:
    """Replace ``{{key}}`` in ``template`` with each keyword argument."""
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def build_plan_prompt(listed, request: dict) -> str:
    """Fill ``plan.v1.md`` with this request and the listed tools."""
    return fill_prompt(
        (PROMPTS / "plan.v1.md").read_text(),
        employee_id=request["employee_id"],
        item=request["item"],
        reason=request["reason"],
        tools=format_tools(listed),
    )


def build_react_prompt(
    listed, request: dict, plan: str, scratchpad: str, used: set[str]
) -> str:
    """Fill ``react.v2.md`` with the plan, request, remaining tools, and trace."""
    return fill_prompt(
        (PROMPTS / "react.v2.md").read_text(),
        plan=plan,
        employee_id=request["employee_id"],
        item=request["item"],
        reason=request["reason"],
        tools=format_tools(listed, used),
        scratchpad=scratchpad,
    )


def parse_action(text: str, listed) -> tuple[str, dict]:
    """Read tool name plus args from Action Input or from Action: name(...)."""
    name = ""
    call = ""
    raw = ""
    for line in text.splitlines():
        if line.startswith("Action Input:"):
            raw = line.split(":", 1)[1].strip()
        elif line.startswith("Action:"):
            call = line.split(":", 1)[1].strip()
            name = call.split("(")[0].strip()
    args: dict = {}
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            args = parsed
    if not args and "(" in call and call.endswith(")"):
        inner = call[call.find("(") + 1 : -1].strip()
        if inner.startswith("{"):
            args = json.loads(inner)
        elif inner:
            values = json.loads(f"[{inner}]")
            keys = []
            for tool in listed.tools:
                if tool.name == name:
                    keys = list((tool.input_schema or {}).get("properties") or {})
                    break
            args = dict(zip(keys, values))
    return name, args


def one_turn(text: str) -> str:
    """Keep one Thought plus Action/Action Input, or Final Answer and Rationale."""
    text = text.split("\nThought:", 1)[0]
    lines = text.splitlines()
    kept = []
    for i, line in enumerate(lines):
        kept.append(line)
        if line.startswith("Action Input:"):
            break
        if line.startswith("Action:"):
            if i + 1 < len(lines) and lines[i + 1].startswith("Action Input:"):
                kept.append(lines[i + 1])
            break
    return "\n".join(kept).strip()


def parse_final(text: str) -> tuple[str, str]:
    """Pull Final Answer and Rationale from a turn."""
    answer = ""
    rationale = ""
    for line in text.splitlines():
        if line.startswith("Final Answer:"):
            answer = line.split(":", 1)[1].strip().lower()
        elif line.startswith("Rationale:"):
            rationale = line.split(":", 1)[1].strip()
    return answer, rationale


def expected_of(request: dict) -> str:
    """allow / deny / escalate from label prefix."""
    label = request["label"]
    if label.startswith("allow"):
        return "allow"
    if label.startswith("deny"):
        return "deny"
    return "escalate"

    
async def run_react(adapter, session, listed, request: dict, plan: str) -> dict:
    """Thought -> Action -> Observation until Final Answer or MAX_TURNS."""
    scratchpad = ""
    used: set[str] = set()
    final = ""
    steps: list[dict] = []
    ticket = ""
    allowed = {t.name for t in listed.tools}

    for step in range(1, MAX_TURNS + 1):
        print(f"--- step {step} ---")
        turn = one_turn(
            adapter.generate(build_react_prompt(listed, request, plan, scratchpad, used))
        )
        print(turn)
        record: dict = {
            "step": step,
            "turn": turn,
            "action": None,
            "args": {},
            "tool_ran": False,
            "observation": None,
        }

        if "Final Answer:" in turn and scratchpad:
            final = turn
            steps.append(record)
            break

        name, args = parse_action(turn, listed)
        if name:
            name = name.split()[0]
        record["action"] = name
        record["args"] = args

        if not name:
            observation = "no Action in this turn"
        elif name in used:
            observation = (
                f"{name} was already called. Use that Observation in the Trace. "
                "Do not call it again."
            )
        elif name not in allowed:
            observation = (
                "unknown tool; use one of: "
                f"{', '.join(sorted(allowed - used)) or 'Final Answer'}"
            )
        else:
            action_result = await call_tool(session, name, args)
            observation = format_observation(action_result)
            used.add(name)
            record["tool_ran"] = True
            if name == "flag_for_human_review" and "review_ticket_id:" in observation:
                ticket = (
                    observation.split("review_ticket_id:", 1)[1]
                    .strip()
                    .splitlines()[0]
                    .strip()
                )

        record["observation"] = observation
        print(f"Observation: {observation}")
        scratchpad += f"{turn}\nObservation: {observation}\n"
        steps.append(record)
        if not name:
            break

    if not final:
        print("--- decide ---")
        all_names = {t.name for t in listed.tools}
        scratchpad += (
            "Observation: no more tool steps. Write Thought, Final Answer, "
            "and Rationale from the Trace. Do not write Action.\n"
        )
        turn = adapter.generate(
            build_react_prompt(listed, request, plan, scratchpad, all_names)
        )
        print(turn)
        final = turn
        steps.append(
            {
                "step": "decide",
                "turn": turn,
                "action": None,
                "args": {},
                "tool_ran": False,
                "observation": None,
            }
        )

    answer, rationale = parse_final(final)
    expected = expected_of(request)
    flagged = "flag_for_human_review" in used
    ok = answer == expected and (expected != "escalate" or flagged)
    return {
        "label": request["label"],
        "employee_id": request["employee_id"],
        "item": request["item"],
        "reason": request["reason"],
        "plan": plan,
        "expected": expected,
        "final": answer,
        "rationale": rationale,
        "flagged": flagged,
        "review_ticket_id": ticket or None,
        "ok": ok,
        "steps": steps,
    }


async def main() -> None:
    """Connect to the equipment server, run each request, write runs/."""
    adapter = OllamaAdapter("qwen3:8b", "http://host.docker.internal:11434")
    async with (
        stdio_client(server_params()) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        results = []
        for request in REQUESTS:
            print(
                f"\n=== {request['label']} "
                f"{request['employee_id']} {request['item']} ==="
            )
            plan = adapter.generate(build_plan_prompt(listed, request))
            print(plan)
            print("--- react ---")
            results.append(
                await run_react(adapter, session, listed, request, plan)
            )

    RUNS.mkdir(parents=True, exist_ok=True)
    path = RUNS / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ.json")
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {path}")
    print("ok:", sum(1 for row in results if row["ok"]), "/", len(results))


if __name__ == "__main__":
    asyncio.run(main())
