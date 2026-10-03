"""Interactive runner: one equipment request through plan, ReAct, reflect, flag."""

from __future__ import annotations

import asyncio
import re

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from client import server_params
from config import Settings
from generation.ollama import OllamaAdapter
from host import build_plan_prompt, run_react

settings = Settings.from_env()

EMPLOYEE_ID = re.compile(r"^E-\d{4}$")


def print_decision(result: dict) -> None:
    print("\n=== decision ===")
    print(f"Final Answer: {result['final']}")
    print(f"Rationale: {result['rationale']}")
    if result["flagged"]:
        print(f"review_ticket_id: {result['review_ticket_id']}")
    print()


def _ask(label: str) -> str | None:
    try:
        value = input(f"{label}: ").strip()
    except EOFError:
        return None
    if value.lower() == "quit":
        return None
    return value


def read_request() -> dict | None:
    """Prompt until employee_id, item, and reason are valid. None means quit."""
    while True:
        employee_id = _ask("employee_id")
        if employee_id is None:
            return None
        if EMPLOYEE_ID.fullmatch(employee_id):
            break
        print("employee_id must match E- followed by 4 digits, e.g. E-1003.")

    while True:
        item = _ask("item")
        if item is None:
            return None
        if item:
            break
        print("item must not be empty.")

    while True:
        reason = _ask("reason")
        if reason is None:
            return None
        if reason:
            break
        print("reason must not be empty.")

    return {
        "label": "cli-request",
        "employee_id": employee_id,
        "item": item,
        "reason": reason,
    }


async def loop() -> None:
    """Reuse one model and MCP session until the user types quit."""
    adapter = OllamaAdapter(settings.generation_model, settings.ollama_host)
    async with (
        stdio_client(server_params()) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        while True:
            request = read_request()
            if request is None:
                print("bye")
                break
            print(
                f"\n=== {request['employee_id']} {request['item']} ==="
            )
            plan = adapter.generate(build_plan_prompt(listed, request))
            print(plan)
            print("--- react ---")
            result = await run_react(
                adapter, session, listed, request, plan
            )
            print_decision(result)


def main() -> None:
    print("Type quit at any prompt to exit.")
    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()