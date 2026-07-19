"""The nine tests from §8. Each defends a specific architectural claim."""
import pytest

from zx.agent import reason
from zx.compiler import CompileError, Compiler
from zx.db import connect
from zx.objects import make_object_id
from zx.planner import Planner, SemanticGap
from zx.resolver import ClarificationNeeded, Resolver


# 1. lead_time_coverage — the doc's own numeric contract (1.67 ± 0.01)
def test_lead_time_coverage(stack):
    reg, objs, ex = stack
    fn = reg.function("fn.lead_time_coverage")
    ex.run_test(fn, {"inputs": {"on_hand": 100, "avg_daily_units_7d": 5.0},
                     "expect": 1.67, "tol": 0.01})


# 2. days_of_stock — real days, per correction §2.1 (148 / 5.0 = 29.6)
def test_days_of_stock(stack):
    reg, objs, ex = stack
    v = objs.get_object(make_object_id("CosmeticsVariant", "220"))
    assert abs(v.get("days_of_stock") - 29.6) < 0.01


# 3. hero_shades — object sets are computed, not hardcoded
def test_hero_shades(stack):
    _, _, ex = stack
    assert ex.object_set_ids("fn.hero_shades") == ["220", "145", "310"]


# 4. stockout_day — the §5.3 narrative holds (shade 220 -> day 8 of peak)
def test_stockout_day(stack):
    reg, objs, ex = stack
    planner = Planner(reg, objs, ex)
    from zx.resolver import Resolution
    res = Resolution("hero shades", "object_set", "ObjectSet", "fn.hero_shades", 0.95, "alias")
    plan = planner.build_plan([res])
    window = reg.window("GiftingPeak")
    resp = reason(plan, window)
    # 220 is the alarm; its computed day into peak is 8.0
    assert "day 8" in resp.answer.replace(".0", "")


# 5. compiler_rejects — referential integrity (to: NoSuchType fails compile)
def test_compiler_rejects_broken_link(tmp_path, monkeypatch):
    import shutil
    from zx.db import PACKS_DIR
    dst = tmp_path / "packs"
    shutil.copytree(PACKS_DIR, dst)
    objfile = dst / "cosmetics" / "objects.yaml"
    objfile.write_text(objfile.read_text(encoding="utf-8").replace(
        "to: InventoryPosition", "to: NoSuchType"), encoding="utf-8")
    c = Compiler(packs_dir=dst).load()
    with pytest.raises(CompileError) as e:
        c.validate(connect())
    assert "NoSuchType" in str(e.value)


# 6. planner_rejects — the link graph is load-bearing (no stocked_at -> no path)
def test_planner_rejects_missing_link(stack):
    reg, objs, ex = stack
    planner = Planner(reg, objs, ex)
    with pytest.raises(SemanticGap):
        planner.validate_path("CosmeticsVariant", "NoSuchTarget")


# 7. resolver_clarifies — principle O6 (conf < 0.7 -> ClarificationNeeded)
def test_resolver_clarifies(stack):
    reg, objs, ex = stack
    r = Resolver(connect(), reg, objs)
    r.build_index()
    res = r.resolve("zzqx nonsense")
    assert isinstance(res, ClarificationNeeded)


# 8. severity_escalation — vertical rules live in the pack (220 CRITICAL, 505 HIGH)
def test_severity_escalation(stack):
    reg, objs, ex = stack
    from zx.events import EventLifter, Signal
    lifter = EventLifter(connect(), reg, objs, ex)
    assert lifter.lift(Signal("STOCKOUT_RISK", "SKU-220")).severity == "CRITICAL"
    assert lifter.lift(Signal("STOCKOUT_RISK", "SKU-505")).severity == "HIGH"


# 9. guard_blocks — actions are safe by construction (hero action on 505 -> blocked)
def test_guard_blocks_non_hero(stack):
    reg, objs, ex = stack
    from zx.actions import ActionLayer
    al = ActionLayer(connect(), reg, objs, ex)
    prop = al.propose("prioritise_hero_shade_replenishment",
                      make_object_id("CosmeticsVariant", "505"), {"urgency_days": 18})
    assert prop.status == "BLOCKED"
    # and an invented action is rejected outright
    bad = al.propose("email_supplier", make_object_id("CosmeticsVariant", "220"), {})
    assert bad.status == "REJECTED"
