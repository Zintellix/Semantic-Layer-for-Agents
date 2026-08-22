"""FastAPI surface exposing the multi-domain semantic-layer pipeline to the UI.

A thin adapter over the same Orchestrator the CLI drives — no semantic logic lives
here. One orchestrator is built (and cached) per domain.

Run:  uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Optional, List

from fastapi import FastAPI, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from strawberry.fastapi import GraphQLRouter

from zx import ONTOLOGY_VERSION
from zx.agent import _credentials_available, pick_provider
from zx.domains import load_domains
from zx.orchestrator import Orchestrator
from zx.graphql import schema
from zx.auth import get_user_roles
from zx.compiler import compile_packs
from zx.db import connect, PACKS_DIR
from zx.registry import Registry

app = FastAPI(title="Zintellix Semantic Layer", version=ONTOLOGY_VERSION,
              description="Enterprise Semantic Layer API — ontology-driven, domain-agnostic")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_DOMAINS = load_domains()
_cache: dict[str, Orchestrator] = {}

def orch(domain: str) -> Orchestrator:
    if domain not in _cache:
        _cache[domain] = Orchestrator(domain=domain)
    return _cache[domain]

# Mount GraphQL APIs dynamically for each domain
for domain_name in _DOMAINS:
    def make_context_getter(d=domain_name):
        async def get_context(request: Request = None, roles: List[str] = Depends(get_user_roles)):
            return {"orchestrator": orch(d), "roles": roles}
        return get_context
    router = GraphQLRouter(schema, context_getter=make_context_getter(domain_name))
    app.include_router(router, prefix=f"/graphql/{domain_name}")


# ---- Request Models ----
class AskRequest(BaseModel):
    question: str
    domain: str
    use_llm: bool = False


class SignalRequest(BaseModel):
    domain: str
    key: str
    type: Optional[str] = None


class ApproveRequest(BaseModel):
    domain: str
    action_id: str


# ---- Core Endpoints ----
@app.get("/api/health")
def health():
    return {"status": "ok", "version": ONTOLOGY_VERSION,
            "domains": list(_DOMAINS.keys()),
            "llm_available": _credentials_available(),
            "provider": pick_provider()}


@app.get("/api/domains")
def domains():
    return {"domains": [
        {"name": d.name, "label": d.label, "flagship": d.flagship,
         "primary_type": d.primary_type, "samples": d.samples}
        for d in _DOMAINS.values()
    ]}


@app.get("/api/objects")
def objects(domain: str):
    try:
        return orch(domain).objects_view()
    except Exception as e:
        # Graceful fallback — return schema-only view if objects_view crashes
        return _schema_only_objects(domain)


@app.post("/api/ask")
def ask(req: AskRequest):
    o = orch(req.domain)
    if req.use_llm:
        o.agent.use_llm = True
    return o.ask(req.question)


@app.post("/api/signal")
def signal(req: SignalRequest):
    return orch(req.domain).signal(req.key, req.type)


@app.post("/api/approve")
def approve(req: ApproveRequest):
    return orch(req.domain).approve(req.action_id)


@app.get("/api/explain/{object_id}")
def explain(object_id: str, domain: str):
    return orch(domain).explain(object_id)


# ---- Enterprise Endpoints ----

@app.get("/api/schema")
def get_schema(domain: Optional[str] = None):
    """Returns the full ontology schema — object types, properties, links, actions, functions."""
    conn = connect()
    reg = Registry(conn)
    
    result = {"object_types": {}, "link_types": [], "functions": [], "actions": []}
    
    for ot in reg.object_types():
        if domain:
            if ot.pack != domain:
                continue
        result["object_types"][ot.object_type] = {
            "pack": ot.pack,
            "primary_key": ot.primary_key,
            "title_property": ot.title_property,
            "datasource": ot.datasource,
            "properties": {
                name: {"type": p.type, "source": p.source, "function": p.function, "is_derived": p.is_derived}
                for name, p in ot.properties.items()
            },
            "links": {
                name: {"to": lk.to_type, "cardinality": lk.cardinality, "join": lk.join}
                for name, lk in ot.links.items()
            },
            "extends": ot.extends,
            "implements": ot.implements,
        }
    
    # Link types
    rows = conn.execute("SELECT * FROM ontology_link_types").fetchall()
    for r in rows:
        lt = {"link_type": r["link_type"], "from_type": r["from_type"],
              "to_type": r["to_type"], "cardinality": r["cardinality"],
              "join": json.loads(r["join_binding"])}
        if domain:
            schema_types = set(result["object_types"].keys())
            if lt["from_type"] not in schema_types and lt["to_type"] not in schema_types:
                continue
        result["link_types"].append(lt)
    
    # Functions
    for fn in reg.functions():
        fn_dict = {"function_id": fn.function_id, "returns": fn.returns,
                   "kind": fn.kind, "formula": fn.formula,
                   "inputs": fn.inputs, "params": fn.params}
        result["functions"].append(fn_dict)
    
    # Actions
    rows = conn.execute("SELECT * FROM ontology_action_types").fetchall()
    for r in rows:
        act = {"action_type": r["action_type"], "object_type": r["object_type"],
               "tier": r["tier"], "reversibility": r["reversibility"],
               "parameters": json.loads(r["parameter_schema"]),
               "guards": json.loads(r["guards"]),
               "connector_write": r["connector_write"]}
        result["actions"].append(act)
    
    conn.close()
    return result


@app.get("/api/lineage/{object_type}")
def get_lineage(object_type: str):
    """Returns data lineage — which tables/columns feed which properties."""
    conn = connect()
    reg = Registry(conn)
    try:
        ot = reg.object_type(object_type)
    except KeyError:
        conn.close()
        return {"error": f"Unknown object type: {object_type}"}
    
    lineage = {
        "object_type": object_type,
        "datasource": ot.datasource,
        "primary_key": ot.primary_key,
        "properties": {},
        "link_dependencies": {}
    }
    
    for name, prop in ot.properties.items():
        entry = {"type": prop.type}
        if prop.source:
            table, _, col = prop.source.partition(".")
            entry["source_table"] = table
            entry["source_column"] = col
            entry["binding"] = "direct"
        elif prop.function:
            entry["function"] = prop.function
            entry["binding"] = "computed"
            try:
                fn = reg.function(prop.function)
                entry["formula"] = fn.formula
                entry["inputs"] = fn.inputs
            except KeyError:
                pass
        lineage["properties"][name] = entry
    
    for lname, lk in ot.links.items():
        lineage["link_dependencies"][lname] = {
            "to_type": lk.to_type,
            "cardinality": lk.cardinality,
            "join_columns": lk.join
        }
    
    conn.close()
    return lineage


@app.get("/api/metrics")
def get_metrics():
    """Returns all computed functions/metrics in the registry."""
    conn = connect()
    reg = Registry(conn)
    metrics = []
    for fn in reg.functions():
        metrics.append({
            "function_id": fn.function_id,
            "returns": fn.returns,
            "kind": fn.kind,
            "formula": fn.formula,
            "inputs": fn.inputs,
            "params": fn.params,
            "test_count": len(fn.tests)
        })
    conn.close()
    return {"metrics": metrics, "total": len(metrics)}


@app.get("/api/audit-log")
def get_audit_log():
    """Returns the decision/action audit log."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    log = []
    for r in rows:
        log.append({
            "action_id": r["action_id"],
            "action_type": r["action_type"],
            "target_objects": json.loads(r["target_objects"]) if r["target_objects"] else [],
            "tier": r["tier"],
            "status": r["status"],
            "params": json.loads(r["params"]) if r["params"] else {},
            "created_at": r["created_at"]
        })
    conn.close()
    return {"log": log, "total": len(log)}


@app.get("/api/data/{object_type}")
def browse_data(object_type: str, limit: int = 50):
    """Browse raw data rows for any object type."""
    conn = connect()
    reg = Registry(conn)
    try:
        ot = reg.object_type(object_type)
    except KeyError:
        conn.close()
        return {"error": f"Unknown object type: {object_type}"}
    
    table = ot.datasource.split(".", 1)[1] if ot.datasource else object_type.lower()
    try:
        rows = conn.execute(f"SELECT * FROM {table} LIMIT ?", (limit,)).fetchall()
        data = [dict(r) for r in rows]
    except Exception as e:
        data = []
    
    conn.close()
    return {
        "object_type": object_type,
        "table": table,
        "primary_key": ot.primary_key,
        "columns": list(ot.properties.keys()),
        "rows": data,
        "total": len(data)
    }


@app.post("/api/upload")
async def upload_pack(file: UploadFile = File(...), pack: str = Form(...)):
    """Upload a YAML file to a pack directory and trigger rebuild."""
    save_dir = PACKS_DIR / pack
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        compile_packs()
        _cache.clear()
        global _DOMAINS
        _DOMAINS = load_domains()
        return {"status": "success", "message": f"Uploaded {file.filename} to {pack}/ and rebuilt.",
                "file": str(file_path), "domains": list(_DOMAINS.keys())}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/rebuild")
def rebuild():
    """Triggers a dynamic recompilation of the semantic layer packs."""
    try:
        compile_packs()
        # Clear the orchestrator cache so new requests get the fresh registry
        _cache.clear()
        global _DOMAINS
        _DOMAINS = load_domains()
        return {"status": "success", "message": "Semantic layer rebuilt successfully.",
                "domains": list(_DOMAINS.keys())}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _schema_only_objects(domain: str):
    """Fallback when objects_view fails — return the schema without data."""
    conn = connect()
    reg = Registry(conn)
    types = []
    for ot in reg.object_types():
        if ot.pack == domain or not domain:
            types.append({
                "object_type": ot.object_type,
                "properties": list(ot.properties.keys()),
                "links": list(ot.links.keys()),
            })
    conn.close()
    return {"domain": domain, "object_types": types, "rows": [],
            "note": "Schema-only view (data query not available for this domain config)"}
