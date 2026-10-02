"""Host: one MCP session, list tools, one hardcoded lookup."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from client import server_params
from generation.ollama import OllamaAdapter

REQUESTS = [
    {
        "label": "allow",
        "employee_id": "E-1003",
        "item": "second monitor",
        "reason": "need an extra screen for design reviews",
    },
    {
        "label": "deny",
        "employee_id": "E-1001",
        "item": "second monitor",
        "reason": "need an extra screen for design work",
    },
    {
        "label": "ambiguous-identity",
        "employee_id": "E-1011",
        "item": "laptop",
        "reason": "current laptop is slow",
    },
    {
        "label": "ambiguous-policy-gap",
        "employee_id": "E-1009",
        "item": "monitor",
        "reason": "no external display",
    },
]

PROMPTS = Path(__file__).resolve().parent / "prompts"


def format_tools(listed) -> str:
    """Render MCP tools as name, description, and parameter JSON for the prompt."""
    lines = []
    for tool in listed.tools:
        schema = tool.input_schema or {}
        lines.append(
            f"- {tool.name}: {tool.description}\n"
            f"  parameters: {json.dumps(schema.get('properties', {}))}"
        )
    return "\n".join(lines)


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


async def main() -> None:
    """Connect to the equipment server and print a plan for each sample request."""
    adapter = OllamaAdapter("mistral:7b", "http://host.docker.internal:11434")
    async with (
        stdio_client(server_params()) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        for request in REQUESTS:
            print(f"\n=== {request['label']} {request['employee_id']} {request['item']} ===")
            plan = adapter.generate(build_plan_prompt(listed, request))
            print(plan)


if __name__ == "__main__":
    asyncio.run(main())
