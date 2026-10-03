# MCP

IT equipment requests over an MCP stdio server. It looks up staff, inventory, and policy from JSON, checks one free-text item against cap and refresh, and asks a local model to allow, deny, or escalate. The host plans, runs a ReAct loop, reflects, and opens a review ticket only after a reflected escalate.

Default stack: Ollama `qwen3:8b` and JSON stores under `data/`.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com), for the interactive CLI, the golden host run, and the live eval

```bash
ollama pull qwen3:8b
```

## Setup

### Ollama

Start the Ollama app, or run `ollama serve`. Check that it is up:

```bash
curl -s http://localhost:11434/api/tags
```

The app's default `OLLAMA_HOST` is `http://host.docker.internal:11434`, which reaches Ollama on the host from the devcontainer. When you run Python on the host, or on the self-hosted runner, set `OLLAMA_HOST=http://localhost:11434`.

### JSON stores

Staff, inventory, policy limits, and review tickets are files. There is no database to start.

| File | Contents |
| --- | --- |
| `data/staff.json` | Employee id, name, role, hire date, department |
| `data/inventory.json` | Assignments: category, status, `assigned_on`, asset tag |
| `data/policy_limits.json` | `cap_active`, `refresh_years`, `policy_rule` per role and category |
| `data/reviews.json` | Open review tickets. `flag_for_human_review` appends here |

Caps and refresh windows are written in [policies/replacements.md](policies/replacements.md). `check_request_eligibility` applies the rows in `data/policy_limits.json`.

A live host run that escalates writes new `REV-####` tickets into `data/reviews.json`.

### Python

```bash
uv sync
```

## Run

From the repo root, with `src` on `PYTHONPATH`:

```bash
# Spike: list tools on server_mini and call get_employee_info for E-1001.
PYTHONPATH=src uv run python src/client_mini.py

# List the four equipment tools on server.py.
PYTHONPATH=src uv run python src/client.py

# Interactive request. Prompts for employee_id (E- plus 4 digits), item, and reason.
# Type quit at any prompt to exit.
PYTHONPATH=src uv run python src/cli.py

# Golden host: 15 requests through plan, ReAct, reflect, and flag.
# Writes runs/<UTC timestamp>.json and prints ok / 15.
PYTHONPATH=src uv run python src/host.py

# Score that JSON against data/golden/golden.json.
PYTHONPATH=src uv run python src/score_run.py runs/<timestamp>.json
```

`runs/` is gitignored. Copy a timestamped file into `docs/` if you want it in git. A recorded host run is [docs/eval-run.json](docs/eval-run.json) (15/15 `ok`). Decision rules are in [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Changing settings for a run

`Settings.from_env()` reads the process environment when a module imports `config`. Export a variable for the rest of the shell session, or prefix one command. Unset variables fall back to the Environment table below.

```bash
export OLLAMA_HOST=http://localhost:11434
export GENERATION_MODEL=qwen3:8b
export MAX_TURNS=8
PYTHONPATH=src uv run python src/host.py
```

```bash
OLLAMA_HOST=http://localhost:11434 \
  PYTHONPATH=src uv run python src/cli.py
```

`host.py` and `tools.py` read these values at import. Set them before the process starts.

## Requests

Each request is `employee_id`, `item`, and `reason`. Role, kit, and limits are not on the request. They come from tools.

`src/host.py` runs these 15 cases. `data/golden/golden.json` scores the same labels.

| Label | Expected | Why |
| --- | --- | --- |
| `allow-manager-second-monitor` | allow | Manager monitor under cap (1 active, cap 2) |
| `allow-new-hire-laptop` | allow | No active laptop |
| `allow-retired-monitor` | allow | Retired unit does not count toward the cap |
| `allow-laptop-refresh-due` | allow | At cap, oldest laptop is due for refresh |
| `allow-first-monitor` | allow | No active monitor |
| `deny-employee-second-monitor` | deny | Employee monitor at cap, still inside 3 years |
| `deny-laptop-too-new` | deny | Laptop at cap, still inside the refresh window |
| `deny-headset-too-new` | deny | Headset at cap, still inside the refresh window |
| `deny-manager-at-monitor-cap` | deny | Manager already at monitor cap 2 |
| `deny-second-laptop-too-new` | deny | Laptop at cap, still inside the refresh window |
| `escalate-duplicate-id` | escalate | Two staff rows for `E-1011` |
| `escalate-unknown-id` | escalate | No staff row for `E-9999` |
| `escalate-unmapped-gpu` | escalate | `GPU` is not a covered category |
| `escalate-incomplete-status` | escalate | Matching keyboard has no `status` |
| `escalate-mixed` | escalate | `laptop and monitor` names two categories |

Covered categories: monitor, laptop, dock, headset, keyboard, mouse. Roles with limit rows: `employee`, `manager`. `item` maps by case-insensitive substring. Words such as `second` or `third` are not a quantity.

## Host loop

`cli.py` and `host.py` share `run_react`. One MCP session stays open for the run.

1. **Plan.** Fill `plan.v1.md`. The model lists tool steps and does not call tools. Facts must come from tools.
2. **ReAct.** Up to `MAX_TURNS` (default 8). Each turn is one Thought plus Action and Action Input, or Final Answer and Rationale. The host calls the named tool, appends `Observation:` to the trace, and hides tools already used. A Final Answer is accepted only after the trace is non-empty. The golden path is `get_employee_info`, then `get_policy_limits`, then `check_request_eligibility`, then Final Answer (4 ReAct steps).
3. **Max steps.** If the loop ends without a Final Answer, `max_steps.v1.md` forces `escalate`.
4. **Reflect.** `reflect.v1.md` checks the draft against the trace. `eligible: true` stays allow unless the item asks for more units than `cap_active - active`, or the quantity is vague (`a few`, `several`, `full setup`). `eligible: false` is deny. `eligible: null` is escalate. The reflected text replaces the draft.
5. **Flag.** If the reflected answer is `escalate`, `flag.v1.md` must call `flag_for_human_review`. The host stores `review_ticket_id` on the decision. The ReAct prompt tells the model not to open a ticket itself. Scoring treats a ticket id inside a ReAct observation as a premature flag.

`eligible` from the tool is `true`, `false`, or `null`:

- **allow** when `eligible` is `true` (under cap, or at cap and the oldest dated unit is due for refresh).
- **deny** when `eligible` is `false` (at cap and still inside the refresh window, or at cap with no `refresh_years`).
- **escalate** when `eligible` is `null`: unknown or duplicate id, unmapped item, mixed categories, missing `status`, missing `assigned_on` on an active unit already at cap, no policy row for that role and category, or staff or inventory JSON that fails validation.

Ollama is called at `{OLLAMA_HOST}/api/generate` with temperature 0, seed 42, `think: false`, and stop sequences `\nObservation:` and `\nThought:`. Timeout is 120 seconds.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `GENERATION_PROVIDER` | `ollama` | Generation adapter name. The host always constructs `OllamaAdapter` |
| `GENERATION_MODEL` | `qwen3:8b` | Ollama model id |
| `STORE_PROVIDER` | `json` | Store adapter name. Tools always open the JSON files under `DATA_DIR` |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama base URL |
| `DATA_DIR` | `data` | Directory for staff, inventory, policy limits, and reviews |
| `RUNS_DIR` | `runs` | JSON output directory for `host.py` |
| `PROMPTS_DIR` | `src/prompts` | Read by `Settings`. `host.py` fills templates from `src/prompts` |
| `GOLDEN_PATH` | `data/golden/golden.json` | Cases and expected tool order for `score_run.py` |
| `MAX_TURNS` | `8` | ReAct steps before the max-steps prompt |
| `PLAN_PROMPT` | `plan.v1.md` | Plan template |
| `REACT_PROMPT` | `react.v2.md` | ReAct template |
| `REFLECT_PROMPT` | `reflect.v1.md` | Reflect template |
| `FLAG_PROMPT` | `flag.v1.md` | Flag template |
| `MAX_STEPS_PROMPT` | `max_steps.v1.md` | Forced escalate when the loop runs out of steps |

Names are enums in `src/enums.py`. Supported values: `ollama`, `qwen3:8b`, `json`, and the five prompt filenames above. Any other value fails when `Settings.from_env()` runs.

## Layout

```text
src/
  server.py                  # MCP equipment server: four tools over stdio
  server_mini.py             # spike: get_employee_info only
  client.py                  # spawn server.py and assert the tool list
  client_mini.py             # spawn server_mini and call get_employee_info
  cli.py                     # interactive employee_id, item, reason
  host.py                    # 15 golden requests; writes runs/
  score_run.py               # score a run JSON against golden.json
  tools.py                   # employee, policy, eligibility, review ticket
  models.py                  # Staff, Assignment, PolicyLimit, ReviewTicket
  config.py                  # Settings.from_env()
  enums.py
  generation/
    base.py                  # ModelAdapter
    ollama.py                # /api/generate
  store/
    base.py                  # Store protocol
    json.py                  # one JSON file
  prompts/
    plan.v1.md
    react.v2.md
    reflect.v1.md
    flag.v1.md
    max_steps.v1.md
data/
  staff.json
  inventory.json
  policy_limits.json
  reviews.json
  golden/golden.json         # 15 cases, tool order, step count
policies/replacements.md     # caps, refresh windows, rule ids
docs/REQUIREMENTS.md
docs/eval-run.json           # recorded host run, 15/15 ok
tests/                       # unit tests; mock_data/ for store fixtures
tests/test_golden_metrics.py # live host, marked integration
.github/workflows/checks_mcp.yaml
```

## Checks

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -m "not integration" --cov --cov-report=term-missing
```

Coverage `fail_under` is 100 on `src`. `src/store/*` and `src/generation/*` are omitted.

`tests/test_golden_metrics.py` is marked `integration`. It runs `host.main()` against a temp `runs/` directory and scores the JSON. Gates: decision 1.00, tool order 1.00, eligible 1.00, max-steps 1.00, no premature flag 1.00, and step-count at least 0.80, over 15 cases. It skips when Ollama is down. On CI (`CI` set) that same miss fails the job.

```bash
OLLAMA_HOST=http://localhost:11434 uv run pytest -m integration
```

CI (`.github/workflows/checks_mcp.yaml`) runs on pull requests and on pushes to `main` and `feature/mcp-setup`:

- `checks` (GitHub-hosted): `uv sync --frozen`, mypy, ruff, `pytest -m "not integration" --cov`.
- `live-eval` (self-hosted runner): `pytest -m integration` with `OLLAMA_HOST=http://localhost:11434`. The runner machine also needs Ollama serving `qwen3:8b`.

`score_run.py` also prints reflect accuracy (draft Final Answer stayed the same). The integration job does not gate on that rate. Golden expects `expected_reflect_changed: false`.