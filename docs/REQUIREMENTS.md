# IT Equipment Request Handler - Requirements

**System:** MCP stdio server (`equipment`) + ReAct host. Mock HR, inventory, policy, and review tickets are JSON stores. The agent **must** use tools for facts. It must not invent employees, limits, or eligibility.

**Policy corpus:** [../policies/replacements.md](../policies/replacements.md) is the source of caps and refresh windows. Executable rows live in `data/policy_limits.json`. `check_request_eligibility` applies them.

---

## 1. Request (agent input)


| Field         | Required | Notes                                                                 |
| ------------- | -------- | --------------------------------------------------------------------- |
| `employee_id` | Yes      | Key for every employee tool. Interactive CLI requires `E-` + 4 digits |
| `item`        | Yes      | Free text. Eligibility maps it by substring to one covered category   |
| `reason`      | Yes      | Kept on the request and on review tickets. Not an eligibility input   |


Role, tenure, and equipment are **not** on the request. They come from `get_employee_info`.

---


---

## 2. Tools
1. `get_employee_info(employee_id)` — role, `hire_date`, equipment. Empty list = unknown id. Two or more rows = duplicate id; do not pick one.
2. `get_policy_limits(role)` — `cap_active`, `refresh_years`, `policy_rule` per category. Unknown role → `limits: []`.
3. `check_request_eligibility(employee_id, item)` — `eligible` is `true`, `false`, or `null`, plus `detail` and `policy_rule`.
4. `flag_for_human_review(employee_id, request, reason)` — writes an open ticket and returns `review_ticket_id`.

---

## 3. Policy

Caps, refresh windows, and rule ids are defined in [../policies/replacements.md](../policies/replacements.md) and `data/policy_limits.json`.

Covered categories: monitor, laptop, dock, headset, keyboard, mouse. Roles with limit rows: `employee`, `manager`.

---

## 4. Approve, deny, escalate

After tools have returned:

- **allow** when `eligible` is `true` (under cap, or at cap and the oldest dated unit is due for refresh).
- **deny** when `eligible` is `false` (at cap and still inside the refresh window, or at cap with no `refresh_years`).
- **escalate** when `eligible` is `null` (§5). Do not allow or deny on a guess.

Reflect uses the same mapping. If the reflected answer is `escalate`, the host opens a review ticket.

---


## 5. Ambiguous -> escalate

If any of these hold, the case is **indeterminate**.

1. **Identity:** no staff row, or more than one row, for `employee_id`.
2. **Unmapped item:** `item` contains none of the six covered category names.
3. **Mixed item:** `item` contains more than one covered category name (for example `laptop and monitor`).
4. **Incomplete status:** a matching assignment has no `status`, so the cap cannot be counted.
5. **Incomplete assigned_on:** already at cap, and an **active** matching unit has no `assigned_on`, so refresh age cannot be computed.
6. **Policy gap:** no policy row for that role + category (including `contractor` and unknown roles).
7. **Unreadable stores:** staff or inventory JSON fails validation.

`flag_for_human_review` returns `review_ticket_id`. Put that on the decision object.

---


## 6. Agent decision

After tools (and reflect; flag if escalate):
```text
Final Answer: allow | deny | escalate
Rationale: cite tool Observations only
review_ticket_id: set if the host opened a ticket
