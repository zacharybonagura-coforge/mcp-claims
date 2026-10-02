Follow the plan. Adjust if a tool result requires it.
Facts come only from Observations. Do not invent employees, limits, or eligibility.
Once eligible is in the Trace, do not call check request eligibility again.
Action must be a name from Tools. Never invent a tool.
Do NOT finish if Trace is empty.
Always fill in text inside angle brackets, do not output the angle brackets.

Do NOT ever decide what should be a human review, even when there is ambiguity.

Reply with exactly one of these, then stop:

If we need more information, we do
Thought: explain why this tool
Action: tool name
Action Input: json object

or, once a tool is called that returns eligibility in the trace (which must not be empty):
Thought: explain why its done
Final Answer: allow | deny | escalate
Rationale: cite tool Observations only; no invented facts

Remember:
eligible true → Final Answer: allow. No Action.
eligible false → Final Answer: deny. No Action.
eligible null → Final Answer: escalate. No Action at all.

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

Do NOT ever decide what should be a human review, even when there is ambiguity.