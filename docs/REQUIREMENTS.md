# IT Equipment Request Handler - Requirements

**System:** internal MCP server + ReAct agent. Mock HR, inventory, and policy live on the server. The agent **must** use tools for facts and escalation. It must not invent employees, limits, or eligibility.

**Policy corpus:** `[policies/replacements.md](policies/replacements.md)` is the source of caps and refresh windows.

---

## 1. Request (agent input)


| Field         | Required | Notes                                              |
| ------------- | -------- | -------------------------------------------------- |
| `employee_id` | Yes      | Key for every employee tool                        |
| `item`        | Yes      | Free text ("second monitor", "laptop replacement") |
| `reason`      | Yes      | Why they need it (age, extra screen, broken, etc.) |


Role, tenure, and equipment are **not** on the request. They come from `get_employee_info`.

---


## 2. Policy

Caps, refresh windows, new-hire, and quantity are defined in [policies/replacements.md](policies/replacements.md) (`Equipment Replacement Policy (v1.0)`).

---


## 3. Approve, deny, escalate

After tools have returned:

- **Approve** when identity, item category, and inventory are complete, the ask is clearly extra vs replacement vs first issue, there is **no** unverified exception in `reason`, and the numbered rule in `replacements.md` allows it.
- **Deny** when the same facts are complete, there is **no** unverified exception, and the numbered rule forbids it (over cap, refresh too soon, second monitor for `employee`).
- **Escalate** when any case in §4 applies. Do not approve or deny on a guess.

---


## 4. Ambiguous -> escalate

If any of these hold, the case is **indeterminate**.

1. **Identity:** `get_employee_info` finds no employee, or more than one.
2. **Unmapped item:** `item` is not covered by replacement policy (standing desk, GPU, stipend, "newest whatever").
3. **Incomplete inventory:** missing `assigned_on` or `status` so age/cap cannot be computed.
4. **Unclear ask:** cannot tell extra unit vs replacement vs first issue from `item` + equipment on file.
5. **Unverified exception:** broken, stolen, accessibility, executive override — policy has no broken-asset flag.
6. **Policy gap:** `get_policy_limits` has no row for that role + category.
7. **Mixed / vague quantity:** two primary items, or "a few monitors" with no count.
8. **Ineligible + exception** in the same request (over cap **and** "the screen is cracked"). Escalate; do not deny.

`flag_for_human_review` returns `review_ticket_id`. Put that on the decision object.

---


## 5. Agent decision

After tools:

```text
decision: approve | deny | escalate
employee_id: ...
item: ...
policy_rule: ... | none
review_ticket_id: set if flag_for_human_review was called
rationale: cite tool results only
```
