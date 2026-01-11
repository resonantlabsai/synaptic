from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import sqlite3

@dataclass
class AtomRow:
    atom_id: str
    ts: str
    type: str
    scope: str
    tags: str
    entities: str
    summary: str
    content: str
    w: float
    uses: int
    last_used_ts: str
    pinned: int

class SynapticIndex:
    """SQLite index:
    - atoms table (metadata)
    - atoms_fts (FTS5 on summary+content+tags+entities+scope)
    - edges table (neighbor + coactivation)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        self.conn.close()

    def _init_schema(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS atoms(
            atom_id TEXT PRIMARY KEY,
            ts TEXT,
            type TEXT,
            scope TEXT,
            tags TEXT,
            entities TEXT,
            summary TEXT,
            content TEXT,
            w REAL,
            uses INTEGER,
            last_used_ts TEXT,
            pinned INTEGER
        )""")
        # FTS5 if available
        try:
            c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5(
                atom_id UNINDEXED,
                summary,
                content,
                tags,
                entities,
                scope
            )""")
        except sqlite3.OperationalError:
            pass

        c.execute("""CREATE TABLE IF NOT EXISTS edges(
            src TEXT,
            dst TEXT,
            kind TEXT,              -- 'neighbor' | 'coact'
            weight REAL,
            n INTEGER DEFAULT 0,
            last_ts TEXT,
            PRIMARY KEY (src, dst, kind)
        )""")
        c.execute("""CREATE INDEX IF NOT EXISTS idx_edges_src_kind ON edges(src, kind)""")
        c.execute("""CREATE INDEX IF NOT EXISTS idx_edges_dst_kind ON edges(dst, kind)""")
        self.conn.commit()

    def _fts_exists(self) -> bool:
        c = self.conn.cursor()
        c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='atoms_fts'""")
        return c.fetchone() is not None

    def upsert_atom(self, r: AtomRow):
        c = self.conn.cursor()
        c.execute("""INSERT INTO atoms(atom_id,ts,type,scope,tags,entities,summary,content,w,uses,last_used_ts,pinned)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(atom_id) DO UPDATE SET
              ts=excluded.ts, type=excluded.type, scope=excluded.scope, tags=excluded.tags, entities=excluded.entities,
              summary=excluded.summary, content=excluded.content, w=excluded.w, uses=excluded.uses,
              last_used_ts=excluded.last_used_ts, pinned=excluded.pinned
        """, (r.atom_id, r.ts, r.type, r.scope, r.tags, r.entities, r.summary, r.content, r.w, r.uses, r.last_used_ts, r.pinned))

        # Keep FTS in sync (FTS tables generally don't support ON CONFLICT like normal tables)
        if self._fts_exists():
            try:
                c.execute("DELETE FROM atoms_fts WHERE atom_id=?", (r.atom_id,))
                c.execute("INSERT INTO atoms_fts(atom_id, summary, content, tags, entities, scope) VALUES (?,?,?,?,?,?)",
                          (r.atom_id, r.summary, r.content, r.tags, r.entities, r.scope))
            except sqlite3.OperationalError:
                # If this build lacks FTS5 or disallows these ops, silently skip
                pass

        self.conn.commit()

    def get_atom(self, atom_id: str) -> Optional[sqlite3.Row]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM atoms WHERE atom_id=?", (atom_id,))
        return c.fetchone()

    def search_fts(self, query: str, k: int) -> List[sqlite3.Row]:
        if not self._fts_exists():
            return []
        c = self.conn.cursor()
        try:
            c.execute("""SELECT atoms.*, bm25(atoms_fts) AS rank
                FROM atoms_fts JOIN atoms ON atoms_fts.atom_id = atoms.atom_id
                WHERE atoms_fts MATCH ?
                ORDER BY rank
                LIMIT ?""", (query, k))
            return list(c.fetchall())
        except sqlite3.OperationalError:
            return []

    def search_fallback(self, query: str, k: int) -> List[sqlite3.Row]:
        q = f"%{query.lower()}%"
        c = self.conn.cursor()
        c.execute("""SELECT * FROM atoms
            WHERE lower(summary) LIKE ? OR lower(content) LIKE ? OR lower(tags) LIKE ? OR lower(entities) LIKE ? OR lower(scope) LIKE ?
            ORDER BY pinned DESC, w DESC, uses DESC
            LIMIT ?""", (q, q, q, q, q, k))
        return list(c.fetchall())

    def neighbors(self, atom_id: str, kind: str, k: int) -> List[sqlite3.Row]:
        c = self.conn.cursor()
        c.execute("""SELECT * FROM edges
            WHERE src=? AND kind=?
            ORDER BY weight DESC, n DESC
            LIMIT ?""", (atom_id, kind, k))
        return list(c.fetchall())

    def upsert_edge(self, src: str, dst: str, kind: str, weight: float, ts: str, n_inc: int = 0):
        c = self.conn.cursor()
        c.execute("""INSERT INTO edges(src,dst,kind,weight,n,last_ts)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(src,dst,kind) DO UPDATE SET
              weight=excluded.weight,
              n=edges.n + ?,
              last_ts=excluded.last_ts
        """, (src, dst, kind, float(weight), int(n_inc), ts, int(n_inc)))
        self.conn.commit()
