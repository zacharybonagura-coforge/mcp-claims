You are checking a draft decision against the Request and the Trace.
Do not call tools. Do not write Action. Do not invent a review ticket id.

Draft:
{{draft}}

Request:
employee_id: {{employee_id}}
item: {{item}}
reason: {{reason}}

Trace:
{{scratchpad}}

Pick exactly one. Deny and escalate cannot both pass.

eligible false → Final Answer: deny.
eligible true → Final Answer: allow, unless an allow check below fails.
eligible null → Final Answer: escalate.

Fail an allow draft if any of these hold:
- The item names a count larger than remaining cap (cap_active minus active).
- The item is vague quantity (a few, several, full setup).
- eligible is false or null.

Keep allow only if eligible is true and (no number in the item, or that number plus active is at most cap_active).
Vague quantity (a few, several, full setup) is escalate only when eligible is not false.

If Final Answer is escalate, Rationale MUST name the Trace detail and what it means.
Do not mention a review ticket.

Reply with exactly three lines. Each label on its own line. Never put Final Answer on the Thought line.

Thought: eligible is true or false or null
Final Answer: allow
Rationale: facts from the Trace