from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
import math

from .config import SynapticConfig
from .embeddings import HasherEmbedder, cosine_sparse
from .models import Retrieved, L2Suggestion, MetaCandidate
from .util import tokenize, exp_decay_factor, now_iso

class Retriever:
    def __init__(self, store, cfg: SynapticConfig):
        self.store = store
        self.cfg = cfg
        self.embedder = HasherEmbedder(dim=cfg.embed_dim)

    def l1_search(self, query: str, k: int = 12) -> List[Retrieved]:
        k = max(1, min(k, self.cfg.max_result_atoms))

        fts_query = " ".join(tokenize(query)[:10]) or query
        rows = self.store.idx.search_fts(fts_query, k=max(k*4, 20))
        if not rows:
            rows = self.store.idx.search_fallback(query, k=max(k*4, 20))

        qv = self.embedder.embed(query)
        ts = now_iso()
        hl = self.cfg.decay_half_life_days

        scored: List[Retrieved] = []
        for r in rows:
            rd = dict(r)
            text = (rd.get("summary") or "") + "\n" + (rd.get("content") or "")
            sim = cosine_sparse(qv, self.embedder.embed(text))

            w = float(rd.get("w") or 0.0)
            uses = float(rd.get("uses") or 0.0)
            pinned = 1.0 if int(rd.get("pinned") or 0) else 0.0

            w_eff = w
            if self.cfg.decay_apply_on_retrieval and not pinned:
                last_used = (rd.get("last_used_ts") or rd.get("ts") or "").strip()
                f = exp_decay_factor(last_ts=last_used, now_ts=ts, half_life_days=hl)
                w_eff = w * f

            score = 0.70*sim + 0.20*math.tanh(w_eff/2.0) + 0.08*math.tanh(uses/10.0) + 0.02*pinned
            reasons = []
            if sim > 0: reasons.append(f"sim:{sim:.2f}")
            if pinned: reasons.append("pinned")
            if w_eff: reasons.append(f"w_eff:{w_eff:.2f}")
            scored.append(Retrieved(atom_id=rd["atom_id"], score=float(score), reasons=reasons, row=rd))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]

    def l2_expand(self, seeds: List[Retrieved], neighbor_k: int = 30, take: int = 8) -> List[L2Suggestion]:
        take = max(0, min(take, 50))
        neighbor_k = max(5, min(neighbor_k, 200))
        seed_ids = [s.atom_id for s in seeds]
        seed_set = set(seed_ids)

        candidates: Dict[str, Dict[str, Any]] = {}

        for sid in seed_ids:
            for kind in ("neighbor", "coact"):
                edges = self.store.idx.neighbors(sid, kind=kind, k=neighbor_k)
                for e in edges:
                    dst = e["dst"]
                    if dst in seed_set:
                        continue
                    slot = candidates.setdefault(dst, {"score": 0.0, "reasons": set()})
                    w = float(e["weight"] or 0.0)
                    n = float(e["n"] or 0.0)
                    if kind == "neighbor":
                        slot["score"] += 0.8*w
                        slot["reasons"].add("neighbor")
                    else:
                        slot["score"] += 0.3*w + 0.1*math.tanh(n/10.0)
                        slot["reasons"].add("coact")

        qv = self.embedder.embed(" ".join([s.row.get("summary","") for s in seeds]) or "")
        pool = []
        for i, row in enumerate(self.store.iter_atoms_indexed()):
            if i >= 400:
                break
            aid = row["atom_id"]
            if aid in seed_set:
                continue
            text = (row.get("summary") or "") + "\n" + (row.get("content") or "")
            sim = cosine_sparse(qv, self.embedder.embed(text))
            if sim >= self.cfg.l2_sim_threshold:
                pool.append((aid, sim))
        pool.sort(key=lambda x: x[1], reverse=True)
        for aid, sim in pool[:neighbor_k]:
            slot = candidates.setdefault(aid, {"score": 0.0, "reasons": set()})
            slot["score"] += 0.6*sim
            slot["reasons"].add("sim")

        sugg = [L2Suggestion(atom_id=aid, score=float(v["score"]), reasons=sorted(v["reasons"])) for aid, v in candidates.items()]
        sugg.sort(key=lambda x: x.score, reverse=True)
        return sugg[:take]

    def propose_meta(self, seeds: List[Retrieved], l2: List[L2Suggestion], take: int = 3) -> List[MetaCandidate]:
        take = max(0, min(take, 10))
        top_ids = [s.atom_id for s in seeds] + [x.atom_id for x in l2[:12]]
        top_ids = list(dict.fromkeys(top_ids))

        adj: Dict[str, Dict[str, float]] = {a: {} for a in top_ids}
        for a in top_ids:
            edges = self.store.idx.neighbors(a, kind="coact", k=50)
            for e in edges:
                b = e["dst"]
                if b in adj:
                    adj[a][b] = float(e["weight"] or 0.0) + 0.05*float(e["n"] or 0.0)

        cands: List[MetaCandidate] = []
        for anchor in [s.atom_id for s in seeds[:6]]:
            neigh = sorted(adj.get(anchor, {}).items(), key=lambda kv: kv[1], reverse=True)[:5]
            if len(neigh) < 2:
                continue
            for i in range(len(neigh)):
                for j in range(i+1, len(neigh)):
                    b, wb = neigh[i]
                    c, wc = neigh[j]
                    bc = adj.get(b, {}).get(c, 0.0) + adj.get(c, {}).get(b, 0.0)
                    cohesion = (wb + wc + bc) / 3.0
                    if cohesion < 0.15:
                        continue
                    members = [anchor, b, c]
                    title = f"Pattern cluster ({len(members)})"
                    summary = "Frequent co-activation suggests these ideas belong to the same working concept."
                    score = float(cohesion)
                    cands.append(MetaCandidate(title=title, summary=summary, members=members, score=score,
                                               reasons=["coact_cohesion"]))
        cands.sort(key=lambda x: x.score, reverse=True)

        out: List[MetaCandidate] = []
        seen = set()
        for m in cands:
            key = tuple(sorted(m.members))
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
            if len(out) >= take:
                break
        return out
