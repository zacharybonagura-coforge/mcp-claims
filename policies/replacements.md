# Equipment Replacement Policy (v1.0)

## Scope

### Covered categories

monitor, laptop, dock, headset, keyboard, mouse. Anything else is unmapped (escalate).

`item` maps by case-insensitive substring. None of the names → unmapped. More than one name → mixed. Words such as `second` or `third` are not treated as a quantity.

### Roles

`employee` and `manager` only. Any other role (for example `contractor`) is a policy gap (escalate).

### How limits are applied

Caps count assignments with `status` equal to `active`. Retired and other statuses do not count toward the cap.

Age is years since `assigned_on` on the oldest *dated* matching unit, and only when the request is already at cap: `(today - assigned_on).days / 365.25`.

- Missing `status` on a matching assignment → escalate (cannot count the cap).
- Missing `assigned_on` on an **active** unit **at cap** → escalate (cannot compute refresh age).
- Under cap, dates are not required.

Rule ids (`R-...`) are the `policy_rule` on the matching `policy_limits.json` row. One id per role + category.

### Scoring

1. **Under cap** (`active < cap_active`) → allow. This covers first issue, extra unit under a manager cap, new-hire kit (zero active in that category), and a retired-only desk (retired is not active).
2. **At cap, no `refresh_years`** → deny.
3. **At cap, oldest dated unit age ≥ `refresh_years`** → allow (due for refresh). The eligibility payload may include `replace_unit`.
4. **At cap, oldest dated unit still inside the window** → deny.

`hire_date` is returned on the employee record. It is not a separate eligibility gate.

## Employee

### Monitor

Cap 1 active. Refresh if ≥ 3 years (`R-EMP-MON`).

### Laptop

Cap 1 active. Refresh if ≥ 4 years (`R-EMP-LAP`).

### Dock

Cap 1 active. Refresh if ≥ 4 years (`R-EMP-DOCK`).

### Headset

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-HEAD`).

### Keyboard

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-KBD`).

### Mouse

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-MOU`).

## Manager

### Monitor

Cap 2 active. Additional unit allowed until cap. At cap, replace if the oldest unit is ≥ 3 years (`R-MGR-MON`).

### Laptop

Cap 1 active. Refresh if ≥ 2 years (`R-MGR-LAP`).

### Dock

Cap 1 active. Refresh if ≥ 4 years (`R-MGR-DOCK`).

### Headset

Cap 1 active. Refresh if ≥ 2 years (`R-MGR-HEAD`).

### Keyboard

Cap 1 active. Refresh if ≥ 2 years (`R-MGR-KBD`).

### Mouse

Cap 1 active. Refresh if ≥ 2 years (`R-MGR-MOU`).

## Quantity

### Counted units

The eligibility tool does not parse a number from `item`. Reflect should fail an allow draft if the item names a count larger than remaining cap (`cap_active` minus `active`).

### Vague count

"A few monitors", "several", or "full setup" with no number is escalate, not deny, when `eligible` is not already `false`.