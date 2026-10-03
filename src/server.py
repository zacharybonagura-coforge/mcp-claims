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
    """Look up one employee by id.
    Returns role, hire_date, department, and current equipment
    (category, status, assigned_on, asset_tag). An empty list means
    no match. Two or more rows means a duplicate id; do not pick one.
    """
    return retrieve_employee_info(employee_id)


@mcp.tool()
def get_policy_limits(role: str) -> dict[str, Any]:
    """Return cap_active, refresh_years, and policy_rule per category for a role.
    Role is an exact string (employee vs manager). Unknown roles return
    limits: []. Missing category in that list is a policy gap.
    """
    return retrieve_policy_limits(role)


@mcp.tool()
def check_request_eligibility(employee_id: str, item: str) -> dict[str, Any]:
    """Check whether a free-text item is within cap or refresh for this employee.
    Maps item to one covered category, then compares active kit to policy.
    eligible is true, false, or null. detail explains the outcome
    (within_cap, refresh_ok, refresh_too_soon, identity, unmapped_item,
    mixed_items, policy_gap, incomplete_inventory, parse_error).
    """
    return run_eligibility_check(employee_id, item)


@mcp.tool()
def flag_for_human_review(
    employee_id: str, request: str, reason: str
) -> dict[str, Any]:
    """Escalate an ambiguous request and return review_ticket_id.
    Call this instead of deciding when identity is unclear, inventory
    is incomplete, the item is unmapped, quantity is mixed, or reason
    has an unverified exception. request is the original ask; reason is
    why it cannot be decided. New tickets are status open.
    """
    return record_human_review(employee_id, request, reason)


if __name__ == "__main__":
    mcp.run(transport="stdio")
