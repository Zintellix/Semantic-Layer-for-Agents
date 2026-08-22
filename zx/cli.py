"""zx CLI — drive the semantic layer across domains.

    zx domains
    zx ask --domain sales "Are we going to hit quota on our top deals this quarter?"
    zx ask "Are we going to stock out on our hero shades before the gifting peak?"
    zx signal --domain cosmetics --key SKU-505
    zx approve <action_id> --domain cosmetics
    zx explain ws1:CosmeticsVariant:220 --domain cosmetics
"""
from __future__ import annotations

import argparse
import sys

from .domains import load_domains
from .orchestrator import Orchestrator

C_DIM, C_BOLD, C_GREEN, C_YELLOW, C_RESET = "\033[2m", "\033[1m", "\033[32m", "\033[33m", "\033[0m"


def _print_trace(result: dict):
    print()
    for s in result["stages"]:
        head = f"  [{s['n']}] {s['name']:<9}"
        body = ("\n" + " " * 16).join(s["lines"]) if s["lines"] else ""
        print(f"{C_DIM}{head}{C_RESET} {body}")
    if result.get("status") == "CLARIFY":
        clar = result["clarification"]
        print(f"\n  {C_YELLOW}Clarification needed{C_RESET} for '{clar['surface']}' "
              f"(conf {clar['confidence']} < 0.70). Did you mean:")
        for c in clar["candidates"]:
            print(f"    - {c['label']} ({c['confidence']})")
        return
    if result.get("status") == "SEMANTIC_GAP":
        print(f"\n  {C_YELLOW}Query rejected:{C_RESET} {result['error']}")
        return
    print(f"\n{C_BOLD}{result['answer']}{C_RESET}\n")
    if result.get("action_card"):
        c = result["action_card"]
        print(f"  {C_GREEN}ACTION CARD  [Tier {c['tier']} · {c['status']}]{C_RESET}")
        args = ", ".join(f"{k}={v}" for k, v in c["params"].items())
        print(f"    {c['action_type']}(target={c['target_title']}, {args})")
        if c["guards_passed"]:
            print(f"    guards passed: {', '.join(c['guards_passed'])}")
        print(f"    -> zx approve {c['action_id']} --domain {result['domain']}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="zx", description="Zintellix semantic layer CLI")
    parser.add_argument("--domain", help="domain to query")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("domains")
    p_ask = sub.add_parser("ask"); p_ask.add_argument("question")
    p_ask.add_argument("--no-llm", action="store_true", help="force deterministic reasoner")
    p_sig = sub.add_parser("signal")
    p_sig.add_argument("--key"); p_sig.add_argument("--sku"); p_sig.add_argument("--type")
    p_app = sub.add_parser("approve"); p_app.add_argument("action_id")
    p_exp = sub.add_parser("explain"); p_exp.add_argument("object_id")
    args = parser.parse_args(argv)

    if args.cmd == "domains":
        for d in load_domains().values():
            print(f"  {d.name:<10} {d.label:<24} — {d.flagship}")
        return

    if not args.domain:
        parser.error(f"the following arguments are required for '{args.cmd}': --domain")

    orch = Orchestrator(domain=args.domain,
                        use_llm=(False if getattr(args, "no_llm", False) else None))

    if args.cmd == "ask":
        _print_trace(orch.ask(args.question))
    elif args.cmd == "signal":
        key = args.key or args.sku
        if not key:
            parser.error("signal needs --key (or --sku)")
        r = orch.signal(key, args.type)
        print(f"\n  [lift]     {r['lifted']['event_type']}(target={r['lifted']['variant']})")
        for t in r["severity_trace"]:
            print(f"  [decide]   {t}")
        p = r["proposal"]
        print(f"  [propose]  {p['action_type']} -> {p['status']}"
              + (f" ({p['reason']})" if p['reason'] else ""))
        if r["fallback"]:
            print(f"             falling back to: {r['fallback']['action_type']} "
                  f"[Tier {r['fallback']['tier']}]")
    elif args.cmd == "approve":
        c = orch.approve(args.action_id)
        print(f"\n  {c['action_type']} -> {c['status']} ({c['reason']})")
    elif args.cmd == "explain":
        import json
        print(json.dumps(orch.explain(args.object_id), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
