from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import math

from .util import exp_decay_factor, now_iso

@dataclass
class PruneReport:
    kept: int
    removed: int
    bytes_before: int
    bytes_after: int
    removed_ids: List[str]

def estimate_atom_bytes(row: Dict) -> int:
    s = (row.get("summary") or "") + (row.get("content") or "") + (row.get("tags") or "") + (row.get("entities") or "")
    return len(s.encode("utf-8"))

def prune_to_budget(store, *, max_mb: float = 50.0, dry_run: bool = True) -> PruneReport:
    rows = list(store.iter_atoms_indexed())
    bytes_before = sum(estimate_atom_bytes(r) for r in rows)
    budget = int(max_mb * 1024 * 1024)

    if bytes_before <= budget:
        return PruneReport(kept=len(rows), removed=0, bytes_before=bytes_before, bytes_after=bytes_before, removed_ids=[])

    ts = now_iso()
    hl = getattr(store.cfg, "decay_half_life_days", 30.0)

    def priority(r: Dict) -> float:
        pinned = 1.0 if int(r.get("pinned") or 0) else 0.0
        w = float(r.get("w") or 0.0)
        uses = float(r.get("uses") or 0.0)

        last_used = (r.get("last_used_ts") or r.get("ts") or "").strip()
        f = exp_decay_factor(last_ts=last_used, now_ts=ts, half_life_days=hl)
        w_eff = w * f

        rec = 1.0 if (r.get("last_used_ts") or "").strip() else 0.0
        size_pen = estimate_atom_bytes(r) / 10_000.0
        return 10.0*pinned + 2.2*math.tanh(w_eff/2.0) + 0.9*math.tanh(uses/10.0) + 0.25*rec - 0.35*size_pen

    rows.sort(key=priority, reverse=True)

    kept = []
    total = 0
    for r in rows:
        b = estimate_atom_bytes(r)
        if total + b <= budget or int(r.get("pinned") or 0):
            kept.append(r)
            total += b

    kept_ids = {r["atom_id"] for r in kept}
    removed = [r for r in rows if r["atom_id"] not in kept_ids]
    removed_ids = [r["atom_id"] for r in removed]
    bytes_after = sum(estimate_atom_bytes(r) for r in kept)

    if not dry_run:
        for aid in removed_ids:
            store.delete_atom(aid)

    return PruneReport(kept=len(kept), removed=len(removed), bytes_before=bytes_before, bytes_after=bytes_after, removed_ids=removed_ids)
