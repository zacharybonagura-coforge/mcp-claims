"""MCP process: expose the four equipment tools over stdio."""

from typing import Any

from mcp.server.mcpserver import MCPServer

from tools import check_request_eligibility as run_eligibility_check
from tools import flag_for_human_review as record_human_review
from tools import get_employee_info as retrieve_employee_info
from tools import get_policy_limits as retrieve_policy_limits

mcp = MCPServer(
    name="equipment",
    instructions=(
        "IT equipment request tools. Use get_employee_info for role, hire_date, "
        "and equipment on file; get_policy_limits for caps and refresh windows; "
        "check_request_eligibility for cap and refresh checks; and "
        "flag_for_human_review to escalate. Do not invent employees, limits, "
        "or eligibility."
    ),
)


@mcp.tool()
def get_employee_info(employee_id: str) -> list[dict[str, Any]]:
    """Return role, hire_date, and equipment for this employee id."""
    return retrieve_employee_info(employee_id)


@mcp.tool()
def get_policy_limits(role: str) -> dict[str, Any]:
    """Return per-category caps and refresh windows for this role."""
    return retrieve_policy_limits(role)


@mcp.tool()
def check_request_eligibility(employee_id: str, item: str) -> dict[str, Any]:
    """Return whether this item is within cap and refresh for this employee."""
    return run_eligibility_check(employee_id, item)


@mcp.tool()
def flag_for_human_review(
    employee_id: str, request: str, reason: str
) -> dict[str, Any]:
    """Escalate a request for human review and return a review ticket id."""
    return record_human_review(employee_id, request, reason)


if __name__ == "__main__":
    mcp.run(transport="stdio")
