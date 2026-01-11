from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Atom:
    atom_id: str
    ts: str
    type: str                 # idea|decision|constraint|insight|question|plan|code|principle|cluster
    scope: List[str]          # e.g. ["orion","colony"]
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    content: str = ""         # short raw text (keep it compact)
    summary: str = ""         # distilled form (stable)

    source: Dict[str, Any] = field(default_factory=dict)   # {"kind":"chat","thread_id":"...","msg_ids":[...]} etc.

    # synaptic strength state
    w: float = 0.05           # strength (starts small)
    uses: int = 0
    last_used_ts: str = ""

    pinned: bool = False
    hash: str = ""

@dataclass
class ActivationEvent:
    act_id: str
    ts: str
    query: str
    atom_ids: List[str]
    kind: str                 # "search" | "brief" | "cite" | "manual"
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class L2Suggestion:
    atom_id: str
    score: float
    reasons: List[str] = field(default_factory=list)

@dataclass
class MetaCandidate:
    title: str
    summary: str
    members: List[str]
    score: float
    reasons: List[str] = field(default_factory=list)

@dataclass
class Retrieved:
    atom_id: str
    score: float
    reasons: List[str]
    row: Dict[str, Any]
