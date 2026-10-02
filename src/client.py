"""Spawn server.py over stdio and call equipment tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"


def server_params() -> StdioServerParameters:
    """stdio child: full equipment server with PYTHONPATH=src."""
    return StdioServerParameters(
        command=str(PYTHON),
        args=["src/server.py"],
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "src")},
    )


async def call_tool(
    session: ClientSession, name: str, arguments: dict[str, Any]
) -> Any:
    result = await session.call_tool(name, arguments)
    if result.is_error:
        raise SystemExit(f"tool error ({name}): {result.content}")
    return result.structured_content


async def main() -> None:
    async with (
        stdio_client(server_params()) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        names = [t.name for t in listed.tools]
        print("tools:", names)
        assert names == [
            "get_employee_info",
            "get_policy_limits",
            "check_request_eligibility",
            "flag_for_human_review",
        ], names

if __name__ == "__main__":
    asyncio.run(main())
