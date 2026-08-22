# 🕸️ Zintellix — Semantic Layer for AI Agents

> **An ontology-driven, domain-agnostic semantic layer that turns raw database tables into a governed knowledge graph — with plug-and-play AI agent support.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 What Is This?

A **13-layer semantic engine** that sits between your raw data and your AI agents/BI tools. Instead of letting every tool write its own SQL, the semantic layer provides a **single source of truth** for:

- **What objects exist** (Deals, Accounts, Employees, Tasks...)
- **How they connect** (Deal → belongs_to → Account)
- **What metrics are computed** (top deals by amount, salary budget)
- **What actions are allowed** (update deal stage, change employee title)
- **What security roles can access what** (admin, sales_rep, viewer)

```
┌─────────────────────────────────────────────────────────┐
│                   AI Agent / Dashboard                   │
│           (asks: "Which deals are at risk?")             │
└────────────────────────┬────────────────────────────────┘
                         │ Natural Language
┌────────────────────────▼────────────────────────────────┐
│              Zintellix Semantic Layer                     │
│  ┌──────┐ ┌────────┐ ┌───────┐ ┌─────────┐ ┌────────┐ │
│  │Parse │→│Resolve │→│ Plan  │→│Prefetch │→│ Agent  │ │
│  └──────┘ └────────┘ └───────┘ └─────────┘ └────────┘ │
│          ↓               ↓           ↓                   │
│     ChromaDB         Registry    Object Layer            │
│   (embeddings)      (ontology)  (data binding)           │
└────────────────────────┬────────────────────────────────┘
                         │ SQL (governed)
┌────────────────────────▼────────────────────────────────┐
│              SQLite (or PostgreSQL/Snowflake)             │
│         accounts │ deals │ employees │ departments       │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started (Clone & Run)

### Prerequisites
- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **Git** — [Download](https://git-scm.com/)

### 1. Clone the Repository
```bash
git clone https://github.com/Zintellix/Semantic-Layer-for-Agents.git
cd Semantic-Layer-for-Agents
```

### 2. Create Virtual Environment & Install Dependencies

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment (Optional — for AI Agent)
```bash
cp .env.example .env
# Edit .env and add your API key:
#   GEMINI_API_KEY=your-key-here
```

### 4. Build the Database
This seeds sample data and compiles all ontology packs:
```bash
python build.py
```
✅ Expected output: `Compiled 5 object types, 2 functions, 2 actions... Build complete`

### 5. Start the API Server
```bash
python -m uvicorn api:app --reload --port 8000
```
✅ API is live at **http://localhost:8000**

### 6. Start the Dashboard (New Terminal)
Open a **second terminal** in the same directory:

**Windows:**
```powershell
.\.venv\Scripts\activate
python -m streamlit run dashboard.py
```

**macOS / Linux:**
```bash
source .venv/bin/activate
python -m streamlit run dashboard.py
```
✅ Dashboard is live at **http://localhost:8501**

---

## 🏗️ Architecture — The 13 Layers

| Layer | Module | Purpose |
|-------|--------|---------|
| L0 | `seed/schema.sql` | Registry schema (ontology storage) |
| L1 | `zx/primitives.py` | Dataclasses: ObjectType, LinkType, FunctionDef, ActionType, EventType |
| L2 | `zx/compiler.py` | Ontology compiler — validates + writes YAML packs to registry. **Auto-creates DB tables** |
| L3 | `zx/registry.py` | Runtime registry accessor (cached reads from compiled ontology) |
| L4 | `zx/objects.py` | Object data binding — property reads resolve through source bindings |
| L5 | `zx/functions.py` | Deterministic function executor — derived props, object sets, decision functions |
| L6 | `zx/resolver.py` | Semantic resolver — alias dictionary + ChromaDB vector similarity + confidence gating |
| L7 | `zx/planner.py` | Query planner — path validation + prefetch (proof the graph is load-bearing) |
| L8 | `zx/events.py` | Event lifter — signals → severity classification |
| L9 | `zx/actions.py` | Tiered action layer — propose → guard → approve → execute |
| L10 | `zx/agent.py` | Agent runtime — Gemini/OpenAI/Anthropic + deterministic fallback |
| L11 | `zx/grounding.py` | Grounding validator — numeric + entity + action-schema checks |
| L12 | `zx/orchestrator.py` | Orchestrator — 7-stage pipeline (parse → resolve → plan → prefetch → agent → validate → respond) |

---

## 📁 Project Structure

```
Semantic-Layer-for-Agents/
├── api.py                  # FastAPI server (REST + GraphQL) — 12 endpoints
├── dashboard.py            # Streamlit enterprise UI (8 tabs)
├── build.py                # One-shot build: reset DB → seed → compile
├── requirements.txt        # Python dependencies
├── QUICKSTART.md           # 5-minute getting started guide
├── .env.example            # Environment variable template
│
├── zx/                     # 🧠 Core semantic engine (13 layers)
│   ├── __init__.py         # Version + workspace ID
│   ├── config.py           # Environment loader (.env)
│   ├── db.py               # SQLite connection + paths
│   ├── primitives.py       # L1: Ontology dataclasses
│   ├── compiler.py         # L2: YAML → registry compiler (with auto-DDL)
│   ├── registry.py         # L3: Runtime ontology accessor
│   ├── objects.py          # L4: Object data binding layer
│   ├── functions.py        # L5: Deterministic function executor
│   ├── resolver.py         # L6: Semantic resolver (aliases + ChromaDB)
│   ├── embeddings.py       # L6: Local embedding function
│   ├── planner.py          # L7: Query planner + path validation
│   ├── graphql.py          # L7: Dynamic GraphQL schema
│   ├── events.py           # L8: Event severity lifter
│   ├── actions.py          # L9: Tiered action governance
│   ├── agent.py            # L10: Multi-provider LLM agent
│   ├── grounding.py        # L11: Grounding validator
│   ├── orchestrator.py     # L12: 7-stage orchestration pipeline
│   ├── cache.py            # Query caching
│   ├── auth.py             # RBAC mock (token-based roles)
│   ├── domains.py          # Multi-domain loader
│   └── cli.py              # Command-line interface
│
├── packs/                  # 📦 Domain packs (plug-and-play)
│   ├── core/               # Shared interfaces
│   │   └── interfaces.yaml
│   ├── sales/              # B2B Sales domain
│   │   ├── domain.yaml     # Domain manifest
│   │   ├── objects.yaml    # Account, Deal, SalesRep
│   │   ├── links.yaml      # Relationships
│   │   ├── functions.yaml  # fn.top_deals
│   │   └── actions.yaml    # update_deal_stage
│   └── hr/                 # Human Resources domain
│       ├── domain.yaml     # Domain manifest
│       ├── objects.yaml    # Employee, Department
│       ├── functions.yaml  # fn.all_employees
│       └── actions.yaml    # update_employee_title
│
├── seed/                   # 🌱 Database seed scripts
│   ├── schema.sql          # Registry table definitions
│   ├── seed_sales.py       # Sales test data (3 accounts, 2 reps, 3 deals)
│   └── seed_hr.py          # HR test data (2 employees, 2 departments)
│
├── tests/                  # 🧪 Test suite
│   └── ...
│
├── sample_hr_domain.yaml         # Example: HR domain for upload testing
└── sample_project_domain.yaml    # Example: Project Management domain
```

> **Note:** The `data/` directory (SQLite DB + ChromaDB vectors) is auto-generated by `build.py` and excluded from git.

---

## 📊 Dashboard Tabs

| Tab | What It Does |
|---|---|
| 📋 **Overview** | Platform health, domain count, object types, links, functions |
| 🏗️ **Schema** | Interactive explorer — properties, types, links for each object type |
| 🕸️ **Graph** | Visual ontology graph — object types as nodes, links as edges |
| 📊 **Data** | Browse raw database rows per object type |
| 🤖 **Agent** | Ask natural language questions (Gemini/GPT/Claude + deterministic fallback) |
| 📂 **Domains** | Upload new YAML domain packs and hot-rebuild the registry |
| 🔗 **Lineage** | Property-level data lineage — which table/column feeds which property |
| 📜 **Audit Log** | View the action decision log |

---

## 📡 API Reference

All endpoints available at `http://localhost:8000`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Platform health, version, LLM status |
| `/api/domains` | GET | List all loaded domains with metadata |
| `/api/schema?domain=sales` | GET | Full ontology schema (types, links, functions, actions) |
| `/api/data/{object_type}` | GET | Browse raw data rows for any object type |
| `/api/lineage/{object_type}` | GET | Data lineage — source tables → properties |
| `/api/metrics` | GET | All computed functions and metrics |
| `/api/objects?domain=sales` | GET | Domain object view with rankings |
| `/api/ask` | POST | Natural language query (7-stage pipeline) |
| `/api/signal` | POST | Signal an external event for severity classification |
| `/api/approve` | POST | Approve a proposed action |
| `/api/explain/{object_id}` | GET | Deep-dive into a single object |
| `/api/upload` | POST | Upload YAML + auto-rebuild |
| `/api/rebuild` | POST | Recompile all domain packs |
| `/api/audit-log` | GET | Action decision log |
| `/graphql/{domain}` | GET/POST | Dynamic GraphQL per domain |

---

## 🔌 Creating a New Domain (Plug-and-Play)

### Via Dashboard (Recommended)
1. Open the **📂 Domains** tab at http://localhost:8501
2. Upload your `objects.yaml` and `domain.yaml` files
3. Set the pack name (e.g., `marketing`)
4. Click **Upload & Rebuild** — the domain appears instantly!

### Via File System
1. Create `packs/your_domain/objects.yaml`:
```yaml
- object_type: Campaign
  pack: marketing
  primary_key: campaign_id
  title_property: name
  datasource: sqlite.campaigns
  properties:
    name: { type: string, source: campaigns.name }
    budget: { type: number, source: campaigns.budget }
    channel: { type: string, source: campaigns.channel }
```

2. Create `packs/your_domain/domain.yaml`:
```yaml
domain: marketing
label: Marketing Operations
flagship: "Which campaigns are over budget?"
primary_type: Campaign
object_set: "fn.all_campaigns"
metric:
  mode: aggregate
  unit: "$"
  value: budget
  threshold: 100000
  threshold_label: "quarterly budget"
  direction: at_most
action:
  action_type: pause_campaign
```

3. Rebuild: `python build.py` or hit `/api/rebuild`

> **Auto-DDL:** The compiler will automatically create the `campaigns` table in SQLite from your YAML definitions!

---

## 🤖 Plugging AI Agents on Top

The semantic layer provides **grounded context** to AI agents. Agents never query the database directly.

### REST API
```python
import requests

response = requests.post("http://localhost:8000/api/ask", json={
    "question": "Show me the top deals",
    "domain": "sales",
    "use_llm": True    # Requires GEMINI_API_KEY in .env
})

data = response.json()
print(data["answer"])          # Natural language answer
print(data["citations"])       # Grounded entity references
print(data["confidence"])      # 0.0 - 1.0
print(data["action_card"])     # Proposed action (if any)
print(data["stages"])          # Full 7-stage reasoning trace
```

### GraphQL
Navigate to `http://localhost:8000/graphql/sales`:
```graphql
{
  allObjects(objectType: "Deal", limit: 10) {
    objectId
    objectType
    properties
    traverse(link: "belongs_to_account") {
      objectId
      properties
    }
  }
}
```

---

## 🔒 Security (RBAC)

Role-Based Access Control at the ontology level:

```yaml
# In objects.yaml — restrict access to specific roles
- object_type: Deal
  roles_allowed: ["admin", "sales_rep"]
```

Test with tokens:
```bash
# Admin access
curl -H "Authorization: Bearer admin-token" http://localhost:8000/api/objects?domain=sales

# Viewer access (may be restricted)
curl -H "Authorization: Bearer viewer-token" http://localhost:8000/api/objects?domain=sales
```

---

## 🧪 Testing

```bash
# Build + compile-time tests (formula validation)
python build.py

# Run the sales agent test
python test_sales_agent.py

# Quick API smoke test
curl http://localhost:8000/api/health
curl http://localhost:8000/api/schema?domain=sales
curl http://localhost:8000/api/data/Deal
```

---

## 🧑‍💼 Team Presentation — Key Talking Points

### Elevator Pitch
> "This is a semantic layer — a middleware that translates our business concepts (deals, accounts, employees) into a governed knowledge graph. Any AI agent we build can plug into it and get grounded, verified answers without writing a single SQL query."

### Why This Matters
1. **Domain-Agnostic** — The same engine serves Sales, HR, Marketing — just drop in a YAML pack.
2. **Anti-Hallucination** — The grounding validator checks every number and entity the AI produces against the semantic context.
3. **Plug-and-Play** — New domains are hot-loaded via YAML upload — no code changes, no restarts.
4. **Auto-DDL** — Upload a YAML defining new object types, and the compiler automatically creates the database tables.
5. **Multi-Interface** — REST API, GraphQL, Streamlit dashboard — all consuming the same governed definitions.
6. **Enterprise Security** — RBAC at the ontology level — control who can see which object types.

---

## 📄 License

MIT — See [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
