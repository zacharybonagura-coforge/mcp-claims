"""Spawn server_mini over stdio and call get_employee_info once."""

from __future__ import annotations

import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"


async def main() -> None:
    params = StdioServerParameters(
        command=str(PYTHON),
        args=["src/server_mini.py"],
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "src")},
    )

    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        names = [t.name for t in listed.tools]
        print("tools:", names)
        assert names == ["get_employee_info"], names

        result = await session.call_tool(
            "get_employee_info",
            {"employee_id": "E-1001"},
        )
        if result.is_error:
            raise SystemExit(f"tool error: {result.content}")

        print(result.structured_content)


if __name__ == "__main__":
    asyncio.run(main())