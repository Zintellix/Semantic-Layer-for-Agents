# Zintellix — Semantic Layer POC (multi-domain)

A full-height, one-lane-wide proof of the commerce ontology spine: **all 13 layers
present and executing**, now generalised so **one engine serves many verticals**.
Each domain answers a flagship question with a **grounded, cited, agent-authored**
response and a typed action card.

## Domains

Pick a domain in the UI (or `--domain` on the CLI). Adding a new one = drop in a
pack + a `domain.yaml`; **no engine code changes**.

| Domain | Flagship question | Pattern |
|--------|-------------------|---------|
| **cosmetics** (e-commerce) | *Are we going to stock out on our hero shades before the gifting peak?* | timeline vs seasonal window |
| **sales** (pipeline) | *Are we going to hit quota on our top deals this quarter?* | aggregate vs quota |
| **marketing** (budgets) | *Which top campaigns will exhaust their budget before the promo peak?* | timeline vs promo window |
| **saas** (renewals) | *Is the churn risk on our largest accounts above our churn budget?* | aggregate vs churn budget |

## The 13 layers → modules

| Layer | Module | What it does |
|------|--------|--------------|
| L0 Storage & seed | `seed/*.py`, `seed/schema.sql` | SQLite; commerce (ClickHouse stand-in) + registry (Postgres stand-in) |
| L1 Definition packs | `packs/<domain>/*.yaml` | YAML: six primitives + interfaces, per domain |
| L2 Compiler | `zx/compiler.py` | structural + referential + **functional** validation (function tests are a compile gate) |
| L3 Registry | `zx/registry.py` | compiled defs read back through one accessor |
| L4 Object binding | `zx/objects.py` | `get_object` / `read_property` / `traverse` — objects are views |
| L5 Function executor | `zx/functions.py` | derived props, object sets, decision fns (data-driven) |
| L6 Resolver | `zx/resolver.py` | exact → alias → **ChromaDB similarity** → O6 clarify gate (per-domain) |
| L7 Query planner | `zx/planner.py` | link-path validation + prefetch, from the domain spec |
| L8 Event & rules | `zx/events.py` | signal → typed event → severity from the pack |
| L9 Action layer | `zx/actions.py` | enumerate → schema → guard → tier gate → decision_log |
| L10 Agent runtime | `zx/agent.py` | Ontology Context block → **OpenAI** (or Claude / offline reasoner) |
| L11 Grounding | `zx/grounding.py` | numeric + entity + action-schema checks, downgrade path |
| L12 Orchestrator + CLI | `zx/orchestrator.py`, `zx/cli.py` | 7-stage pipeline, domain-aware |
| — Domain layer | `zx/domains.py`, `packs/<d>/domain.yaml` | the glue that makes the engine multi-vertical |
| — REST + UI | `api.py`, `frontend/` | FastAPI + React/TS trace viewer with a domain selector |

## Run it

### 1. Backend

```bash
cd backend
python -m pip install -r requirements.txt
python build.py          # reset + seed EVERY domain + compile (runs all function tests)
python -m pytest -q      # the nine §8 tests, all green
```

CLI (offline; no API key needed):

```bash
python -m zx.cli domains
python -m zx.cli ask --domain sales "Are we going to hit quota on our top deals this quarter?"
python -m zx.cli ask "Are we going to stock out on our hero shades before the gifting peak?"
python -m zx.cli signal --domain cosmetics --key SKU-505
python -m zx.cli explain ws1:Opportunity:OPP-1 --domain sales
```

Serve the API for the UI:

```bash
uvicorn api:app --reload --port 8000
```

### Using the OpenAI agent

Copy `.env.example` → `.env` and set your key:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Restart the API and toggle **"use OpenAI agent"** in the UI. The agent reasons over
the Ontology Context block; the grounding validator (L11) checks its numbers,
entities, and proposed action against the prefetch. **Without a key the deterministic
reasoner runs** — the demo works either way. (Set `ANTHROPIC_API_KEY` instead to use
Claude; `ZX_AGENT_PROVIDER` forces `openai` | `anthropic` | `off`.)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173  (proxies /api → :8000)
```

## What proves the architecture

- Object sets (`fn.hero_shades`, `fn.top_deals`, `fn.top_campaigns`, `fn.top_accounts`)
  are **computed**, not hardcoded.
- Every number in an answer derives from seeded data **through the binding layer**;
  every entity carries an object ID.
- Delete a link from a pack → the planner **rejects** the query (the graph matters).
- A top object → **CRITICAL** + escalation card; a non-top → **HIGH**, and the guard
  **blocks** the escalation → falls back to flag-for-review. Zero vertical code
  outside the pack.
- A below-0.7 resolution **clarifies** instead of guessing (principle O6).

One engine, four verticals, every seam already cut for SL-0.

*Zintellix Technologies — Internal Use Only · CONFIDENTIAL*
