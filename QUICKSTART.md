# ⚡ Quickstart Guide — 5 Minutes to Your First Query

## Prerequisites
- Python 3.11+ installed
- A terminal/command prompt

## Step 1: Create Virtual Environment (One Time)
```powershell
cd zintellix-semantic
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Build the Database
```powershell
.\.venv\Scripts\python.exe build.py
```
You should see: `Compiled 5 object types, 2 functions... Build complete`

## Step 3: Start the API Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
```

## Step 4: Start the Dashboard (New Terminal)
Open a **second terminal** in the same folder:
```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

## Step 5: Open Your Browser
Go to **http://localhost:8501** — You're in! 🎉

## What You Can Do Now

| Tab | What It Does |
|---|---|
| 📋 Overview | See all loaded domains, object types, links, functions |
| 🏗️ Schema | Explore every object type's properties and relationships |
| 🕸️ Graph | Visualize the ontology as an interactive graph |
| 📊 Data | Browse actual database rows per object type |
| 🤖 Agent | Ask natural language questions (add Gemini API key in sidebar) |
| 📂 Domains | Upload new YAML domain packs on the fly |
| 🔗 Lineage | Trace which tables/columns feed which properties |
| 📜 Audit Log | View the action decision log |

## Adding a New Domain (Dynamic Hot-Load)
1. Go to the **📂 Domains** tab
2. Upload your `objects.yaml` file
3. Set the pack name (e.g., `marketing`)
4. Click **Upload & Rebuild**
5. The new domain appears instantly in the sidebar!

## API Endpoints
All available at `http://localhost:8000`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Platform health & status |
| `/api/domains` | GET | List all loaded domains |
| `/api/schema?domain=sales` | GET | Full ontology schema |
| `/api/data/Deal` | GET | Browse data rows |
| `/api/lineage/Deal` | GET | Property data lineage |
| `/api/metrics` | GET | All computed functions |
| `/api/ask` | POST | Natural language query |
| `/api/rebuild` | POST | Recompile all domain packs |
| `/api/upload` | POST | Upload YAML + rebuild |
| `/api/audit-log` | GET | Action decision log |
| `/graphql/sales` | GET/POST | GraphQL playground |
