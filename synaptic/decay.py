from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .util import now_iso, exp_decay_factor

@dataclass
class DecayReport:
    atoms_seen: int
    atoms_updated: int
    avg_factor: float
    ts: str

def apply_decay(store, *, half_life_days: float, min_delta: float = 1e-6) -> DecayReport:
    """Persist decay into stored strengths (maintenance).

    Retrieval also applies dynamic decay for ranking, but persisting decay:
    - keeps stored w-values honest across long gaps,
    - improves pruning decisions,
    - makes the store behave more like synapses (weakening when unused).
    """
    ts = now_iso()
    seen = 0
    updated = 0
    factors: List[float] = []

    for row in store.iter_atoms_indexed():
        seen += 1
        pinned = bool(int(row.get("pinned") or 0))
        if pinned:
            continue
        last_used = (row.get("last_used_ts") or row.get("ts") or "").strip()
        f = exp_decay_factor(last_ts=last_used, now_ts=ts, half_life_days=half_life_days)
        factors.append(f)
        if f >= 0.999999:
            continue

        w = float(row.get("w") or 0.0)
        w2 = w * f
        if abs(w2 - w) <= min_delta:
            continue

        # Preserve last_used_ts (do not set to "now" for decay)
        store.update_atom_strength(
            row["atom_id"],
            ts=ts,
            delta_w=(w2 - w),
            uses_inc=0,
            last_used_ts=(row.get("last_used_ts") or "")
        )
        updated += 1

    avg = float(sum(factors) / len(factors)) if factors else 1.0
    return DecayReport(atoms_seen=seen, atoms_updated=updated, avg_factor=avg, ts=ts)
