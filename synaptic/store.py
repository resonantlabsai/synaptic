from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

from .config import SynapticConfig
from .models import Atom, ActivationEvent
from .util import now_iso, sha256_text, stable_id, safe_truncate, to_jsonable
from .index import SynapticIndex, AtomRow

class SynapticStore:
    """Owns the append-only ledgers + SQLite index.

    Design:
    - atoms.jsonl: authoritative history of atoms (append-only; last write wins for latest state)
    - activations.jsonl: usage events (append-only)
    - synaptic.sqlite: query index and edges
    """

    def __init__(self, cfg: SynapticConfig):
        self.cfg = cfg
        self.home = cfg.home
        self.home.mkdir(parents=True, exist_ok=True)
        self.atoms_path = self.home / "atoms.jsonl"
        self.acts_path = self.home / "activations.jsonl"
        self.db_path = self.home / "synaptic.sqlite"
        self.idx = SynapticIndex(self.db_path)

    def close(self):
        self.idx.close()

    def init(self):
        # touch files so tooling sees them
        if not self.atoms_path.exists():
            self.atoms_path.write_text("", encoding="utf-8")
        if not self.acts_path.exists():
            self.acts_path.write_text("", encoding="utf-8")

    def add_atom(self, *, type: str, scope: List[str], tags: List[str], entities: List[str],
                 content: str, summary: str, source: Dict[str, Any] | None = None, pinned: bool = False) -> Atom:
        ts = now_iso()
        source = source or {}
        content = safe_truncate(content.strip(), self.cfg.max_atom_bytes)
        summary = safe_truncate(summary.strip() if summary else content.strip(), self.cfg.max_atom_bytes)

        payload = {
            "ts": ts, "type": type, "scope": scope, "tags": tags, "entities": entities,
            "content": content, "summary": summary, "source": source
        }
        atom_id = stable_id("atom", payload)
        h = sha256_text(summary + "\n" + content)

        atom = Atom(
            atom_id=atom_id, ts=ts, type=type, scope=scope, tags=tags, entities=entities,
            content=content, summary=summary, source=source,
            w=0.05, uses=0, last_used_ts="", pinned=bool(pinned), hash=h
        )
        self._append_jsonl(self.atoms_path, to_jsonable(atom))
        self.idx.upsert_atom(AtomRow(
            atom_id=atom.atom_id, ts=atom.ts, type=atom.type, scope=",".join(atom.scope),
            tags=",".join(atom.tags), entities=",".join(atom.entities),
            summary=atom.summary, content=atom.content, w=float(atom.w),
            uses=int(atom.uses), last_used_ts=atom.last_used_ts, pinned=1 if atom.pinned else 0
        ))
        return atom

    def update_atom_strength(self, atom_id: str, *, ts: str, delta_w: float = 0.0, uses_inc: int = 0, last_used_ts: str | None = None):
        row = self.idx.get_atom(atom_id)
        if row is None:
            return
        w = float(row["w"]) + float(delta_w)
        uses = int(row["uses"]) + int(uses_inc)
        last = last_used_ts if last_used_ts is not None else (row["last_used_ts"] or ts)
        # clamp w to a reasonable range
        w = max(-5.0, min(5.0, w))
        # write an updated atom record (append-only; last wins)
        atom = Atom(
            atom_id=row["atom_id"], ts=row["ts"], type=row["type"],
            scope=(row["scope"].split(",") if row["scope"] else []),
            tags=(row["tags"].split(",") if row["tags"] else []),
            entities=(row["entities"].split(",") if row["entities"] else []),
            summary=row["summary"], content=row["content"],
            source={},  # index doesn't store source; keep blank here
            w=w, uses=uses, last_used_ts=last,
            pinned=bool(row["pinned"]), hash=""
        )
        self._append_jsonl(self.atoms_path, to_jsonable(atom))
        self.idx.upsert_atom(AtomRow(
            atom_id=atom.atom_id, ts=atom.ts, type=atom.type, scope=",".join(atom.scope),
            tags=",".join(atom.tags), entities=",".join(atom.entities),
            summary=atom.summary, content=atom.content, w=float(atom.w),
            uses=int(atom.uses), last_used_ts=atom.last_used_ts, pinned=1 if atom.pinned else 0
        ))

    def log_activation(self, query: str, atom_ids: List[str], kind: str, meta: Dict[str, Any] | None = None) -> ActivationEvent:
        ts = now_iso()
        meta = meta or {}
        payload = {"ts": ts, "query": query, "atom_ids": atom_ids, "kind": kind, "meta": meta}
        act_id = stable_id("act", payload)
        ev = ActivationEvent(act_id=act_id, ts=ts, query=query, atom_ids=atom_ids, kind=kind, meta=meta)
        self._append_jsonl(self.acts_path, to_jsonable(ev))
        return ev

    def iter_atoms_indexed(self) -> Iterable[Dict[str, Any]]:
        # read from SQLite for performance
        c = self.idx.conn.cursor()
        for row in c.execute("SELECT * FROM atoms ORDER BY pinned DESC, w DESC, uses DESC"):
            yield dict(row)

    def delete_atom(self, atom_id: str):
        # destructive: remove from sqlite (atoms.jsonl remains append-only history)
        c = self.idx.conn.cursor()
        c.execute("DELETE FROM atoms WHERE atom_id=?", (atom_id,))
        try:
            c.execute("DELETE FROM atoms_fts WHERE atom_id=?", (atom_id,))
        except Exception:
            pass
        self.idx.conn.commit()

    @staticmethod
    def _append_jsonl(path: Path, obj: Dict[str, Any]):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
