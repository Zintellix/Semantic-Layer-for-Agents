"""L6 · Semantic Resolver (domain-scoped).

The resolution ladder:
  1. exact object_id match            -> confidence 1.0
  2. alias dictionary match           -> stored confidence
  3. ChromaDB vector similarity       -> normalised similarity score
  4. confidence < 0.7                 -> ClarificationNeeded (never a guess)  [O6]

Aliases and the vector index are scoped per domain: each domain seeds its own
alias phrases (from its domain.yaml) and gets its own Chroma collection over its
primary object type. Swapping the local embedder for text-embedding-3-small later
is a one-line change to embeddings.embed().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import chromadb

from . import WORKSPACE_ID
from .db import CHROMA_DIR
from .domains import Domain, load_domains
from .embeddings import LocalEmbeddingFunction

CONFIDENCE_GATE = 0.70  # O6 — below this, clarify instead of guess. NEVER cut this.


@dataclass
class Resolution:
    surface: str
    kind: str                 # 'object' | 'object_set' | 'window'
    target_type: str
    target_id: str
    confidence: float
    method: str               # 'exact' | 'alias' | 'similarity'
    label: str = ""


@dataclass
class ClarificationNeeded:
    surface: str
    confidence: float
    candidates: list[dict] = field(default_factory=list)
    kind: str = "clarification"


class Resolver:
    def __init__(self, conn, registry, objects, domain: Optional[Domain] = None):
        self.conn = conn
        self.registry = registry
        self.objects = objects
        self.domain = domain or load_domains()["cosmetics"]
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self._client.get_or_create_collection(
            name=f"entities_{self.domain.name}",
            embedding_function=LocalEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )

    def _seed_aliases(self) -> list[tuple]:
        rows = []
        for fn_id, phrases in self.domain.alias_object_sets.items():
            for p in phrases:
                rows.append((p.lower(), "object_set", "ObjectSet", fn_id, 0.95))
        for win, phrases in self.domain.alias_windows.items():
            for p in phrases:
                rows.append((p.lower(), "window", "Window", win, 1.0))
        return rows

    # ---- index build (idempotent, per domain) ------------------------
    def build_index(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM entity_aliases WHERE source='seed' AND domain=?",
                    (self.domain.name,))
        for alias, kind, ttype, tid, conf in self._seed_aliases():
            cur.execute(
                "INSERT OR REPLACE INTO entity_aliases "
                "(workspace_id, domain, alias, object_type, object_id, source, confidence) "
                "VALUES (?,?,?,?,?,?,?)",
                (WORKSPACE_ID, self.domain.name, alias, ttype, tid, "seed", conf))
        self.conn.commit()

        ids, docs, metas = [], [], []
        for v in self.objects.all_of(self.domain.primary_type):
            # index the title and the raw key only. We deliberately do NOT index a
            # "<noun> <key>" handle: the shared noun token would let a bare "<noun> N"
            # reference score high and skip the O6 clarification gate.
            for text in (v.title, str(v.pk)):
                ids.append(f"obj::{v.pk}::{len(ids)}")
                docs.append(str(text))
                metas.append({"kind": "object", "target_type": self.domain.primary_type,
                              "target_id": v.pk, "label": v.title})
        for alias, kind, ttype, tid, conf in self._seed_aliases():
            ids.append(f"alias::{tid}::{len(ids)}")
            docs.append(alias)
            metas.append({"kind": kind, "target_type": ttype, "target_id": tid, "label": tid})
        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])
        if ids:
            self.collection.add(ids=ids, documents=docs, metadatas=metas)

    # ---- the ladder ---------------------------------------------------
    def resolve(self, surface: str):
        surface = surface.strip()
        low = surface.lower()

        # rung 1 — exact object id
        if surface.count(":") == 2:
            try:
                obj = self.objects.get_object(surface)
                return Resolution(surface, "object", obj.object_type, surface, 1.0, "exact", obj.title)
            except Exception:  # noqa: BLE001
                pass

        # rung 2 — alias dictionary (domain-scoped)
        row = self.conn.execute(
            "SELECT * FROM entity_aliases WHERE workspace_id=? AND domain=? AND alias=?",
            (WORKSPACE_ID, self.domain.name, low)).fetchone()
        if row:
            kind = {"ObjectSet": "object_set", "Window": "window"}.get(row["object_type"], "object")
            return Resolution(surface, kind, row["object_type"], row["object_id"],
                              row["confidence"], "alias", row["object_id"])

        # rung 3 — ChromaDB vector similarity
        res = self.collection.query(query_texts=[surface], n_results=3)
        metas = res["metadatas"][0] if res["metadatas"] else []
        dists = res["distances"][0] if res["distances"] else []
        if metas:
            best, best_dist = metas[0], dists[0]
            confidence = max(0.0, 1.0 - best_dist)
            candidates = [
                {"target_type": m["target_type"], "target_id": m["target_id"],
                 "label": m["label"], "confidence": round(max(0.0, 1.0 - d), 3)}
                for m, d in zip(metas, dists)
            ]
            if confidence < CONFIDENCE_GATE:                      # rung 4 — O6 gate
                return ClarificationNeeded(surface, round(confidence, 3), candidates)
            return Resolution(surface, best["kind"], best["target_type"], best["target_id"],
                              round(confidence, 3), "similarity", best["label"])

        return ClarificationNeeded(surface, 0.0, [])

    # ---- learned-alias write-back (memory loop) ----------------------
    def confirm(self, surface: str, resolution: Resolution):
        low = surface.strip().lower()
        self.conn.execute(
            "INSERT INTO entity_aliases "
            "(workspace_id, domain, alias, object_type, object_id, source, confidence, confirmed_count) "
            "VALUES (?,?,?,?,?,?,?,1) "
            "ON CONFLICT(workspace_id, domain, alias) DO UPDATE SET "
            "confirmed_count = confirmed_count + 1, confidence = MAX(confidence, ?)",
            (WORKSPACE_ID, self.domain.name, low, resolution.target_type,
             resolution.target_id, "learned", resolution.confidence, resolution.confidence))
        self.conn.commit()
