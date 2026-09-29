# Equipment Replacement Policy (v1.0)

## Scope

### Covered categories

monitor, laptop, dock, headset, keyboard, mouse. Anything else is unmapped (escalate).

### Roles

`employee` and `manager` only. Any other role is a policy gap (escalate).

### How limits are applied

Caps count **active** assignments. Age is years since `assigned_on`. Rule ids (`R-...`) are what the agent puts on `policy_rule`.

## New hire

### Eligibility

`hire_date` within 90 days and **zero** active items in that category.

### Standard kit

1 laptop, 1 monitor, 1 dock, 1 keyboard, 1 mouse, 1 headset, without waiting on refresh windows.

## Employee

### Monitor

Cap 1 active. Replacement if current unit is ≥ 3 years or retired. Second monitor is deny (`R-EMP-MON`, `R-EMP-MON-CAP`).

### Laptop

Cap 1 active. Refresh if ≥ 4 years (`R-EMP-LAP`).

### Dock

Cap 1 active. Refresh if ≥ 4 years, tied to laptop cycle (`R-EMP-DOCK`).

### Headset

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-HEAD`).

### Keyboard

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-KBD`).

### Mouse

Cap 1 active. Refresh if ≥ 2 years (`R-EMP-MOU`).

## Manager

### Monitor

Cap 2 active. Additional unit allowed until cap. Replacing one unit: that unit ≥ 3 years (`R-MGR-MON`).

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

Quantity > 1 is approve only if each unit fits the cap (for example a manager with 0 monitors requesting 2).

### Vague count

"A few monitors" or "full setup" with no number is escalate, not deny.