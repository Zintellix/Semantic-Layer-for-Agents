"""Domain layer — the glue that lets one semantic engine serve many verticals.

Each vertical is a pack directory with a `domain.yaml` manifest describing the
*task* (flagship question, the entry object set, what to prefetch, how to reason
about the metric). The ontology primitives themselves (objects, links, functions,
events, actions) live in the same pack's other YAML files, exactly as before.

Add a new domain = drop in a pack + a domain.yaml. No engine code changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .db import PACKS_DIR


@dataclass
class Metric:
    mode: str                       # "timeline" | "aggregate"
    unit: str = ""
    # timeline
    level: Optional[str] = None     # stock/budget/level property on the member (or linked)
    rate: Optional[str] = None      # depletion rate property
    window: Optional[str] = None    # seasonal window name
    uplift_key: str = "expected_uplift_pct"
    min_days: Optional[float] = None  # timeline without a window: alarm below this
    event_noun: str = "breach"      # "stockout" | "budget exhaustion" | ...
    # aggregate
    value: Optional[str] = None     # property to sum across members
    threshold: Optional[float] = None
    threshold_label: str = "target"
    direction: str = "at_least"     # at_least (miss if below) | at_most (over if above)


@dataclass
class Prefetch:
    traverse: Optional[str] = None      # link to pull a related object (may be None)
    target_type: Optional[str] = None   # the traversed object type
    member_props: list[str] = field(default_factory=list)
    target_props: list[str] = field(default_factory=list)


@dataclass
class DomainAction:
    action_type: str
    param: str = "urgency_days"     # the single numeric param the reasoner fills
    param_mode: str = "window_start"  # window_start | one | days_cover


@dataclass
class Domain:
    name: str
    label: str
    flagship: str
    primary_type: str
    object_set: str
    prefetch: Prefetch
    metric: Metric
    action: DomainAction
    samples: list[str] = field(default_factory=list)
    alias_object_sets: dict[str, list[str]] = field(default_factory=dict)
    alias_windows: dict[str, list[str]] = field(default_factory=dict)
    signal_type: str = "RISK_DETECTED"

    @property
    def is_cosmetics(self) -> bool:
        return self.name == "cosmetics"


def _load(path: Path) -> Domain:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    pf = d.get("prefetch", {})
    mt = d.get("metric", {})
    ac = d.get("action", {})
    al = d.get("aliases", {})
    return Domain(
        name=d["domain"], label=d["label"], flagship=d["flagship"],
        primary_type=d["primary_type"], object_set=d["object_set"],
        samples=d.get("samples", []),
        signal_type=d.get("signal_type", "RISK_DETECTED"),
        prefetch=Prefetch(pf.get("traverse"), pf.get("target_type"),
                          pf.get("member_props", []), pf.get("target_props", [])),
        metric=Metric(mode=mt["mode"], unit=mt.get("unit", ""),
                      level=mt.get("level"), rate=mt.get("rate"), window=mt.get("window"),
                      uplift_key=mt.get("uplift_key", "expected_uplift_pct"),
                      min_days=mt.get("min_days"), event_noun=mt.get("event_noun", "breach"),
                      value=mt.get("value"), threshold=mt.get("threshold"),
                      threshold_label=mt.get("threshold_label", "target"),
                      direction=mt.get("direction", "at_least")),
        action=DomainAction(ac["action_type"], ac.get("param", "urgency_days"),
                            ac.get("param_mode", "window_start")),
        alias_object_sets=al.get("object_sets", {}),
        alias_windows=al.get("windows", {}),
    )


def load_domains(packs_dir: Path | None = None) -> dict[str, Domain]:
    packs = Path(packs_dir or PACKS_DIR)
    out: dict[str, Domain] = {}
    for p in sorted(packs.iterdir()):
        man = p / "domain.yaml"
        if man.exists():
            dom = _load(man)
            out[dom.name] = dom
    return out
