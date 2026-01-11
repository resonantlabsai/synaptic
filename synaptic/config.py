from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class SynapticConfig:
    home: Path
    embed_dim: int = 256

    # L2
    l2_neighbor_k: int = 30
    l2_sim_threshold: float = 0.25

    # Safety / limits
    max_atom_bytes: int = 32_000   # hard cap for atom content+summary
    max_result_atoms: int = 50     # hard cap for retrieval output size

    # Decay (time-based). Interpreted as exponential half-life.
    # Example: half_life_days=30 -> strength halves every ~30 days of non-use.
    decay_half_life_days: float = 30.0
    decay_apply_on_retrieval: bool = True

def get_config() -> SynapticConfig:
    # Prefer env override; else use ./synaptic_data (repo-friendly, portable)
    home = Path(os.environ.get("SYNAPTIC_HOME", "./synaptic_data")).expanduser().resolve()
    embed_dim = int(os.environ.get("SYNAPTIC_EMBED_DIM", "256"))

    hl = float(os.environ.get("SYNAPTIC_DECAY_HALF_LIFE_DAYS", "30"))
    apply_on_ret = os.environ.get("SYNAPTIC_DECAY_ON_RETRIEVAL", "1").strip().lower() not in ("0", "false", "no")

    return SynapticConfig(home=home, embed_dim=embed_dim, decay_half_life_days=hl, decay_apply_on_retrieval=apply_on_ret)
