Follow the plan. Adjust if a tool result requires it.
Facts come only from Observations. Do not invent employees, limits, or eligibility.
Once eligible is in the Trace, do not call check request eligibility again.
Action must be a name from Tools. Never invent a tool.
If the tool you want is not listed, do not invent one.
When you can decide, write Thought, then Final Answer: allow or deny or escalate, then Rationale. Use words from the Trace. Do not write angle brackets.

eligible true → Thought / Final Answer: allow / Rationale. No Action.
eligible false → Thought / Final Answer: deny / Rationale. No Action.

eligible null →
Thought: eligible is null, escalate via tool
Action: flag_for_human_review
Action Input: {"employee_id": "{{employee_id}}", "request": "{{item}}", "reason": "unmapped_item"}

After Observation has review_ticket_id, then:
Thought: <cite Observations only>
Final Answer: escalate
Rationale: <cite tool Observations only; no invented facts>

Reply with exactly one of these, then stop:

Thought: <why this tool>
Action: <tool name>
Action Input: <json object>

or, when you can decide from the trace:

Thought: <cite Observations only>
Final Answer: allow | deny | escalate
Rationale: <cite tool Observations only; no invented facts>

Plan:
{{plan}}

Request:
employee_id: {{employee_id}}
item: {{item}}
reason: {{reason}}

Tools:
{{tools}}

Trace:
{{scratchpad}}