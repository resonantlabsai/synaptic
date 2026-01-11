from __future__ import annotations
import argparse, json
from typing import List

from .config import get_config
from .store import SynapticStore
from .retrieve import Retriever
from .prune import prune_to_budget
from .brief import build_brief
from .decay import apply_decay

def _split_csv(s: str) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def cmd_init(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()
    st.close()
    print(f"Initialized Synaptic at: {cfg.home}")

def cmd_add(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()
    atom = st.add_atom(
        type=args.type,
        scope=_split_csv(args.scope),
        tags=_split_csv(args.tags),
        entities=_split_csv(args.entities),
        content=args.content,
        summary=args.summary or "",
        source={"kind": args.source_kind, "ref": args.source_ref} if (args.source_kind or args.source_ref) else {},
        pinned=bool(args.pinned),
    )
    st.close()
    print(json.dumps({"ok": True, "atom": {"atom_id": atom.atom_id, "ts": atom.ts, "type": atom.type}}, ensure_ascii=False))

def cmd_search(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()

    decay_meta = {}
    if args.decay:
        rep = apply_decay(st, half_life_days=cfg.decay_half_life_days)
        decay_meta = rep.__dict__

    r = Retriever(st, cfg)
    seeds = r.l1_search(args.query, k=args.k)
    atom_ids = [x.atom_id for x in seeds]
    st.log_activation(args.query, atom_ids, kind="search", meta={"k": args.k, **({"decay": decay_meta} if decay_meta else {})})

    # strengthen on retrieval (small bump)
    ts = st.log_activation(args.query, atom_ids, kind="manual", meta={"note":"strengthen_on_search"}).ts
    for aid in atom_ids:
        st.update_atom_strength(aid, ts=ts, delta_w=0.01, uses_inc=1, last_used_ts=ts)

    st.close()
    out = [{"atom_id": x.atom_id, "score": x.score, "reasons": x.reasons, "summary": x.row.get("summary","")} for x in seeds]
    print(json.dumps({"ok": True, "results": out}, ensure_ascii=False))

def cmd_brief(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()

    decay_meta = {}
    if args.decay:
        rep = apply_decay(st, half_life_days=cfg.decay_half_life_days)
        decay_meta = rep.__dict__

    r = Retriever(st, cfg)
    seeds = r.l1_search(args.query, k=args.k)
    l2 = r.l2_expand(seeds, neighbor_k=cfg.l2_neighbor_k, take=args.l2)
    meta = r.propose_meta(seeds, l2, take=args.meta)
    seed_ids = [x.atom_id for x in seeds]

    st.log_activation(args.query, seed_ids, kind="brief", meta={"k": args.k, "l2": args.l2, **({"decay": decay_meta} if decay_meta else {})})
    ts = st.log_activation(args.query, seed_ids, kind="manual", meta={"note":"strengthen_on_brief"}).ts
    for aid in seed_ids:
        st.update_atom_strength(aid, ts=ts, delta_w=0.02, uses_inc=1, last_used_ts=ts)

    # record coactivation edges among seeds
    for i in range(len(seed_ids)):
        for j in range(i+1, len(seed_ids)):
            a, b = seed_ids[i], seed_ids[j]
            st.idx.upsert_edge(a, b, kind="coact", weight=1.0, ts=ts, n_inc=1)
            st.idx.upsert_edge(b, a, kind="coact", weight=1.0, ts=ts, n_inc=1)

    st.close()
    brief = build_brief(
        args.query,
        seeds,
        l2_suggestions=[{"atom_id": x.atom_id, "score": x.score, "reasons": x.reasons} for x in l2],
        meta=[{"title": m.title, "summary": m.summary, "members": m.members, "score": m.score, "reasons": m.reasons} for m in meta],
    )
    print(json.dumps({"ok": True, "brief": brief, "atom_ids": seed_ids,
                      "l2_suggestions": [x.__dict__ for x in l2],
                      "meta_candidates": [m.__dict__ for m in meta]}, ensure_ascii=False))

def cmd_prune(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()
    rep = prune_to_budget(st, max_mb=args.max_mb, dry_run=bool(args.dry_run))
    st.close()
    print(json.dumps({"ok": True, "report": rep.__dict__}, ensure_ascii=False))

def cmd_decay(args):
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()
    rep = apply_decay(st, half_life_days=args.half_life_days or cfg.decay_half_life_days)
    st.close()
    print(json.dumps({"ok": True, "report": rep.__dict__}, ensure_ascii=False))

def main():
    p = argparse.ArgumentParser(prog="syn", description="Synaptic: local AI memory store")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Initialize synaptic_data folder")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="Add a memory atom")
    sp.add_argument("--type", required=True)
    sp.add_argument("--scope", default="")
    sp.add_argument("--tags", default="")
    sp.add_argument("--entities", default="")
    sp.add_argument("--content", required=True)
    sp.add_argument("--summary", default="")
    sp.add_argument("--source-kind", default="")
    sp.add_argument("--source-ref", default="")
    sp.add_argument("--pinned", action="store_true")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("search", help="L1 search")
    sp.add_argument("query")
    sp.add_argument("--k", type=int, default=12)
    sp.add_argument("--decay", action="store_true", help="Apply time-based decay before searching (persists).")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("brief", help="Build a memory brief (L1 + L2)")
    sp.add_argument("query")
    sp.add_argument("--k", type=int, default=12)
    sp.add_argument("--l2", type=int, default=8, help="number of L2 suggestions")
    sp.add_argument("--meta", type=int, default=3, help="number of meta pattern candidates")
    sp.add_argument("--decay", action="store_true", help="Apply time-based decay before building the brief (persists).")
    sp.set_defaults(func=cmd_brief)

    sp = sub.add_parser("prune", help="Prune to budget")
    sp.add_argument("--max-mb", type=float, default=50.0)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_prune)

    sp = sub.add_parser("decay", help="Apply time-based decay to stored strengths (maintenance)")
    sp.add_argument("--half-life-days", type=float, default=0.0, help="Override decay half-life for this run.")
    sp.set_defaults(func=cmd_decay)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
