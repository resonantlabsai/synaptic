from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import hashlib
import math
from .util import tokenize

@dataclass
class HasherEmbedder:
    """A tiny, local embedder based on **stable feature hashing**.

    - Deterministic across runs (uses sha256 instead of Python's salted hash).
    - Produces a sparse, L2-normalized vector dict {idx: value}.
    """
    dim: int = 256

    def _stable_hash64(self, token: str) -> int:
        d = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(d[:8], "big", signed=False)

    def embed(self, text: str) -> Dict[int, float]:
        toks = tokenize(text)
        if not toks:
            return {}
        counts: Dict[int, float] = {}
        for t in toks:
            h = self._stable_hash64(t)
            idx = h % self.dim
            counts[idx] = counts.get(idx, 0.0) + 1.0

        norm = math.sqrt(sum(v*v for v in counts.values()))
        if norm <= 0.0:
            return counts
        return {k: v / norm for k, v in counts.items()}

def cosine_sparse(a: Dict[int, float], b: Dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    s = 0.0
    for k, va in a.items():
        vb = b.get(k)
        if vb is not None:
            s += va * vb
    return float(s)
