"""Minimal MCP spike: one tool over stdio.

Proof that a client can list tools and call get_employee_info before the
full equipment server is built. Not the production process, which will be
server.py with the remaining tools.
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

from tools import get_employee_info as retrieve_employee_info

mcp = MCPServer(
    name="equipment-mini",
    instructions=(
        "MINIMAL SPIKE. Only get_employee_info is registered. "
        "Use it to confirm MCP connectivity; do not treat this as the full server."
    ),
)


@mcp.tool()
def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return role, hire_date, and equipment for this employee id."""
    return retrieve_employee_info(employee_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")