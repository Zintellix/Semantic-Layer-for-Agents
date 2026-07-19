"""FastAPI surface exposing the multi-domain semantic-layer pipeline to the UI.

A thin adapter over the same Orchestrator the CLI drives — no semantic logic lives
here. One orchestrator is built (and cached) per domain.

Run:  uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from zx import ONTOLOGY_VERSION
from zx.agent import _credentials_available, pick_provider
from zx.domains import load_domains
from zx.orchestrator import Orchestrator

app = FastAPI(title="Zintellix Semantic Layer", version=ONTOLOGY_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_DOMAINS = load_domains()
_cache: dict[str, Orchestrator] = {}


def orch(domain: str = "cosmetics") -> Orchestrator:
    if domain not in _cache:
        _cache[domain] = Orchestrator(domain=domain)
    return _cache[domain]


class AskRequest(BaseModel):
    question: str
    domain: str = "cosmetics"
    use_llm: bool = False


class SignalRequest(BaseModel):
    domain: str = "cosmetics"
    key: str
    type: Optional[str] = None


class ApproveRequest(BaseModel):
    domain: str = "cosmetics"
    action_id: str


@app.get("/api/health")
def health():
    return {"status": "ok", "ontology_version": ONTOLOGY_VERSION,
            "llm_available": _credentials_available(), "provider": pick_provider()}


@app.get("/api/domains")
def domains():
    return {"domains": [{"name": d.name, "label": d.label, "flagship": d.flagship,
                         "samples": d.samples, "primary_type": d.primary_type}
                        for d in _DOMAINS.values()]}


@app.get("/api/objects")
def objects(domain: str = "cosmetics"):
    return orch(domain).objects_view()


@app.post("/api/ask")
def ask(req: AskRequest):
    o = orch(req.domain)
    o.agent.use_llm = req.use_llm and _credentials_available()
    return o.ask(req.question)


@app.post("/api/signal")
def signal(req: SignalRequest):
    return orch(req.domain).signal(req.key, req.type)


@app.post("/api/approve")
def approve(req: ApproveRequest):
    return orch(req.domain).approve(req.action_id)


@app.get("/api/explain/{object_id}")
def explain(object_id: str, domain: str = "cosmetics"):
    return orch(domain).explain(object_id)
